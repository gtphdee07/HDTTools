"""Function tests for scripts/long_command_guard.py (#200), the PreToolUse hook that puts a build session's
device commands on the supervised runner, and for its registration in .claude/settings.json. The hook is
fed the JSON the harness sends on stdin; nothing here runs a command, adb or an emulator."""

import json
import shlex
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import long_command_guard as guard  # noqa: E402

RUNNER = f"uv run --no-project {shlex.quote(guard.SUPERVISOR.as_posix())}"
GRADLE = "android/gradlew -p android connectedDebugAndroidTest"


def hook(command, tool="Bash", log_path=None, decide_fn=None):
    """Feeds one hook call; returns (exit code, parsed output or None)."""
    out = []
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}, "hook_event_name": "PreToolUse"})
    kwargs = {"decide_fn": decide_fn} if decide_fn else {}
    code = guard.run_hook(payload, out=out.append, log_path=log_path or Path("unused.log"), **kwargs)
    return code, (json.loads(out[0]) if out else None)


def rewritten(command):
    code, answer = hook(command)
    assert code == 0 and answer is not None, command
    decision = answer["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse" and decision["permissionDecision"] == "allow", decision
    return decision["updatedInput"]["command"]


def refused(command):
    code, answer = hook(command)
    assert code == 0 and answer is not None, command
    decision = answer["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    return decision["permissionDecisionReason"]


# --- a bare device command is rewritten ----------------------------------------------------------


def test_a_bare_gradle_device_run_is_rewritten_to_the_supervised_form():
    assert rewritten(GRADLE) == f"{RUNNER} --device --output-limit-s 300 -- {GRADLE}"


@pytest.mark.parametrize(
    "command",
    [
        "./gradlew connectedAndroidTest",
        "gradlew.bat -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.rigcheck.app.ui.FooTest",
        "android/gradlew connectedDebugAndroidTest --tests x",
    ],
)
def test_each_connected_task_spelling_is_rewritten(command):
    assert rewritten(command).endswith(f"-- {command}")


def test_a_bare_adb_instrument_run_is_rewritten():
    command = "adb shell am instrument -w com.rigcheck.app.test/com.rigcheck.app.CustomTestRunner"
    assert rewritten(command) == f"{RUNNER} --device -- {command}"


def test_adb_with_a_serial_and_a_quoted_shell_command_is_still_recognised():
    command = 'adb -s emulator-5554 shell "am instrument -w a/b"'
    assert rewritten(command).endswith(f"--device -- {command}")


def test_a_compound_line_has_only_its_device_command_rewritten():
    assert rewritten(f"cd android && {GRADLE}") == f"cd android && {RUNNER} --device --output-limit-s 300 -- {GRADLE}"
    assert rewritten(f"{GRADLE} | tail -5") == f"{RUNNER} --device --output-limit-s 300 -- {GRADLE} | tail -5"
    assert rewritten(f"echo start; {GRADLE}; echo done").endswith(f"-- {GRADLE}; echo done")


def test_an_environment_prefix_stays_in_front_of_the_wrapper():
    assert rewritten(f"ANDROID_SERIAL=emulator-5554 {GRADLE}").startswith(f"ANDROID_SERIAL=emulator-5554 {RUNNER}")


# --- the command's own text is kept, so the shell still reads it the same way ----------------------------


@pytest.mark.parametrize(
    "command",
    [
        f"{GRADLE} > out.txt 2>&1",
        "gradlew connectedDebugAndroidTest -Pclass=$CLASS",
        "gradlew connectedDebugAndroidTest --tests 'com.x.*'",
        "gradlew connectedDebugAndroidTest $(cat args.txt)",
    ],
)
def test_variables_globs_substitutions_and_redirects_are_left_as_typed_after_the_double_dash(command):
    result = rewritten(command)
    assert result.startswith(RUNNER) and result.endswith(f"-- {command}")


def test_an_environment_value_with_quotes_stays_outside_the_wrapped_command():
    assert rewritten(f'JAVA_OPTS="-Xmx2g -Dx=1" {GRADLE}').startswith(f'JAVA_OPTS="-Xmx2g -Dx=1" {RUNNER}')


# --- an emulator start cannot be wrapped: refused with the exact command to type ---------------------------


def test_a_bare_emulator_start_is_refused_and_pointed_at_the_boot_only_run():
    assert "android_suite_loop.py --boot-only --avd medium_phone" in refused("emulator -avd medium_phone -no-snapshot")
    assert "android_suite_loop.py --boot-only --avd medium_phone" in refused("C:/Android/emulator/emulator.exe -avd medium_phone")


def test_the_emulator_flags_become_options_of_the_boot_only_run():
    command = r"G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window"
    reason = refused(command.replace("\\", "/"))
    assert "--boot-only --avd medium_phone --gpu swangle_indirect --emulator-arg=-no-audio --emulator-arg=-no-window" in reason
    assert "-no-snapshot" not in reason


def test_an_at_avd_name_and_a_flag_with_a_value_are_forwarded_in_order():
    assert guard.emulator_flags(["emulator", "@Pixel_7", "-memory", "4096"]) == " --avd Pixel_7 --emulator-arg=-memory --emulator-arg=4096"


def test_a_line_with_an_emulator_start_is_refused_as_a_whole_and_names_every_supervised_command():
    reason = refused(f"{GRADLE}; emulator -avd x")
    assert "--boot-only --avd x" in reason and "run_supervisor.py' --device" in reason


# --- what it leaves alone ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        f"{RUNNER} --device -- {GRADLE}",
        "uv run scripts/run_supervisor.py --device -- adb shell am instrument -w a/b",
        "uv run scripts/run_supervisor.py --device -- emulator -avd x",
        "uv run scripts/android_suite_loop.py --runs 3",
        "uv run scripts/android_suite_loop.py --boot-only",
    ],
)
def test_a_command_already_under_a_runner_passes_unchanged(command):
    assert hook(command) == (0, None)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "ls android",
        "uv run pytest tests/test_x.py",
        "android/gradlew -p android testDebugUnitTest",
        "android/gradlew -p android assembleDebug assembleDebugAndroidTest",
        "adb devices",
        "adb shell getprop sys.boot_completed",
        "adb install -r app.apk",
        'git commit -m "Run connectedDebugAndroidTest through the runner"',
        "grep -rn connectedDebugAndroidTest docs",
        "echo adb shell am instrument",
        "cat emulator.log",
        "",
    ],
)
def test_a_command_the_hook_does_not_recognise_passes_untouched(command):
    assert hook(command) == (0, None)


