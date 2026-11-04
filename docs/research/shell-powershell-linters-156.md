# Shell and PowerShell linters: facts for ticket #156

Research only. No recommendation. This file records what the tools' own docs, repos and package pages say, plus what the repo's files contain. Nothing was installed, downloaded or run: no linter, no repo script, no `Install-Module`, no `uv` command. Repo facts come from reading files and `grep`/`wc`/`git ls-files --eol`. Because no linter ran, **the number of findings on the current tree is UNKNOWN** (section 6).

All pages below were read on **2026-11-03**. Web pages were fetched through a summarising fetcher, so quotes are short; a figure that came only from a summary is flagged. "Page updated" is the stamp on the page when read.

Marker legend: **Confirmed** = stated in a primary source cited beside it (or, for repo facts, read in the cited file). **Indirect** = follows from two primary facts, or is stated only in a code comment or sample, not as a rule. **UNCONFIRMED** = no primary source found, or not checked; a settling test is in section 6.

Primary sources (short names used below):

- [SC-README] https://github.com/koalaman/shellcheck/blob/master/README.md (raw read)
- [SC-MAN] https://raw.githubusercontent.com/koalaman/shellcheck/master/shellcheck.1.md
- [SC-REL] https://api.github.com/repos/koalaman/shellcheck/releases/latest (v0.11.0, published 2025-08-04) and .../releases/tags/stable
- [SC-CHANGES] https://raw.githubusercontent.com/koalaman/shellcheck/master/CHANGELOG.md
- [SC-WIKI] shellcheck wiki: Directive, Ignore, SC1017, SC2148 (`raw.githubusercontent.com/wiki/koalaman/shellcheck/<Page>.md`)
- [SC-JSON] https://raw.githubusercontent.com/koalaman/shellcheck/master/src/ShellCheck/Formatter/JSON.hs
- [SCPY-PYPI] https://pypi.org/pypi/shellcheck-py/json (0.11.0.1)
- [SCPY-REPO] https://github.com/ryanrhee/shellcheck-py (`README.md`, `setup.cfg`, `setup.py`, raw)
- [SC-NPM] https://registry.npmjs.org/shellcheck (npm.com page returned 403)
- [PSSA-MSL] https://learn.microsoft.com/en-us/powershell/utility-modules/psscriptanalyzer/overview?view=ps-modules (updated 2026-03-20), [PSSA-USE] `.../using-scriptanalyzer` (updated 2026-08-24), [PSSA-RULES] `.../rules-recommendations` (updated 2026-01-28), [PSSA-WH] `.../rules/avoidusingwritehost` (updated 2026-07-21)
- [PSSA-INV] https://learn.microsoft.com/en-us/powershell/module/psscriptanalyzer/invoke-scriptanalyzer?view=ps-modules (updated 2026-08-24)
- [PSSA-GAL] https://www.powershellgallery.com/packages/PSScriptAnalyzer and the gallery API `https://www.powershellgallery.com/api/v2/Packages(Id='PSScriptAnalyzer',Version='1.25.0')`
- [PSSA-GH] https://github.com/PowerShell/PSScriptAnalyzer (`README.md`, `LICENSE`, `Engine/Generic/DiagnosticRecord.cs`, raw)
- [PSGET-INST] https://learn.microsoft.com/en-us/powershell/module/powershellget/install-module?view=powershellget-2.x (updated 2025-07-01); [PSGET-SAVE] `.../save-module?view=powershellget-2.x` (updated 2023-05-11)
- [PS-MODPATH] https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath?view=powershell-5.1 (updated 2026-08-25); [PS-EXECPOL] `.../about_execution_policies?view=powershell-5.1` (updated 2026-08-31)
- [REPO] files in this repo, cited by path and line.

---

## 1. shellcheck

### 1.1 Ways to obtain it on Windows

| Route | What it is | First or third party | Facts | Status | Source |
| --- | --- | --- | --- | --- | --- |
| GitHub release zip | `shellcheck-v0.11.0.zip`, 8,068,167 bytes. The README's "Windows, x86" link points at `shellcheck-stable.zip`, which has the identical size (8,068,167), so it is the same file. The release has no asset with "windows" in its name. | First party (koalaman) | Licence GPLv3 | Confirmed (README link, asset list); that the zip holds `shellcheck.exe` is Indirect (the PyPI wheel's `setup.cfg` extracts `shellcheck.exe` from a zip, section below); contents of the zip not opened | [SC-README], [SC-REL] |
| winget / scoop / choco | `winget install --id koalaman.shellcheck`, `scoop install shellcheck`, `choco install shellcheck`. These are system or user-profile package-manager installs. | Package managers; the winget id carries the author's namespace | Install path, size and whether a location can be chosen: not checked | Names Confirmed [SC-README]; paths UNCONFIRMED | [SC-README] |
| PyPI `shellcheck-py` | Wheel `shellcheck_py-0.11.0.1-py2.py3-none-win_amd64.whl`, 8,027,541 bytes. Other wheels: macOS x86_64, macOS arm64, manylinux x86_64; plus an sdist of 3,139 bytes. Wraps shellcheck 0.11.0 (version `0.11.0.1`, uploaded 2025-08-09). | **Third party.** Author "Ryan Rhee", no maintainer listed; MIT licence; repo `github.com/ryanrhee/shellcheck-py` | `setup.cfg` downloads the binary from `github.com/koalaman/shellcheck/releases/download/v0.11.0/...` at build time with a pinned sha256 (the linux entry shows `sha256 = 8c3be12b...`; the Windows entry shows `extract_path = shellcheck.exe` from a zip; its sha256 line was not shown). `setup.py` declares the wheel contains "no python source", tagged `py2.py3-none-<platform>`. README: after install "the `shellcheck` binary should be available in your environment ... (or `shellcheck.exe` on windows)". Requires Python >=3.9 (repo needs >=3.14, `pyproject.toml:6`). | Confirmed (listing, size, licence, author); wheel bundling the exe is Indirect (size 8.0 MB vs 8.07 MB zip, `setup.cfg`); Windows sha256 pinned: UNCONFIRMED | [SCPY-PYPI], [SCPY-REPO] |
| npm `shellcheck` | Version 4.1.0 ("Wrapper to download shellcheck"), MIT, maintainer `gunar`, repo `gunar/shellcheck`, unpacked size 41,159 bytes, `bin: bin/shellcheck.js`, no install/postinstall script, modified 2025-08-12. README: "On first execution `shellcheck` it's automatically downloaded." | **Third party** | Where the binary is downloaded to: not checked | Confirmed (registry metadata); download behaviour is README-only; location UNCONFIRMED | [SC-NPM] |

