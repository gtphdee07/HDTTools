"""Drift checks for the five testing documents (#64): the root `TESTING.md` and the one per context
(`tests/`, `web/`, `workers/scan-proxy/`, `android/`). A count or a closed gap cannot be checked
without running a suite, so the real counts were taken from real runs when the documents were
written. What does drift without anyone noticing, and what these tests pin, is the shape:

- every test file of a context is named in that context's document (the audit found 13 Web files,
  10 Python files and 8 Android files that no document mentioned);
- each document links to the agreed rules and to the planner, and every relative link resolves;
- every script a document names exists, and every `npm run` script Web's and Scan Proxy's documents
  run exists in that package's `package.json` (a renamed or removed command is the commonest way a
  documented command stops being real);
- the root document describes the session-end and release layers the rules add;
- every entry under "Known gaps" says whether it is closed or still open, and an open one names the
  ticket that tracks it, so a gap that was fixed cannot sit there looking open;
- a test file named as if it exists, exists (one named only to say it was retired or moved is fine).
"""

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "docs" / "test-audit" / "rules.md"
PLANNER = ROOT / "scripts" / "test_planner.py"

# document -> (globs of the test files it must name, how a file is named in prose)
CONTEXT_DOCS = {
    "tests/TESTING.md": (["tests/test_*.py"], "file"),
    "web/TESTING.md": (["web/src/**/*.test.ts", "web/src/**/*.test.tsx"], "file"),
    "workers/scan-proxy/TESTING.md": (["workers/scan-proxy/src/**/*.test.ts"], "file"),
    "android/TESTING.md": (["android/app/src/test/**/*Test.kt", "android/app/src/androidTest/**/*Test.kt"], "stem"),
}
ALL_DOCS = ["TESTING.md", *CONTEXT_DOCS]

# A heading under which a gap is listed, and the markers a gap's first words may carry.
GAPS_HEADING = re.compile(r"^## Known gaps", re.M)
GAP_STATUS = re.compile(
    r"^- (?:✅ )?\*\*(Closed|Retired|Obsolete|Open|Deliberately not tested|Not a gap)\b", re.M
)
RETIRED_WORDS = re.compile(r"retired|removed|went with|moved|deleted|no longer|replaced|renamed|history", re.I)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def gaps_section(text: str) -> str | None:
    match = GAPS_HEADING.search(text)
    if not match:
        return None
    rest = text[match.end():]
    end = re.search(r"^## ", rest, re.M)
    return rest[: end.start()] if end else rest


def top_level_bullets(section: str) -> list[str]:
    """Each top-level bullet with its continuation lines."""
    bullets: list[list[str]] = []
    for line in section.splitlines():
        if line.startswith("- "):
            bullets.append([line])
        elif bullets and (line.startswith("  ") or not line.strip()):
            bullets[-1].append(line)
    return ["\n".join(b).strip() for b in bullets]


@pytest.mark.parametrize("doc", CONTEXT_DOCS)
def test_every_test_file_of_a_context_is_named_in_its_document(doc):
    patterns, naming = CONTEXT_DOCS[doc]
    text = read(doc)
    missing = []
    for pattern in patterns:
        for path in sorted(ROOT.glob(pattern)):
            needle = path.stem if naming == "stem" else path.name
            if needle not in text:
                missing.append(path.relative_to(ROOT).as_posix())
    assert not missing, f"{doc} names none of: {missing}"


@pytest.mark.parametrize("doc", ALL_DOCS)
def test_each_document_links_to_the_rules_and_the_planner(doc):
    text = read(doc)
    base = (ROOT / doc).parent
    targets = {
        (base / target).resolve()
        for target in re.findall(r"\]\(([^)#\s]+)", text)
        if not re.match(r"[a-z]+:", target)
    }
    assert RULES.resolve() in targets, f"{doc} has no link to docs/test-audit/rules.md"
    assert PLANNER.resolve() in targets, f"{doc} has no link to scripts/test_planner.py"


@pytest.mark.parametrize("doc", ALL_DOCS)
def test_every_relative_link_in_a_document_resolves(doc):
    base = (ROOT / doc).parent
    broken = []
    for target in re.findall(r"\]\(([^)#\s]+)", read(doc)):
        if re.match(r"[a-z]+:", target):
            continue
        if not (base / target).exists():
            broken.append(target)
    assert not broken, f"{doc} links to files that do not exist: {broken}"