def test_a_tool_other_than_bash_is_never_touched():
    assert hook(GRADLE, tool="Write") == (0, None)
    assert hook(GRADLE, tool="Read") == (0, None)


@pytest.mark.parametrize("text", ["", "not json", "[]", "null", '{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": {"command": 7}}'])
def test_unreadable_or_incomplete_input_passes_unchanged(text, tmp_path):
    out = []
    assert guard.run_hook(text, out=out.append, log_path=tmp_path / "g.log") == 0
    assert out == []


# --- it fails open --------------------------------------------------------------------------------


def test_an_exception_inside_the_hook_lets_the_command_run_and_is_logged(tmp_path):
    def broken(command):
        raise RuntimeError("bug in the hook")

    log = tmp_path / "sub" / "guard.log"
    assert hook(GRADLE, log_path=log, decide_fn=broken) == (0, None)
    text = log.read_text(encoding="utf-8")
    assert "RuntimeError: bug in the hook" in text and "Traceback" in text


def test_a_hook_that_cannot_even_write_its_log_still_lets_the_command_run(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the log directory should be", encoding="utf-8")

    def broken(command):
        raise RuntimeError("x")

    assert hook(GRADLE, log_path=blocker / "guard.log", decide_fn=broken) == (0, None)


def test_main_without_the_hook_flag_only_prints_the_help(capsys):
    assert guard.main([]) == 0
    assert "PreToolUse" in capsys.readouterr().out


# --- splitting a line into commands ------------------------------------------------------------


def test_quotes_and_redirects_do_not_split_a_command():
    assert [s.text.strip() for s in guard.split_segments('echo "a && b" ; ls 2>&1 | wc -l')] == ['echo "a && b"', "ls 2>&1", "wc -l"]
    assert [s.text.strip() for s in guard.split_segments("a && b || c & d\ne")] == ["a", "b", "c", "d", "e"]


# --- the registration in .claude/settings.json ---------------------------------------------------


def settings():
    return json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]


def test_settings_register_the_guard_for_bash_next_to_the_unchanged_session_start_hook():
    hooks = settings()
    (session_start,) = hooks["SessionStart"]
    assert session_start == {
        "matcher": "startup|resume",
        "hooks": [{
            "type": "command",
            "command": 'uv run --no-project "$CLAUDE_PROJECT_DIR/scripts/verification_debt.py" --hook',
            "timeout": 60,
        }],
    }
    (pre_tool_use,) = hooks["PreToolUse"]
    assert pre_tool_use["matcher"] == "Bash"
    (entry,) = pre_tool_use["hooks"]
    assert entry["type"] == "command" and entry["command"].endswith('scripts/long_command_guard.py" --hook')
    assert (ROOT / "scripts" / "long_command_guard.py").is_file()