Could it be a uv dev dependency? `pyproject.toml:25-33` has a `[dependency-groups] dev` list (pytest, ruff pinned `==0.17.1`, vulture, ...) with `uv.lock`. A PyPI package with a `py2.py3-none-win_amd64` wheel is the same shape as that group's other entries. **UNCONFIRMED**: that uv selects the `win_amd64` wheel on this machine and where it puts `shellcheck.exe` (a venv `Scripts` folder is the usual console-script location, not verified here). The sdist (3,139 bytes) would download at build time, so a platform with no matching wheel would need network at install.

### 1.2 Dialects, directives, exit codes, formats

| Fact | Status | Source |
| --- | --- | --- |
| `-s/--shell` accepts `sh`, `bash`, `dash`, `ksh`, `busybox`. Without it the shell is deduced "from the file's shell directive, shebang, or .bash/.bats/.dash/.ksh extension". `sh` "refers to POSIX sh (not the system's), and will warn of portability issues." | Confirmed | [SC-MAN] |
| Warns "when using features not supported by the shebang". | Confirmed | [SC-README] |
| A `.sh` extension does **not** imply a shell. A file with no shebang, no directive and no `-s` gets SC2148 (shell unknown); fix with `-s bash`, `# shellcheck shell=...` before the first command, or a shebang. Files are passed explicitly on the command line, so an extensionless file such as `.githooks/pre-commit` is read by its shebang (`#!/bin/sh`). | Confirmed (SC2148 page, "A `.sh` extension doesn't imply a shell"); extensionless-with-shebang is Indirect (follows from shebang rule; man page says nothing about extensionless files) | [SC-WIKI] SC2148, [SC-MAN] |
| Inline: `# shellcheck disable=SC2059[,SC...]` scopes to the next command; placed right after or replacing the shebang it covers the whole file. Ranges (`SC3000-SC4000`) and `disable=all` (v0.8+) exist. | Confirmed | [SC-WIKI] Directive, Ignore; [SC-MAN] |
| A reason can be attached: "It is recommended to add a comment to document why a specific directive was used. The comment can be added on the preceding line. The comment can also be added at the end of the directive line." The reason is free text, not machine-read. | Confirmed | [SC-WIKI] Directive |
| Project-wide config: `.shellcheckrc` (or `shellcheckrc`) with `key=value` lines treated as file-wide directives; "Only the first-found file will be used"; `--norc` disables it. Also `-e CODE` on the command line and `SHELLCHECK_OPTS`. None of these is per-file or per-count. | Confirmed | [SC-WIKI] Directive, Ignore |
| Exit codes: 0 = all files scanned, no issues; 1 = scanned, some issues; 2 = some files could not be processed; 3 = bad syntax (e.g. unknown flag); 4 = bad options (e.g. unknown formatter). | Confirmed | [SC-MAN] "RETURN VALUES" |
| `-S/--severity`: `error`, `warning`, `info`, `style`; default `style`. Whether the exit code ignores findings below the `-S` floor is not stated. | Confirmed (values); exit-code effect UNCONFIRMED | [SC-MAN] |
| `-f` formats: `tty` (default), `gcc`, `checkstyle`, `diff`, `json1`, `json` ("legacy version of the json1 format"), `quiet`. The JSON formatter emits per comment: `file`, `line`, `endLine`, `column`, `endColumn`, `level`, `code`, `message`, `fix`. The legacy `json` encodes a flat array; the `json1` wrapper shape was not confirmed. | Confirmed (list, fields); json1 shape UNCONFIRMED | [SC-MAN], [SC-JSON] |
| The repo has no `# shellcheck` directive or `.shellcheckrc` today. | Confirmed | `grep -rn shellcheck` over `scripts/wizard_*.sh` returned no matches; no rc file seen in the listing |

### 1.3 Windows specifics

