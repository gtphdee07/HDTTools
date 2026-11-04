"""Function tests for scripts/destructive_command_guard.py (#207), the PreToolUse hook that holds a delete, move
or overwrite whose target is a variable, glob, `~` or a place outside the project, and for its registration in
.claude/settings.json. The hook is fed the JSON the harness sends on stdin; nothing here deletes, moves or
writes anything (every command line below is only parsed)."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import destructive_command_guard as guard  # noqa: E402

PROJECT = r"G:\Work\Proj"  # Windows paths on purpose: the guard parses them with ntpath, so no host dependence
SCRATCH = r"C:\Users\Me\AppData\Local\Temp\claude\abc\def\scratchpad"
SCRATCH_FWD = SCRATCH.replace("\\", "/")
NOW = lambda: datetime(2026, 11, 4, 12, 0, 0)  # noqa: E731


LOG_FOR_TEST = [None]  # the log file of the current test, in its tmp_path, so no test writes a log into the working folder


@pytest.fixture(autouse=True)
def scratch_dirs(monkeypatch, tmp_path):
    LOG_FOR_TEST[0] = tmp_path / "destructive_command_guard.log"
    monkeypatch.setattr(guard, "SAFE_DIRS", (r"C:\Users\Me\AppData\Local\Temp\claude", r"C:\Users\Me\AppData\Local\Temp\hdttools-status"))


def verdict(command, tool="Bash", cwd=PROJECT, subagent=False):
    """The permission decision for one command line, or None when the command is let through untouched."""
    answer = guard.decide(command, tool=tool, project_root=PROJECT, cwd=cwd, subagent=subagent)
    if answer is None:
        return None
    decision = answer["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse" and decision["permissionDecisionReason"], decision
    return decision["permissionDecision"]


# --- what is held ----------------------------------------------------------------------------------


@pytest.mark.parametrize("command", [
    'rm -rf "$DIR"/*',  # ticket
    "rm -rf $UNSET/x",  # ticket
    "rm -rf ~/x",  # ticket (tilde)
    "rm /c/Users/x/file",  # ticket (outside, MSYS path)
    "rm ../outside",  # ticket (.. leaves the project)
    "echo hi > /c/Users/x/file",  # ticket (redirect outside)
    'rm -rf "$HOME/x"',
    "rm -rf *.tmp",  # a glob
    "rm -rf build/*",
    "rm -rf {a,b}",  # brace expansion
    "rm -rf $(cat list.txt)",  # command substitution
    "rm -rf `cat list.txt`",
    "rm 'C:/Users/x/f'",  # Windows path in forward slashes
    "rm -rf .",  # the project folder itself
    "rm -rf ..",
    "rm -rf /",
    "rmdir /c/Users/x/dir",
    "mv a.txt /c/Users/x/",  # a move out of the project
    "mv /c/Users/x/a.txt .",  # a move out of somewhere else
    "cp a.txt /c/Users/x/b.txt",  # an overwrite outside
    "cp -t /c/Users/x a.txt",
    "cp --target-directory=/c/Users/x a.txt",
    "dd if=a of=/c/Users/x/b",
    "truncate -s 0 /c/Users/x/f",
    "shred -u /c/Users/x/f",
    "unlink ../f",
    "cat a | tee /c/Users/x/f",  # a pipe does not hide the second command
    "ls && rm -rf /c/Users/x",  # nor does &&
    "ls; rm -rf /c/Users/x",
    "ls || rm -rf $X",
    "ls\nrm -rf $X",  # nor a newline
    "(rm -rf $X)",  # nor a subshell
    "echo $(rm -rf /c/Users/x)",  # nor a substitution
    'for f in a b; do rm "$f"; done',  # a loop variable
    "if true; then rm $X; fi",
    "xargs rm < list.txt",  # its targets come from another command
    "ls | xargs rm",
    "find $D -delete",
    "find /c/Users -name '*.log' -delete",
    "find . -name x -exec rm {} ; && find /c/Users -delete",
    "find /c/Users/x -exec rm -f {} +",
    "sed -i s/a/b/ /c/Users/x/f",  # the 'sed -i' on a real file outside
    "sed -i.bak -e s/a/b/ $F",
    "bash -c 'rm -rf $X'",  # a wrapper is read through
    'sh -c "rm -rf /c/Users/x"',
    'cmd /c "del C:\\Users\\x\\f.txt"',  # ticket (inside cmd /c)
    'cmd /c del /q %TEMP%\\*',
    "cmd /c rd /s /q C:\\Users\\x",
    'sudo rm -rf /c/Users/x',
    "FOO=1 rm -rf $X",
    "env FOO=1 rm -rf $X",
    "nohup rm -rf $X",
    "cd /c/Users/x && rm -rf foo",  # the cd moves the relative target out of the project
    "cd \"$X\" && rm foo",  # a cd to an unknown place makes a relative target unknown
    "cd .. && rm foo",
    "echo hi >> /c/Users/x/f",
    "echo hi >| /c/Users/x/f",
    "echo hi &> /c/Users/x/f",
    "echo hi 2> /c/Users/x/f",
    "echo hi > $OUT",
    "echo hi > $HOME/f",
    "echo hi >\"$OUT\"",
    "rm -- -rf $X",  # after -- every word is a target
    'echo "$(rm /c/x)"',  # review: a substitution inside double quotes still runs
    'echo "`rm /c/x`"',
    'x="$(rm -rf $X)"',
    'git commit -m "$(rm -rf /c/Users/x)"',
    'echo "a $(echo b; rm -rf $X) c"',
    "cat <<EOF\nbody\nEOF\nrm -rf $X",  # a command after a here-document is still read
    "cat <<-'END'\n\tbody\n\tEND\nrm -rf $Y",  # <<- lets the closing line be tab-indented, and the next command is read
    "cat <<< x\nrm -rf $X",  # a here-string has no body to skip
    "mv . elsewhere",  # review: the project folder as a SOURCE moves it away
    "mv . ../x",
])
def test_bash_commands_with_an_unresolved_or_outside_target_are_held_for_a_prompt(command):
    assert verdict(command) == "ask", command


@pytest.mark.parametrize("command", [
    "Remove-Item $env:TEMP\\* -Recurse",  # ticket
    "Remove-Item ~\\x",  # ticket
    "Remove-Item C:\\Users\\x\\f.txt",
    "Remove-Item -Path $dir -Recurse -Force",
    "Remove-Item -LiteralPath C:\\Users\\x -Recurse",
    "Remove-Item -Path:$dir",
    "Remove-Item '..\\other' -Recurse",
    "Remove-Item 'C:\\Users\\x\\*'",  # a wildcard inside quotes still globs in PowerShell
    "Remove-Item 'build\\*.obj'",
    "Remove-Item '~\\x'",  # PowerShell resolves ~ even inside quotes
    "Remove-Item \"$($x)\"",
    "Remove-Item .",
    "ri $x",
    "rm -Recurse $x",
    "del $x",
    "rd $x",
    "Remove-Item $x -WhatIf:$false",
    "Move-Item a.txt C:\\Users\\x\\",
    "Move-Item C:\\Users\\x\\a.txt .",
    "mi $a $b",
    "Copy-Item a.txt $dest",
    "Copy-Item a.txt C:\\Users\\x\\b.txt",
    "Rename-Item C:\\Users\\x\\a b",
    "Set-Content C:\\Users\\x\\f.txt 'hi'",
    "Set-Content -Path $p -Value hi",
    "Add-Content $log 'x'",
    "Clear-Content C:\\Users\\x\\f.txt",
    "'hi' | Out-File C:\\Users\\x\\f.txt",
    "'hi' | Out-File -FilePath $f",
    "New-Item -ItemType File -Path C:\\Users\\x\\f.txt -Force",
    "Get-Date > C:\\Users\\x\\f.txt",  # ticket (redirect)
    "Get-Date >> $log",
    "Get-Date *> C:\\Users\\x\\f.txt",
    "Get-ChildItem build | ForEach-Object { Remove-Item $_.FullName }",  # a script block
    "foreach ($f in $files) { Remove-Item $f }",
    "if ($x) { del $y }",
    "Get-ChildItem x; Remove-Item $y",
    "Get-ChildItem x | Remove-Item",  # nothing named: the pipe supplies the targets
    "Get-ChildItem x -Recurse | Remove-Item -Force",
    "& Remove-Item $x",
    "powershell -Command \"Remove-Item $x\"",
    "pwsh -c 'Remove-Item C:\\Users\\x'",
    "powershell.exe -NoProfile -Command Remove-Item C:\\Users\\x",
    "powershell -EncodedCommand AAAA",  # unreadable: held
    "Invoke-Expression $cmd",
    "iex $cmd",
    "cd C:\\Users\\x; Remove-Item foo",
    "Set-Location $x; Remove-Item foo",
    "[System.IO.File]::Delete($x)",
    "[IO.Directory]::Delete('C:\\x', $true)",
    "cmd /c \"rd /s /q C:\\Users\\x\"",
    "Remove-Item HKLM:\\Software\\x",  # review: a provider path is not a project path
    "Remove-Item HKCU:\\Software\\x -Recurse",
    "Remove-Item Cert:\\LocalMachine\\My\\ABC",
    "Get-Item C:\\x | Move-Item -Destination tmp",  # review: the pipeline supplies the sources
    "Get-ChildItem C:\\x | Copy-Item -Destination tmp",
    "Get-ChildItem build | Remove-Item -Recurse",
    "Get-ChildItem build | Rename-Item -NewName x",
    "Remove-Item @(\"C:\\x\")",  # review: an array or a splat is built at run time
    "Remove-Item @args",
    "Remove-Item -Path @paths",
    "Write-Output \"$(Remove-Item C:\\x)\"",  # a substitution inside double quotes
    "Write-Output \"a $(Remove-Item $x) b\"",
    "mv . elsewhere",
])
def test_powershell_commands_with_an_unresolved_or_outside_target_are_held_for_a_prompt(command):
    assert verdict(command, tool="PowerShell") == "ask", command


def test_a_held_command_is_also_held_when_the_same_text_arrives_through_the_other_tool():
    assert verdict("rm -rf $X", tool="PowerShell") == "ask"
    assert verdict("Remove-Item $X", tool="Bash") == "ask"


# --- what passes untouched --------------------------------------------------------------------------


@pytest.mark.parametrize("command", [
    "rm tmp/one.txt",  # ticket: one literal path inside the project
    "rm -rf build",
    "rm -rf ./build/",
    "rm -f a.txt b.txt",
    "rm -rf ./a/../b",  # still inside after the .. is resolved
    "rm -rf sub/dir/../../x",
    "rmdir empty_dir",
    "rm -rf /g/Work/Proj/build",  # an absolute path inside the project (MSYS form)
    "rm -rf G:/Work/Proj/build",
    "rm -rf 'G:\\Work\\Proj\\build'",
    "rm -rf g:/work/proj/BUILD",  # drive and folder names ignore case on Windows
    "mv a.txt dir/",
    "mv a.txt b.txt",
    "cp a.txt b.txt",
    "cp -r src dist",
    "mkdir -p out && rm -rf out/old",
    "cd sub && rm x",  # the cd stays inside
    "cd /g/Work/Proj/sub && rm x",
    "pushd sub; rm x; popd",
    "git branch -d x",  # ticket: git operations are exempt
    "git branch -D old && git worktree remove .claude/worktrees/ticket-1 --force",
    "git rm -rf somedir",
    "git clean -fdx",
    "git -C /c/elsewhere clean -fdx",
    "git checkout -- .",
    'git commit -m "rm -rf /"',  # ticket: quoted text that merely contains rm -rf
    "git commit -m \"don't Remove-Item $HOME\"",
    "echo 'rm -rf $X'",
    'echo "rm -rf $X"',
    "grep -r 'rm -rf' scripts",
    "gh issue create --body 'rm -rf ~'",
    "rm '$HOME'",  # single quotes: the literal name $HOME, a file in the project
    "rm 'a*b'",  # single quotes keep a star literal in bash
    "rm \\*",
    "rm -rf \\$X",
    "echo hi > out.txt",
    "echo hi >> out.txt",
    "echo hi > sub/out.txt",
    "ls > /dev/null",
    "ls 2>/dev/null",
    "ls >/dev/null 2>&1",
    "ls &>/dev/null",
    "ls 2>&1 | grep x",
    "ls 1>&2",
    "ls > /dev/stderr",
    "cat < /c/Users/x/in.txt",  # reading is not touching
    "cat /c/Users/x/in.txt",
    "ls /c/Users/x",
    "uv run pytest tests/ -q",
    "uv run scripts/x.py --out=/c/Users/x",
    "python -c \"import shutil; shutil.rmtree(x)\"",  # an interpreter's code is not read (documented gap)
    "find . -name '*.pyc' -delete",
    "find build -type f -name '*.o' -exec rm -f {} ;",
    "find /c/Users -name x",  # a search that deletes nothing
    "sed s/a/b/ /c/Users/x/f",  # no -i: prints, changes nothing
    "sed -i s/a/b/ src/f.py",
    "sed -n 1,5p /c/Users/x/f",
    "tee out.txt",
    "dd if=/c/Users/x/in of=out.bin",
    "bash -c 'rm -rf build'",
    "sh -c \"echo hi\"",
    "cmd /c dir",
    "ls ; ls",
    "",
    "   ",
    "echo",
    f"rm {SCRATCH_FWD}/x.md",  # the harness scratchpad is the sanctioned scratch space
    f"echo hi > {SCRATCH_FWD}/x.md",
    "rm C:/Users/Me/AppData/Local/Temp/hdttools-status/ticket-1.md",
    "rm -f tmp.txt 2>/dev/null",
    "rm -rf node_modules .venv",
    "cp a.txt .",  # the project folder as a destination is normal
    "mv a.txt .",
    "cp -r src/. dist",
    "echo \"$(date)\" > build.log",  # a harmless substitution in quotes
    "echo \"$(ls tmp)\"",
    "echo \"$(git rev-parse HEAD)\"",
    "echo \"`date` rm $X `whoami`\"",  # text between two backtick commands is not a command
    "git commit -m \"$(cat <<'EOF'\nfix the thing\ncp it to $HOME and rm -rf $X\nEOF\n)\"",  # a commit message in a here-document
    "cat > notes.md <<EOF\nrm -rf $X\nmv a /c/Users/x\nEOF",
    "cat <<-'END'\n\trm -rf $X\n\tEND",
    "cat <<EOF1 <<EOF2\nrm $X\nEOF1\nrm $Y\nEOF2",
    "cat <<< 'rm -rf $X'",  # a here-string is data
])
def test_bash_commands_with_only_named_targets_inside_the_project_pass_untouched(command):
    assert verdict(command) is None, command


@pytest.mark.parametrize("command", [
    "Remove-Item tmp\\one.txt",
    "Remove-Item .\\build -Recurse -Force",
    "Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue",
    "Remove-Item -Path build\\x.txt -Force",
    "Remove-Item -LiteralPath .\\build",
    "Remove-Item G:\\Work\\Proj\\build -Recurse",
    "Remove-Item 'G:\\Work\\Proj\\build'",
    "Remove-Item 'sub dir\\a.txt'",
    "Remove-Item Env:\\SKIP_KEYS -ErrorAction SilentlyContinue",  # an environment variable, not a file
    "Remove-Item Variable:foo",
    "Remove-Item Function:foo",
    "Remove-Item Alias:ll",
    "Remove-Item build -Include *.tmp",  # -Include names a filter, not a target
    "Remove-Item build -Filter *.tmp -Recurse",
    "Remove-Item build -Exclude *.keep",
    "Remove-Item build -Confirm:$false",
    "Remove-Item build -Recurse:$true",
    "Remove-Item build -WhatIf",
    "Move-Item a.txt sub\\",
    "Copy-Item a.txt b.txt",
    "Copy-Item src dist -Recurse",
    "Rename-Item a.txt b.txt",
    "Set-Content notes.txt $value",  # the value is data, only the path is a target
    "Set-Content -Path notes.txt -Value $value",
    "Set-Content notes.txt 'a/b'",
    "Add-Content notes.txt $line",
    "Clear-Content notes.txt",
    "'hi' | Out-File notes.txt",
    "$x | Out-File -FilePath notes.txt -Encoding utf8",
    "New-Item -ItemType Directory -Path out -Force",
    "New-Item out\\a.txt -ItemType File",
    "Get-Date > $null",
    "Get-Date > nul",
    "Get-Date > out.txt",
    "Get-Date >> out.txt",
    "Get-Date 2>&1 | Out-Null",
    "Get-Content f.txt | Out-File notes.txt",  # a pipeline that feeds DATA to a write is fine
    "Get-ChildItem build | Select-Object -First 3 | Out-File list.txt",
    "mv a.txt .",
    "Write-Output \"$(Get-Date)\"",
    "Write-Output \"Remove-Item is a cmdlet\"",
    "Remove-Item Env:\\Path -ErrorAction SilentlyContinue",
    "Get-Date *> $null",
    "Get-Date 2>$null",
    "Get-ChildItem C:\\Users\\x",
    "Get-Content C:\\Users\\x\\f.txt",
    "Get-ChildItem build | ForEach-Object { $_.Name }",
    "foreach ($f in $files) { Write-Output $f }",
    "if ($x) { Write-Output $y }",
    "git commit -m \"Remove-Item $x\"",
    "git branch -D $b",
    "Write-Output 'Remove-Item $x'",
    "Set-Location sub; Remove-Item a.txt",
    "cd sub; ri a.txt",
    "$a = 1; if ($a -gt 0) { echo ok }",
    "$env:X = 'y'",
    "& .\\android\\release.ps1",
    "uv run scripts/x.py",
    "powershell -NoProfile -Command Get-Date",
    "pwsh -c 'Remove-Item build'",
    "cmd /c \"del build\\x.tmp\"",
    "cmd /c rd /s /q build",
    "",
])
def test_powershell_commands_with_only_named_targets_inside_the_project_pass_untouched(command):
    assert verdict(command, tool="PowerShell") is None, command


def test_a_relative_target_is_resolved_against_the_working_directory_the_harness_reports():
    assert verdict("rm x", cwd=PROJECT + "\\sub") is None
    assert verdict("rm x", cwd=r"C:\Users\Me") == "ask"
    assert verdict("rm ../x", cwd=PROJECT + "\\sub") is None
    assert verdict("rm ../../x", cwd=PROJECT + "\\sub") == "ask"
    assert verdict("rm x", cwd=None) is None  # no cwd reported: the project root


def test_scratch_folders_allow_a_literal_path_but_never_a_glob_or_a_path_that_climbs_out():
    assert verdict(f"rm {SCRATCH_FWD}/a.txt") is None
    assert verdict(f"rm {SCRATCH_FWD}/*") == "ask"
    assert verdict(f"rm {SCRATCH_FWD}/../../../../other") == "ask"  # four levels up leaves the claude folder
    assert verdict("rm C:/Users/Me/AppData/Local/Temp/other.txt") == "ask"
    assert verdict("rm C:/Users/Me/AppData/Local/Temp/claude-other/x") == "ask"  # a sibling whose name starts the same
    assert verdict("rm -rf C:/Users/Me/AppData/Local/Temp/claude") == "ask"  # the scratch root itself
    assert verdict(f"Remove-Item '{SCRATCH}\\a.txt'", tool="PowerShell") is None


# Merge review of #207: every other test swaps SAFE_DIRS for a made-up pair, so a mutation that made the whole temp
# folder safe survived. This one reads the guard's own definition.
def test_the_real_scratch_folders_are_claude_and_hdttools_status_under_the_temp_folder(monkeypatch):
    monkeypatch.undo()  # drops the autouse override of SAFE_DIRS
    temp = guard._temp_dir()
    assert guard.SAFE_DIRS == (str(temp / "claude"), str(temp / "hdttools-status"))


def test_the_project_folder_itself_and_its_parents_are_outside_it():
    assert verdict(f"rm -rf {PROJECT.replace(chr(92), '/')}") == "ask"
    assert verdict("rm -rf G:/Work") == "ask"
    assert verdict("rm -rf G:/Work/Proj2/x") == "ask"  # a sibling whose name starts the same


# --- what the answer says -----------------------------------------------------------------------------


def test_the_reason_names_the_command_the_target_why_and_the_check_to_run_first():
    answer = guard.decide("rm -rf $UNSET/x", tool="Bash", project_root=PROJECT, cwd=PROJECT)
    reason = answer["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.startswith("destructive_command_guard:")
    assert "rm" in reason and "$UNSET/x" in reason and "variable" in reason
    assert "CLAUDE.md" in reason and "Resolve-Path" in reason and "printf" in reason
    reason = guard.decide("rm ../x", tool="Bash", project_root=PROJECT, cwd=PROJECT)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "outside the project" in reason
    reason = guard.decide("rm *.tmp", tool="Bash", project_root=PROJECT, cwd=PROJECT)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "wildcard" in reason
    reason = guard.decide("rm ~/x", tool="Bash", project_root=PROJECT, cwd=PROJECT)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "home folder" in reason


def test_one_line_with_many_held_targets_lists_each_command_once_and_stays_short():
    command = "; ".join(f"rm -rf $V{i}" for i in range(30))
    reason = guard.decide(command, tool="Bash", project_root=PROJECT, cwd=PROJECT)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.count("$V0") == 1 and "and 2" in reason and len(reason) < 1200


def test_the_answer_asks_and_never_rewrites_the_command():
    decision = guard.decide("rm -rf $X", tool="Bash", project_root=PROJECT, cwd=PROJECT)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "ask" and "updatedInput" not in decision


def test_a_command_from_a_sub_agent_is_refused_instead_of_asked():
    assert verdict("rm -rf $X", subagent=True) == "deny"
    assert verdict("Remove-Item $x", tool="PowerShell", subagent=True) == "deny"
    assert verdict("rm tmp/x", subagent=True) is None  # a safe command still passes in a sub-agent


# --- the tokenizer ------------------------------------------------------------------------------------


def words(text, dialect="bash"):
    return [[t.value for t in segment.tokens if t.kind == "word"] for segment in guard.tokenize(text, dialect)]


def test_quotes_keep_a_word_together_and_a_separator_inside_quotes_does_not_split():
    assert words('echo "a && b" ; ls') == [["echo", "a && b"], ["ls"]]
    assert words("echo 'a;b' | wc") == [["echo", "a;b"], ["wc"]]
    assert words("a && b || c & d\ne") == [["a"], ["b"], ["c"], ["d"], ["e"]]
    assert words("echo a\\ b") == [["echo", "a b"]]
    assert words('echo "a\\"b"') == [["echo", 'a"b']]
    assert words('rm "C:\\Users\\x"') == [["rm", "C:\\Users\\x"]]  # a backslash before an ordinary character stays


def test_powershell_quoting_uses_doubled_quotes_and_backtick_not_backslash():
    assert words("Write-Output 'it''s'", "powershell") == [["Write-Output", "it's"]]
    assert words('Write-Output "a""b"', "powershell") == [["Write-Output", 'a"b']]
    assert words('Write-Output "a`"b"', "powershell") == [["Write-Output", 'a"b']]
    assert words("Remove-Item C:\\x\\ ; ls", "powershell") == [["Remove-Item", "C:\\x\\"], ["ls"]]
    assert words("ForEach-Object { Remove-Item $_ }", "powershell") == [["ForEach-Object"], ["Remove-Item", "$_"]]
    assert words("echo ${env:X}", "powershell") == [["echo", "${env:X}"]]  # a brace after $ is a name, not a block


def test_an_unterminated_quote_does_not_crash_the_tokenizer():
    assert words('rm "abc') == [["rm", "abc"]]
    assert words("rm 'abc", "powershell") == [["rm", "abc"]]


def test_flags_mark_what_the_shell_will_expand():
    (segment,) = guard.tokenize("rm $A '$B' \"$C\" *.x '*.y' ~/z '~/w' \\$D", "bash")
    flags = {t.value: (t.dynamic, t.glob, t.tilde) for t in segment.tokens}
    assert flags["$A"] == (True, False, False)
    assert flags["$B"] == (False, False, False)
    assert flags["$C"] == (True, False, False)
    assert flags["*.x"] == (False, True, False)
    assert flags["*.y"] == (False, False, False)
    assert flags["~/z"] == (False, False, True)
    assert flags["~/w"] == (False, False, False)
    assert flags["$D"] == (False, False, False)


# --- failing closed -----------------------------------------------------------------------------------


def hook(payload, **kwargs):
    """Feeds one hook call; returns (exit code, parsed output or None)."""
    out = []
    text = payload if isinstance(payload, str) else json.dumps(payload)
    kwargs.setdefault("log_path", LOG_FOR_TEST[0])
    code = guard.run_hook(text, out=out.append, project_root=PROJECT, now=NOW, **kwargs)
    return code, (json.loads(out[0]) if out else None)


def call(command, tool="Bash", **extra):
    return {"tool_name": tool, "tool_input": {"command": command}, "hook_event_name": "PreToolUse", "cwd": PROJECT, **extra}


def test_a_held_command_prints_the_answer_and_exits_zero():
    code, answer = hook(call("rm -rf $X"))
    assert code == 0 and answer["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_a_passing_command_prints_nothing():
    assert hook(call("rm tmp/x")) == (0, None)


def test_input_that_starts_with_a_byte_order_mark_is_read_normally():
    assert hook("﻿" + json.dumps(call("rm tmp/x"))) == (0, None)
    code, answer = hook("﻿" + json.dumps(call("rm -rf $X")))
    assert code == 0 and "guard error" not in answer["hookSpecificOutput"]["permissionDecisionReason"]


def test_other_tools_and_missing_commands_pass_untouched():
    assert hook(call("rm -rf $X", tool="Edit")) == (0, None)
    assert hook({"tool_name": "Bash", "tool_input": {}}) == (0, None)
    assert hook({"tool_name": "Bash", "tool_input": {"command": 5}}) == (0, None)
    assert hook({"tool_name": "Bash"}) == (0, None)


def test_a_sub_agent_call_is_refused_through_the_hook_input():
    code, answer = hook(call("rm -rf $X", agent_id="a1", agent_type="Explore"))
    assert code == 0 and answer["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_crash_inside_the_guard_holds_the_command_for_a_prompt_and_is_logged(tmp_path):
    def boom(command, **kwargs):
        raise RuntimeError("bug in the guard")

    log = tmp_path / "guard.log"
    code, answer = hook(call("ls"), decide_fn=boom, log_path=log)
    decision = answer["hookSpecificOutput"]
    assert code == 0 and decision["permissionDecision"] == "ask"
    assert "guard error" in decision["permissionDecisionReason"] and "RuntimeError" in decision["permissionDecisionReason"]
    assert "bug in the guard" in log.read_text(encoding="utf-8") and "2026-11-04T12:00:00" in log.read_text(encoding="utf-8")


def test_a_crash_in_a_sub_agent_is_refused_not_asked():
    def boom(command, **kwargs):
        raise RuntimeError("bug")

    code, answer = hook(call("ls", agent_id="a1"), decide_fn=boom)
    assert code == 0 and answer["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("text", ["not json", "", "[]", "null", "42", '"rm -rf /"'])
def test_input_the_guard_cannot_read_holds_the_command_for_a_prompt(text, tmp_path):
    code, answer = hook(text, log_path=tmp_path / "g.log")
    assert code == 0 and answer["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_an_unwritable_log_does_not_stop_the_answer(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")

    def boom(command, **kwargs):
        raise RuntimeError("bug")

    code, answer = hook(call("ls"), decide_fn=boom, log_path=blocker / "sub" / "g.log")  # a file where a folder must be
    assert code == 0 and answer["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_the_project_folder_comes_from_the_hook_environment_then_from_the_reported_cwd(monkeypatch):
    out = []

    def run(command, cwd):
        out.clear()
        guard.run_hook(json.dumps(call(command, cwd=cwd)), out=out.append, log_path=LOG_FOR_TEST[0], now=NOW)
        return json.loads(out[0])["hookSpecificOutput"]["permissionDecision"] if out else None

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", PROJECT)
    assert run("rm tmp/x", PROJECT + "\\sub") is None
    assert run("rm tmp/x", r"C:\Elsewhere") == "ask"  # the environment names the project; the cwd is somewhere else
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    assert run("rm tmp/x", r"C:\Elsewhere") is None  # no environment value: the reported cwd stands in for the project
    assert run("rm ../x", r"C:\Elsewhere") == "ask"


def test_with_no_project_folder_known_every_target_is_outside():
    answer = guard.decide("rm tmp/x", tool="Bash", project_root=None, cwd=None)
    assert answer["hookSpecificOutput"]["permissionDecision"] == "ask"


# --- the script as the harness runs it -------------------------------------------------------------------


SCRIPT = ROOT / "scripts" / "destructive_command_guard.py"


def run_script(stdin_text, *args, env_extra=None):
    temp = str(LOG_FOR_TEST[0].parent)  # the script's log lives under the temp folder: keep it inside the test's tmp_path
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT), "TEMP": temp, "TMP": temp, "TMPDIR": temp, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], input=stdin_text, capture_output=True, text=True, timeout=60, env=env, check=False,
    )


def test_the_script_answers_a_held_command_on_stdout_with_exit_code_zero():
    done = run_script(json.dumps(call("rm -rf $X", cwd=str(ROOT))), "--hook")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_the_script_prints_nothing_for_a_passing_command_and_for_garbage_it_asks():
    done = run_script(json.dumps(call("ls tmp", cwd=str(ROOT))), "--hook")
    assert done.returncode == 0 and done.stdout == "", done.stderr
    done = run_script("this is not json", "--hook")
    assert done.returncode == 0 and json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_the_script_without_the_hook_flag_prints_its_description_and_blocks_nothing():
    done = run_script("")
    assert done.returncode == 0 and "PreToolUse" in done.stdout


def test_the_script_compiles_so_a_syntax_error_cannot_reach_a_session():
    compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")


# --- the registration in .claude/settings.json ----------------------------------------------------------


def registered():
    return json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]


def test_settings_register_the_guard_for_both_the_bash_and_the_powershell_tool():
    (entry,) = [e for e in registered() if "destructive_command_guard.py" in json.dumps(e)]
    assert set(entry["matcher"].split("|")) == {"Bash", "PowerShell"}
    (handler,) = entry["hooks"]
    assert handler["type"] == "command" and handler["command"].endswith('scripts/destructive_command_guard.py" --hook')
    assert handler["command"].startswith('uv run --no-project "$CLAUDE_PROJECT_DIR/')
    assert isinstance(handler["timeout"], int) and 5 <= handler["timeout"] <= 60
    assert SCRIPT.is_file()


def test_the_behaviour_has_a_page_under_docs_agents_and_the_project_claude_md_points_at_it_from_the_verify_section():
    page = ROOT / "docs" / "agents" / "destructive-command-guard.md"
    assert page.is_file() and "scripts/destructive_command_guard.py" in page.read_text(encoding="utf-8")
    claude_md = (ROOT / "Claude.md").read_text(encoding="utf-8")
    section = claude_md.split("## Verify before touching anything outside this repo", 1)[1].split("\n## ", 1)[0]
    assert "docs/agents/destructive-command-guard.md" in section


def test_registering_the_new_guard_left_the_device_command_guard_and_session_start_hook_as_they_were():
    hooks = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
    (session_start,) = hooks["SessionStart"]
    assert session_start["matcher"] == "startup|resume"
    (device,) = [e for e in hooks["PreToolUse"] if e["matcher"] == "Bash"]
    (handler,) = device["hooks"]
    assert handler["command"].endswith('scripts/long_command_guard.py" --hook')
