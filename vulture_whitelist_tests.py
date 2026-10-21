# vulture whitelist for tests/ (#150). `uv run vulture tests vulture_whitelist_tests.py`
#
# tests/ is scanned on its own, apart from src/ and scripts/: scanned together, a function in src/ that only
# its own test calls would count as used and real dead code would hide. On its own, vulture sees each
# definition in tests/ that no other test references. Every name below is one that is used without a
# visible reference, or a deliberate part of a fake's shape; the reason is the comment above it.
# tests/test_vulture_whitelists.py fails when a name here is no longer reported, so an entry cannot outlive
# the code it excuses.

# pytest calls these by name: plugin hooks in tests/conftest.py and fixtures that apply themselves (autouse).
pytest_configure
pytest_deselected
pytest_sessionfinish
pytest_terminal_summary
pytest_testnodedown
_block_live_anthropic_unless_external
_gate_passes_unless_a_test_says_otherwise
_isolate_recent_rigs
_require_api_key
_block

# Fakes whose method or attribute names are the interface the code under test calls.
# tests/test_file_picker.py: a tkinter root.
withdraw
attributes
destroy
# tests/test_external_freshness.py: an HTTP response used as a context manager, read through `headers`.
headers
exc
# tests/test_vision_client.py: the Anthropic client and its tool-use block.
create
input
type
# Dataclass fields of the stand-in records in tests/test_review_form_rebuild.py: the code under test reads
# them by introspection, not by name.
size
pressure_psi
weight_lb
company