| Fact | Status | Source |
| --- | --- | --- |
| Carriage returns: SC1017 "Literal carriage return"; the script's `\r` are "treated literally, and results in all sorts strange bugs". v0.7.2 changelog: here-docs containing `\r` "are now parsed correctly, with better warnings". | Confirmed | [SC-WIKI] SC1017, [SC-CHANGES] |
| Changelog Windows lines: v0.4.7 statically linked binaries for Linux and Windows; v0.3.8 ANSI colours disabled on Windows; v0.11.0 diff output uses `/` as separator on Windows. | Confirmed | [SC-CHANGES] |
| `.gitattributes` (all 9 lines) sets `*.sh text eol=lf` and `.githooks/* text eol=lf` with the comment "otherwise bash fails on stray \r characters"; `*.pdf binary`. **No rule for `*.ps1`.** | Confirmed | [REPO] `.gitattributes:1-9` |
| Checked-out state: `git ls-files --eol` shows `scripts/wizard_web_revenuecat.sh` and `.githooks/pre-push` as `i/lf w/lf attr/text eol=lf`; `test-external.ps1` and `android/test-weekly.ps1` as `i/lf w/crlf attr/` (index LF, working tree CRLF, no attribute). | Confirmed | `git ls-files --eol` on 2026-11-03 |
| So on this machine the wizards and hooks are LF in the working tree (SC1017 should not fire); the `.ps1` files are CRLF (not shellcheck's concern). Not every wizard/hook was checked individually. | Indirect (attribute covers all `*.sh` and `.githooks/*`) | `.gitattributes`, one sample each |

---

## 2. PSScriptAnalyzer

### 2.1 Version, licence, size, platform

| Fact | Status | Source |
| --- | --- | --- |
| Current release **1.25.0**, published 2026-03-20; owners PowerShellTeam and andschwa; author Microsoft Corporation; `IsLatestVersion: true`; no dependencies; cmdlets `Get-ScriptAnalyzerRule`, `Invoke-ScriptAnalyzer`, `Invoke-Formatter`. | Confirmed | [PSSA-GAL] |
| Package size (the gallery `.nupkg`): **14,658,674 bytes**. Unpacked size on disk: not given. | Confirmed (package); unpacked UNCONFIRMED | [PSSA-GAL] API `PackageSize` |
| Licence: MIT ("Copyright (c) Microsoft Corporation."). | Confirmed | [PSSA-GH] `LICENSE` |
| Supported: "Windows PowerShell 5.1 or greater; PowerShell 7.2.11 or greater on Windows/Linux/macOS". Gallery `PowerShellVersion` is 5.1. (The GitHub README's build section names Windows PowerShell "5.0" as a build target and gives no support list; the two Microsoft sources agree on 5.1.) | Confirmed | [PSSA-MSL], [PSSA-GAL]; README [PSSA-GH] |
| Package contents include the module manifest, `Microsoft.Windows.PowerShell.ScriptAnalyzer.dll`, `...BuiltinRules.dll`, `Newtonsoft.Json.dll`, `Pluralize.NET.dll`, `Microsoft.PowerShell.CrossCompatibility.dll`, PS-version-specific builds, compatibility-profile JSON files, a `Settings` folder of presets, `.signature.p7s`. | Confirmed | [PSSA-GAL] file list |
| The dev machine has Windows PowerShell 5.1 and no pwsh 7 (owner's statement in the ticket brief, not re-checked). 5.1 is inside the supported range. | Confirmed (range) | [PSSA-MSL] |

### 2.2 Install options

| Option | Command / fact | Status | Source |
| --- | --- | --- | --- |
| `Install-Module` | `Install-Module -Name PSScriptAnalyzer -Force` (PowerShellGet 2.x) or `Install-PSResource -Name PSScriptAnalyzer -Reinstall` (PSResourceGet 1.x). | Confirmed | [PSSA-MSL] |
| `-Scope CurrentUser` | Needs no admin. On Windows PowerShell 5.1 the CurrentUser module folder is `$HOME\Documents\WindowsPowerShell\Modules` (AllUsers: `$Env:ProgramFiles\WindowsPowerShell\Modules`). The Install-Module page's own CurrentUser example quotes the PowerShell 7 folder `$HOME\Documents\PowerShell\Modules`. The default scope depends on the PowerShellGet version: in 1.x it is AllUsers (needs elevation); the CurrentUser-by-default rule is stated for PowerShell 6+. **`$HOME\Documents` can be redirected (e.g. OneDrive); not checked on this machine.** | Confirmed (paths, defaults); machine's `$HOME` mapping UNCONFIRMED | [PS-MODPATH], [PSGET-INST] |
| First-run prompts | "Dependent upon your repository settings, you might need to answer a prompt" (untrusted PSGallery). Whether a NuGet package-provider bootstrap is needed on this 5.1 and where it would install: not in the fetched pages. TLS 1.2 note: PSGallery requires TLS 1.2 (Windows PowerShell may need `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12`). | Confirmed (prompt, TLS note); NuGet bootstrap UNCONFIRMED | [PSGET-INST] |
| `Save-Module -Path <dir>` | "Saves a module and its dependencies on the local computer but doesn't install the module"; `-Path` is the destination; `-Force` creates a missing path; `-RequiredVersion` pins a version; output is `<dir>\PSScriptAnalyzer\<version>\`. | Confirmed (cmdlet behaviour); resulting folder layout for this module Indirect (the page's examples show `<Path>\<Module>\<version>`) | [PSGET-SAVE] |
| Importing from a project-local folder | "The saved module can then be copied into the appropriate `$env:PSModulePath` location of the offline machine." A path-based import (`Import-Module <full path>`) is the documented alternative to PSModulePath, but the fetched `about_PSModulePath` page does not state it; also the module version lookup uses `.psd1`/`.psm1` found recursively under each PSModulePath folder. | Save-Module sentence Confirmed; `Import-Module <path>` UNCONFIRMED from these sources (well-known, not verified here) | [PSGET-SAVE], [PS-MODPATH] |
| Execution policy | Windows client default is **Restricted**: it "prevents running of all script files, including ... module script files (`.psm1`)". Per-process override: `powershell.exe -ExecutionPolicy <policy>`, stored only in `$Env:PSExecutionPolicyPreference`, and it does not override a Group Policy setting. The module's `.psm1` is in the package. This machine's effective policy was **not read** (the repo's planner config calls `powershell web/test-external.ps1` and similar, so some policy permits `.ps1` files, but that is not a statement about this machine's setting). | Confirmed (policy semantics); this machine UNCONFIRMED | [PS-EXECPOL], [PSSA-GAL] file list; `scripts/test_planner_config.json:88,103,148` |

### 2.3 Running and gating

| Fact | Status | Source |
| --- | --- | --- |
| Syntax includes `-Path`, `-Recurse`, `-Severity <string[]>`, `-ExcludeRule`, `-IncludeRule`, `-Settings <Object>`, `-EnableExit`, `-ReportSummary`, `-SuppressedOnly`, `-IncludeSuppressed`, `-Fix`, `-ScriptDefinition`. "By default, it uses all rules." | Confirmed | [PSSA-INV] |
| `-Path` accepts a file or directory; analyses `.ps1`, `.psm1`, `.psd1`; "If the directory contains other types of files, they are ignored". So `.githooks/pre-commit` (no extension) is outside PSScriptAnalyzer's reach, as `.ps1` files are outside shellcheck's. | Confirmed | [PSSA-INV] |
| `-Severity` values: `Error`, `Warning`, `Information`, `ParseError`. It "filters the rule violation output only after running all rules". Parser errors are emitted as diagnostics since 1.18.0 and are suppressed only by leaving `ParseError` out of `-Severity`; they cannot be suppressed with the attribute. | Confirmed | [PSSA-INV], [PSSA-USE] |
| **Exit code.** The cmdlet writes objects to the pipeline. The docs describe an exit code only for `-EnableExit`: "exits the PowerShell sessions and returns an exit code equal to the number of error records" (CI use). No page says it sets `$LASTEXITCODE` or a non-zero exit otherwise. Whether "error records" means only `Error`-severity findings or all findings is not defined in the text. | Confirmed (what is documented); behaviour without `-EnableExit` is Indirect (documentation silent); meaning of "error records" UNCONFIRMED | [PSSA-INV] |
| Output object: `DiagnosticRecord` with `Message`, `Extent` (line/column live in `Extent`), `RuleName`, `Severity` (`Information=0, Warning=1, Error=2, ParseError=3`), `ScriptName`, `ScriptPath`, `RuleSuppressionID`, `SuggestedCorrections`, `IsSuppressed`. The default table view prints `RuleName Severity ScriptName Line Message` (the docs' sample header says `FileName` in places and `ScriptName` in others). | Confirmed | [PSSA-GH] `DiagnosticRecord.cs`, [PSSA-USE] |
| Excusing in a script: `[Diagnostics.CodeAnalysis.SuppressMessageAttribute('<RuleName>', '', Justification='...')]` on a script, function or parameter (a `param()` block is the anchor in the docs' script-level examples). Optional `Scope='Function'` and `Target='<regex or wildcard>'` narrow it. The Justification is a named argument, "optionally" added; it is shown by `-SuppressedOnly`. Suppressions are not reported unless `-SuppressedOnly` / `-IncludeSuppressed` is passed. | Confirmed | [PSSA-USE], [PSSA-INV] example 7 |
| Excusing in settings: a `.psd1` hashtable (path, hashtable, or preset name) with keys `CustomRulePath`, `ExcludeRules`, `IncludeDefaultRules`, `IncludeRules`, `RecurseCustomRulePath`, `Rules`, `Severity`. `ExcludeRules` is per rule across the whole run; none of the listed keys is per file or per count. Values in `-Settings` take precedence over same-named command-line parameters. A file named `PSScriptAnalyzerSettings.psd1` in the project root is found implicitly when the project root is passed as `-Path`. A comment is possible inside a `.psd1` (PowerShell syntax), but no machine-read reason field is documented. | Confirmed (keys, precedence, implicit file); reason-in-file Indirect | [PSSA-INV] notes, [PSSA-USE] |
| Built-in presets: `CmdletDesign`, `CodeFormatting` (+Allman/OTBS/Stroustrup), `DSC`, `PSGallery`, `ScriptFunctions`, `ScriptingStyle`, `ScriptSecurity`. | Confirmed | [PSSA-INV] |
| **`PSAvoidUsingWriteHost`**: Severity Warning, "Default state: Always enabled", "isn't configurable"; detects `Write-Host` "in functions that don't use the `Show` verb". Excusable only by a custom settings file or the suppression attribute. **In this repo no `.ps1` contains `Write-Host`** (`grep -c` = 0 in all 9; the string occurs only as the rule in the docs). The scripts print status through bare output and `Write-Error`/`throw` (`android/test-weekly.ps1:69,79,84`). The rule's text says it applies "in functions"; whether it fires at script top level (these scripts have no functions in the lines grepped) is not stated. | Confirmed (rule); relevance to this repo: 0 uses Confirmed; top-level behaviour UNCONFIRMED | [PSSA-WH], [PSSA-RULES], `grep` of the 9 `.ps1` files |
| Other rules the docs list as default Warning for script code: `AvoidUsingCmdletAliases`, `AvoidUsingPositionalParameters`, `AvoidUsingEmptyCatchBlock`, `AvoidGlobalVars`, `UseDeclaredVarsMoreThanAssignments`, `AvoidUsingInvokeExpression`, `UseShouldProcessForStateChangingFunctions`. Script Security Error rules include `AvoidUsingPlainTextForPassword`, `UsePSCredentialType`, `AvoidUsingConvertToSecureStringWithPlainText`. The page groups rules by recommendation and says "rules are grouped by the Severity defined in the implementation"; it does not mark which are on in a default run beyond "uses all rules". | Confirmed (list); the on/off column per rule not given | [PSSA-RULES] |

---

## 3. Calling from Python on Windows

How the repo already launches things: `scripts/static_checks.py:143-145` `run_capture` resolves `command[0]` with `shutil.which` (PATH/PATHEXT) and calls `subprocess.run([...], cwd=cwd, capture_output=True, text=True)`; `scripts/release_steps.py:23-34` `default_run_command` does the same without capture. The planner config calls `powershell ...` (Windows PowerShell 5.1) for `.ps1` wrappers (`scripts/test_planner_config.json:88,103,106,107,148,156`). No `.py` file in `scripts/` or `tests/` contains the word `ExecutionPolicy` (case-insensitive grep, 0 hits), so no Python caller passes it today.

None of the command lines below was run. They are shapes built from the documented flags.

| Tool | Candidate command line (Python list form) | Status |
| --- | --- | --- |
| shellcheck via uv dev dependency | `["uv", "run", "shellcheck", "-f", "json", "-S", "style", "--", "<files>"]`, or `["uv", "run", "--with", "shellcheck-py", "shellcheck", ...]` for a throwaway. `uv run ruff ...` is the form already used for ruff at `static_checks.py:45`. | Shape Indirect (ruff precedent + wheel's documented console `shellcheck`); entry-point name on Windows UNCONFIRMED |
| shellcheck as an unzipped binary | `[<path>\shellcheck.exe, "-f", "json", <files>]` with the folder either on PATH or given as an absolute path. | Indirect (zip is documented, contents not opened) |
| shellcheck file selection | `["shellcheck", "-s", "bash", "scripts/wizard_*.sh"]` needs the glob expanded by Python (no shell with `subprocess.run` as list); `.githooks/pre-commit` and `.githooks/pre-push` carry `#!/bin/sh` shebangs so need no `-s`. | Indirect |
| PSScriptAnalyzer from Windows PowerShell | `["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "<script text>"]` where the script text imports the module from a folder, runs `Invoke-ScriptAnalyzer -Path <files> -Settings <psd1> ... \| ConvertTo-Json -Depth 4` and ends in an explicit `exit`. `-File <wrapper.ps1>` is the other form. | Flags Confirmed in [PS-EXECPOL] (`-ExecutionPolicy`); `-NoProfile`/`-NonInteractive`/`-Command` are standard `powershell.exe` switches, not fetched here; whole line UNCONFIRMED until run |
| PSScriptAnalyzer exit code | Without `-EnableExit` there is no documented exit code (section 2.3), so a wrapper would have to count the returned objects itself and call `exit`. | Indirect |
| Windows exit-code count | `-EnableExit` returns a count; a Windows process exit code is an unsigned 32-bit integer (not looked up in a primary source). | UNCONFIRMED |

---

## 4. What `static_checks.py` and a baseline would plug into

Facts only. Cited as `file:line` in `scripts/static_checks.py` unless noted.

**A step.**

- `Step` is a frozen dataclass: `name`, `command` (list), `cwd` (default `REPO_ROOT`), `lint_context` (default `None`; comment at line 61: "an oxlint step whose warnings are judged against the allow-list") (lines 56-61).
- `steps_for(context, *, coverage)` returns the ordered list per context: core and streamlit (ruff, two vulture passes, optional coverage) lines 70-79; web (tsc, oxlint, knip) 80-85; scan-proxy (tsc, oxlint, knip, coverage floor) 86-92; anything else raises `KeyError` (93). `CONTEXTS = ("core", "streamlit", "web", "scan-proxy")` (96). There is no `android` here; Android's `session_end` is `scripts/android_session_end.py` (`docs/agents/static-checks.md:15`; docstring lines 9-13). That file was **not read** for this note.
- Dispatch in `run()`: for each step, `if step.lint_context: run_lint_step(...)` else `run_command(step.command, cwd=step.cwd).returncode` (lines 192-197). Every step runs even after a failure; the exit code is the first failing step's (198-203; doc `static-checks.md:19`).
- Where the inventory places the unlinted files: `scripts/*.sh`, `.githooks/*`, root `test-external.ps1` under **core**; `web/*.ps1` under **web**; `workers/scan-proxy/*.ps1` under **scan-proxy**; `android/*.ps1` under **android** (`docs/agents/static-checks.md:49,67,75,86`; all four say "#156").
- Planner triggers: each context's `session_end` string is in `scripts/test_planner_config.json` (core line 52-53, web 78, scan-proxy 94, android 147). Web and scan-proxy have `static_triggers` lists that include `scripts/static_allowlists/*` (lines 80, 96); the core entry's trigger list was not read.

**An allow-list with reasons.**

- One JSON file for oxlint only: `ALLOWLIST = REPO_ROOT/scripts/static_allowlists/oxlint.json` (line 40). Shape `{"_comment": ..., "entries": [{context, file, rule, count, reason}, ...]}` (`oxlint.json:1-54`, 7 entries, all `context: web`). `_comment` (line 2) says "every entry needs a reason".
- `load_allowlist(context, path)` returns the entries whose `context` matches (lines 102-104).
- Key used for judging: `(file, rule)` -> `count` (line 133). `reason` is read by no code in `static_checks.py`; it is enforced only by a test (below).
- Hard-wired to oxlint: `parse_oxlint` (107-119) maps oxlint JSON to `{file, rule, severity, line}`; `run_lint_step` (148-168) checks the binary exists with `shutil.which` (150-154), calls `step.command` through `capture` (155), expects JSON on stdout (156-161: otherwise prints output and returns the process's code, or 1), loads the allow-list for `step.lint_context` (162), prints `N finding(s), M allowed by scripts/static_allowlists/oxlint.json, K problem(s)` (167; the file name is literal), returns 1 on any problem.

**The "entry for a finding that no longer exists fails" rule.**

- `judge_lint(findings, allowlist)` (122-140): an `error` severity finding is a problem (128-129); each warning is counted per `(file, rule)` (130-132); a count above the allowed one is `new warning ... N found, M allowed` (134-136); an allowed count above the seen count is `stale allow-list entry ... lists N, M found` (137-139).
- The staleness rule is therefore exact-count: both fewer and more occurrences fail.
- Unit tests of those rules use fakes, in `tests/test_static_checks.py`: allowed passes (177-180); new warning (183-189); one more than allowed (192-196); stale entry (199-201); error beats an allowed warning (204-207); backslash paths normalised to `/` (210-213); lint step prints a new warning (216-224); missing binary names its own install command (227-233); non-JSON output returns the tool's code (236-240).
- File-hygiene tests over the real JSON: every entry has a context in `("web", "scan-proxy")`, an int count >= 1 and a non-blank `reason` (250-254); `(context, file, rule)` is unique (257-259); every listed file exists under the context's directory (262-265). The context tuple is hard-coded at line 252 and the root map at 263.
- Real-tree test, `tests/test_static_checks_real.py`: `pytestmark = [pytest.mark.core, pytest.mark.minor]` (26); the oxlint test is `@pytest.mark.slow` and `@pytest.mark.xdist_group("node")` and parametrised over `["web", "scan-proxy"]` (68-70); it skips if `node` is missing (72) or `web/node_modules/.bin` is absent (75-76), calls `sc.run_lint_step(step, capture=sc.run_capture, out=messages.append)` on the real tree and asserts `code == 0` (79-82). That is the test which fails when the JSON names a finding the tool no longer reports.
- Proof-of-failure pattern for the ruff step: a `tmp_path` probe file; clean source passes, `import os` fails with `F401` (85-98). The ticket's third criterion ("a deliberate defect makes it exit non-zero") matches the doc's section "Proving a check can fail" (`static-checks.md:95-97`: one deliberate defect per context, run once by hand, then removed).
- The vulture whitelists use the same idea by a different mechanism: a name that vulture stops reporting fails (`test_static_checks_real.py:50-56`).

**The doc that records decisions.** `docs/agents/static-checks.md`: "How they run" table (7-15), Decisions 1-4 (24-29), Allow-lists table (31-37), per-context inventory (39-86), "What a check cannot see" (88-93), "Proving a check can fail" (95-97). The #156 gap is named four times in the inventory (49, 67, 75, 86). Ticket #156 asks for the decision to be recorded there with the reason, whichever way it goes (`gh issue view 156`).

**Other facts relevant to plugging in.** `pyproject.toml:6` `requires-python = ">=3.14"`; dev group at 25-33. The repo rule that pins ruff exactly (`ruff==0.17.1`) is tested (`test_static_checks.py:96`). The CLAUDE.md rule asks for permission, and for a location, before any system-wide install; a project-level `uv add` is exempt.

---

## 5. The scripts under check

Lines from `wc -l` on 2026-11-03; constructs from `grep`/reading of the lines named. No script was executed.

### 5.1 Shell (shellcheck's input)

| File | Lines | Shebang | Constructs seen | Live or destructive |
| --- | --- | --- | --- | --- |
| `scripts/wizard_android_sign_in.sh` | 270 | `#!/usr/bin/env bash` | `set -euo pipefail` (9); `read -r`, `read -rs` (80, 87, 108, 122); `[[ ]]` (12 lines); arrays (`SKIPPED+=(...)`); here-string `<<<` (260); `mktemp` (133); `gh secret set` / `gh variable set` (146, 160); `keytool` (219); `curl` (258, GET to Supabase `/auth/v1/settings`) | Writes GitHub secrets/variables if `gh` is logged in; reads Supabase settings. No `rm`. |
| `scripts/wizard_android_upload_key.sh` | 380 | `#!/usr/bin/env bash` | `set -euo pipefail` (10); `read` (75, 82, 103, 117); `[[ ]]` (23 lines); arrays; two here-strings (303-304); `mktemp` (128); `gh secret set`/`variable set` (141, 155); `keytool` (about 12 lines, creates a keystore, 284-291); `"${JAVA_HOME:-}"` | Creates an Android upload keystore; writes GitHub secrets/variables. No `rm`. |
| `scripts/wizard_scan_proxy_live_accounts.sh` | 321 | `#!/usr/bin/env bash` | `set -euo pipefail` (9); `read` (80, 87, 108, 122); `[[ ]]` (16); arrays; `mktemp` (133); `gh secret set`/`variable set` (146, 160); `curl` x3 (208 POST Supabase password sign-in; 287; 311 GET `api.revenuecat.com/v2/.../virtual_currencies`) | Calls live Supabase and RevenueCat with real credentials; writes GitHub secrets/variables. No `rm`. |
| `scripts/wizard_web_external_test_user.sh` | 233 | `#!/usr/bin/env bash` | `set -euo pipefail` (9); `read`; `[[ ]]` (10); arrays; `mktemp` (133); `gh secret set`/`variable set`; `curl` (221, POST) | Calls a live endpoint; writes GitHub secrets/variables. No `rm`. |
| `scripts/wizard_web_revenuecat.sh` | 339 | `#!/usr/bin/env bash` | `set -euo pipefail` (9); `read`; `[[ ]]` (22); arrays; `mktemp` (133); `gh secret set`/`variable set`; `npx`/`npm`/`wrangler` mentioned (1 each; pattern count) | Writes GitHub secrets/variables. No `rm`. |
| `scripts/wizard_web_revenuecat_dashboard.sh` | 330 | `#!/usr/bin/env bash` | `set -euo pipefail` (9); `read`; `[[ ]]` (10); arrays; here-string (318 `<<<`); `mktemp` (133); `gh secret set`/`variable set`; `npm` (4 lines, one at ~316 captures output "to avoid SIGPIPE"); `ENV_FILE="/dev/null"` (204) | Runs an `npm` script; writes GitHub secrets/variables. No `rm`. |
| `.githooks/pre-commit` | 17 | `#!/bin/sh` | `case "$(git branch --show-current)"` ... `esac`; `if uv run scripts/generate_dashboard.py --from-snapshot >/dev/null 2>&1; then git add dashboard.svg`; `exit 0`. No `set -`. | Runs `git add dashboard.svg` on non-`ticket-*` branches. No delete, no live call (comment: "Runs no tests and contacts no registry"). |
| `.githooks/pre-push` | 16 | `#!/bin/sh` | `root="$(git rev-parse --show-toplevel)" \|\| exit 1`; `exec uv run "$root/scripts/external_gate.py" pre-push "$@"`. No `set -`. | Reads recorded status and package registries; "never runs a live test". |

Other facts about the wizards:

- Five of the six share an identical first **182 lines** (md5 of the lines above the `# STAGES:` marker is the same for `android_sign_in`, `scan_proxy_live_accounts`, `web_external_test_user`, `web_revenuecat`, `web_revenuecat_dashboard`); `android_upload_key` has a different 177-line library. Each file's header says the library is generated by the `/wizard` skill and "do not hand-edit". Any finding in the shared library would therefore be reported once per file (5 times) at the same line number. Confirmed (md5 of `head -n` to the marker line).
- Stage code (below the marker): 88, 203, 139, 51, 157, 148 lines respectively (same measurement).
- The issue text says "5 interactive bash wizards"; there are **6** `scripts/wizard_*.sh` files.
- No real here-doc (`<<WORD`) occurs in any shell file; every `<<` is a `<<<` here-string (`grep '<<' | grep -v '<<<'` = 0 hits).
- The wizards replace an env file via `mktemp` + `mv` (`wizard_web_revenuecat.sh:131-136`); no `rm` or `rm -rf` appears in any of the 8 shell files (`grep '\brm\b'` = 0 hits).
- `.shellcheckrc`, `# shellcheck source=` and `trap` do not appear in the wizards (`grep trap` over `wizard_*.sh`: no matches shown).

### 5.2 PowerShell (PSScriptAnalyzer's input)

| File | Lines | Constructs seen | Live, paid or destructive |
| --- | --- | --- | --- |
| `test-external.ps1` | 47 | `param(...)` (34); one `& uv run --project $repoRoot (Join-Path ...) \`...`; `exit $LASTEXITCODE` (47). No `Write-Host`, no `$ErrorActionPreference`. | Wrapper for the Python External suite (live, paid per the repo's notes). |
| `web/test-external.ps1` | 31 | `param` (21); `& uv run ... -- npm run test:external`; `exit $LASTEXITCODE` | Web External suite (live). |
| `android/release.ps1` | 48 | `param` (36); `& uv run ... android_release.py @extraArgs`; `exit $LASTEXITCODE` | Release script wrapper. |
| `android/test-external.ps1` | 56 | `param` (42); `& uv run ... external_wrapper.py ... run_external_android.py`; `exit` | Builds/installs on a device, runs External tests. |
| `android/test-weekly.ps1` | 194 | `$ErrorActionPreference = 'Stop'` (54); `Get-Command adb -ErrorAction SilentlyContinue` (59); `throw` (67, 69); `Write-Error` + `exit 1` (79-80, 84-85); `ConvertFrom-Json` (82); `& node ...liveTokenCli.ts` (77); `& npm run typecheck/deploy --prefix` (94, 96); `& .\gradlew.bat` (106); `& $adb install/shell/...` (103-143); `cmd /c "...>"` (177); backtick line continuations. No `Write-Host`, no `Invoke-Expression`, no `Remove-Item`. | **Live and paid:** signs in a funded Supabase account, **redeploys workers/scan-proxy to production**, buys scans (its own text: "nothing was deployed or bought" on failure). Pushes files to a device (`adb shell echo ... > marker`). |
| `workers/scan-proxy/release.ps1` | 46 | `param` (34); `& uv run ... scan_proxy_release.py @extraArgs`; `exit` | Release (deploy) wrapper. |
| `workers/scan-proxy/test-external.ps1` | 48 | `param` (36); `& uv run ... external_wrapper.py -- npm run test:external`; `exit` | External suite (live, paid with a ceiling). |
| `workers/scan-proxy/test-release.ps1` | 47 | `param` (29); sets `$env:SKIP_KEYS = '1'` (34) and `Remove-Item Env:\SKIP_KEYS -ErrorAction SilentlyContinue` (36); `npm run test:release` (39); `& uv run ... record_external_result.py` (45); `exit $testExitCode` | Release suite (live, paid). `Remove-Item` targets an environment variable only, no file. |
| `workers/scan-proxy/test-weekly.ps1` | 30 | `npm run test:weekly` (25); `& uv run ... record_external_result.py` (28); `exit $testExitCode` | Weekly suite (live, paid: "real, bounded calls"). |

Across all nine: `Write-Host` 0, `Invoke-Expression`/`iex` 0, `Remove-Item` of a file 0 (one env-var removal), `Set-StrictMode` 0 (grep), `$ErrorActionPreference` in 1. Working-tree line endings: CRLF (sampled on 2 of the 9; `.gitattributes` has no `*.ps1` rule).

---

## 6. Findings (not measured) and settling tests

**No linter was run. The findings count on the current tree is UNKNOWN for shellcheck and for PSScriptAnalyzer, so the size of any baseline is UNKNOWN.** What can be said from reading alone, with no number attached:

- The five wizards that share one 182-line library would repeat any finding in that library five times.
- `android/test-weekly.ps1` is the only PowerShell file with more than ~56 lines; the other eight are 30-56-line wrappers around `uv run` / `npm run` with `param` blocks.
- The default-on `PSAvoidUsingWriteHost` has nothing to match (0 uses). The other default rules' hit counts are unknown.

Settling tests (for the owner or a later session; each runs in a **throwaway folder**, not in the repo, and stays offline except for the one download):

1. shellcheck count, binary route:
   ```
   mkdir C:\shellcheck-test-156    (any empty folder on a non-C: drive)
   cd that folder; download shellcheck-v0.11.0.zip from the release page [SC-REL] into it; unzip there
   .\shellcheck.exe -f json "<repo>\scripts\wizard_android_sign_in.sh" ... (all 6 wizards + both .githooks files)
   ```
   Add `-s sh` only if a hook lacks a shebang (both have one). Record the exit code (0/1/2) and `ConvertFrom-Json | Group-Object code` for a per-code count, once with default severity and once with `-S warning`.
2. shellcheck via uv (settles section 1.1 and the wheel facts): in a scratch folder, `uv run --no-project --with shellcheck-py==0.11.0.1 shellcheck --version`. Read the printed version (expects 0.11.0) and `uv`'s cache/venv paths.
3. PSScriptAnalyzer count:
   ```
   powershell -NoProfile -Command "Save-Module -Name PSScriptAnalyzer -RequiredVersion 1.25.0 -Path C:\pssa-test-156 -Force"
   powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Module C:\pssa-test-156\PSScriptAnalyzer\1.25.0\PSScriptAnalyzer.psd1; Invoke-ScriptAnalyzer -Path '<repo>\android\test-weekly.ps1' | Group-Object RuleName | Select Count,Name"
   ```
   Repeat for the other eight `.ps1` files. Then `Get-ChildItem C:\pssa-test-156 -Recurse | Measure-Object Length -Sum` for the unpacked size and `Get-ExecutionPolicy -List` for the machine's policy, then delete the throwaway folder. (This is a `Save-Module` into a chosen folder, so nothing is installed and `$HOME\Documents` is untouched; the first `Save-Module` may still prompt about the NuGet provider/untrusted repository, which settles section 2.2.)
4. Exit-code behaviour: run the same `Invoke-ScriptAnalyzer` line, then `$LASTEXITCODE`; then with `-EnableExit`, to see whether the count equals the `Error` findings only or all findings.
5. CRLF effect: run test 3 on one `.ps1` and again on a copy converted to LF; compare the counts.

---

## 7. Other UNCONFIRMED items

| Item | What would settle it |
| --- | --- |
| Whether the Windows `shellcheck.exe` in the GitHub zip is 32-bit ("Windows, x86" per the README link label) and whether the `win_amd64` wheel carries the same exe. | Unzip the release zip and the wheel (`.whl` is a zip) into two empty folders; compare the two `shellcheck.exe` hashes. |
| Whether shellcheck's exit code respects `-S` (e.g. exit 0 when only `style` findings exist and `-S warning` is given). | Run `shellcheck -S error` on a file with only warnings and read the exit code. |
| The `json1` output wrapper (`{"comments": [...]}`?) versus the flat `json` array. | Run `-f json1` on one file. |
| Install sizes and paths for winget / scoop / choco, and whether a location can be chosen. | Each manager's own docs; the CLAUDE.md rule requires asking the owner before any such install. |
| Whether `uv` places `shellcheck.exe` in the venv `Scripts` folder under that name. | Test 2, then `uv run where shellcheck`. |
| `Import-Module <full path>` as documented behaviour (fetched PSModulePath page does not state it). | Test 3 (works or errors). |
| Whether `Install-Module` on this 5.1 needs the NuGet package-provider bootstrap and where that installs (C: or elsewhere). | Test 3's first `Save-Module` shows the prompt; the provider's install folder is shown by `Get-PackageProvider -ListAvailable`. |
| Machine's effective execution policy and whether `$HOME\Documents` is redirected (OneDrive). | `Get-ExecutionPolicy -List`; `[Environment]::GetFolderPath('MyDocuments')`. |
| Whether `PSAvoidUsingWriteHost` fires at script top level (not inside a function). | Moot for this repo today (0 uses). |
| Whether the 14.7 MB gallery package expands to a few tens of MB on disk, and the size of the NuGet provider. | Test 3's `Measure-Object`. |
| Whether `Invoke-ScriptAnalyzer` sets any exit code without `-EnableExit`, and what "number of error records" counts. | Test 4. |
| The `android_session_end.py` structure (where `android/*.ps1` checks would plug in) and the core entry's `static_triggers`. | Read `scripts/android_session_end.py` and `scripts/test_planner_config.json` lines 40-60. |
| Whether the six shell files and nine `.ps1` files actually fall in the default lint set of each tool without errors from non-ASCII text (the wizards are UTF-8 with box-drawing characters, per `file`: "Unicode text, UTF-8 text executable"); and whether PSScriptAnalyzer flags `.ps1` files with no BOM (rule `PSUseBOMForUnicodeEncodedFile`). | Tests 1 and 3 (the second applies only if any `.ps1` contains non-ASCII characters; not checked). |