def test_the_root_document_describes_every_level_of_the_ladder():
    text = read("TESTING.md")
    for heading in ("## Run levels", "### Per issue", "### Session end", "### Release"):
        assert re.search(rf"^{re.escape(heading)}\b", text, re.M), f"root TESTING.md has no '{heading}' heading"
    for command in ("--level issue", "--level session", "--level release"):
        assert command in text, f"root TESTING.md never shows the planner's `{command}`"
    for context_doc in CONTEXT_DOCS:
        assert context_doc in text, f"root TESTING.md does not point at {context_doc}"


@pytest.mark.parametrize("doc", [d for d in CONTEXT_DOCS])
def test_every_known_gap_says_whether_it_is_closed_or_open_and_an_open_one_names_its_ticket(doc):
    section = gaps_section(read(doc))
    assert section is not None, f"{doc} has no '## Known gaps' section"
    bullets = top_level_bullets(section)
    assert bullets, f"{doc}'s Known gaps section lists nothing"
    unmarked = [b.splitlines()[0][:80] for b in bullets if not GAP_STATUS.match(b)]
    assert not unmarked, f"{doc}: gaps with no status (Closed, Retired, Obsolete, Open, Deliberately not tested, Not a gap): {unmarked}"
    untracked = [
        b.splitlines()[0][:80]
        for b in bullets
        if b.startswith("- **Open") and not re.search(r"#\d+|no ticket", b.splitlines()[0])
    ]
    assert not untracked, f"{doc}: open gaps that name neither a ticket nor 'no ticket': {untracked}"


# Gaps the audit (docs/test-audit/) found fixed in code but still listed as open in a document.
FIXED_GAP_WORDING = {
    "workers/scan-proxy/TESTING.md": [
        "No timeout on the Anthropic/RevenueCat",
        "spendCredit itself rejecting propagates out of runScan",
        "no `try/catch` around the spend call",
    ],
}


@pytest.mark.parametrize("doc", FIXED_GAP_WORDING)
def test_a_gap_the_code_has_since_closed_is_not_listed_as_open(doc):
    text = read(doc)
    still_there = [phrase for phrase in FIXED_GAP_WORDING[doc] if phrase in text]
    assert not still_there, f"{doc} still describes a closed gap as open: {still_there}"


SCRIPT_REFERENCE = re.compile(r"(?<![\w/.-])(?:\.\./)*(scripts/[\w.-]+\.(?:py|sh|ps1))")


@pytest.mark.parametrize("doc", ALL_DOCS)
def test_every_script_a_document_names_exists(doc):
    missing = sorted({
        name for name in SCRIPT_REFERENCE.findall(read(doc)) if not (ROOT / name).exists()
    })
    assert not missing, f"{doc} names scripts that do not exist: {missing}"


# document -> the package whose npm scripts its commands run
NPM_DOCS = {"web/TESTING.md": "web", "workers/scan-proxy/TESTING.md": "workers/scan-proxy"}
NPM_RUN = re.compile(r"npm (?:--prefix [\w/.-]+ )?run ([\w:-]+)")


@pytest.mark.parametrize("doc", NPM_DOCS)
def test_every_npm_script_a_context_document_runs_exists_in_its_package(doc):
    import json

    scripts = json.loads((ROOT / NPM_DOCS[doc] / "package.json").read_text(encoding="utf-8"))["scripts"]
    named = set(NPM_RUN.findall(read(doc)))
    missing = sorted(name for name in named if name not in scripts)
    assert not missing, f"{doc} runs npm scripts that {NPM_DOCS[doc]}/package.json does not have: {missing}"


def _test_file_names() -> set[str]:
    names: set[str] = set()
    for pattern in ("tests/*.py", "web/src/**/*.ts", "web/src/**/*.tsx", "workers/scan-proxy/src/**/*.ts",
                    "android/app/src/**/*.kt", "scripts/*.py"):
        names.update(p.name for p in ROOT.glob(pattern))
        names.update(p.stem for p in ROOT.glob(pattern) if p.suffix == ".kt")
    return names


NAMED_AS_A_TEST = re.compile(r"`(?:[\w./-]*/)?(test_\w+\.py|[\w.]+\.test\.tsx?|\w+Test\.kt)`")


@pytest.mark.parametrize("doc", ALL_DOCS)
def test_a_test_file_named_in_a_document_exists_unless_the_text_says_it_is_gone(doc):
    existing = _test_file_names()
    text = read(doc)
    missing = []
    for block in re.split(r"\n\s*\n|\n(?=\|)", text):
        if RETIRED_WORDS.search(block):
            continue
        for name in NAMED_AS_A_TEST.findall(block):
            if name not in existing and name.removesuffix(".kt") not in existing:
                missing.append(name)
    assert not missing, f"{doc} names test files that do not exist: {sorted(set(missing))}"
