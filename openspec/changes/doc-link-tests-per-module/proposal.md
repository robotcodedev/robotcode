# Proposal

## Why

The Python tests take about 4 minutes 20 seconds per Robot Framework version, on one core (Robot Framework 7.5: 4989 tests, 251 s of test time). `hatch run test:test` runs the nine versions one after the other. About 105 s of each run go into the fresh Python process that RobotCode starts for every library or variable file it has not cached yet: 304 such imports at about 0.35 s each.

Three test modules of the Documentation Viewer links cause 192 of these imports. Each of their tests writes the same project into a new temporary directory. The libraries therefore have a new path in every test, and no import is ever found in the library cache.

## What Changes

- `test_hover_documentation_links.py`, `test_documentation_target.py` and `test_signature_help_documentation_links.py` write their project once per module instead of once per test.
- The project files get a modification time older than the two seconds in which RobotCode does not trust a file state. The first import of each library then already goes into the library cache, and the module's later tests read it from there.
- `open_temp_document` in `tests/robotcode/language_server/robotframework/parts/conftest.py` opens a document with a version, as the editor does. Its namespace is then analyzed fresh, as it is today. Without the version, a shared project that is old enough would bring the namespace back from the namespace disk cache from the second test of a module on.
- The assertions of the tests stay the same.

Not part of this change:
- the other slow spots of the test run: the uncached model in the parity tests, the number of language-server starts, and the import cost of the import subprocess;
- `test_library_loading.py`, which tests the loading itself;
- the two smaller modules that write different libraries in each test (`test_libraries_of_one_module.py`, `test_completion_argument_docs.py`, together about 4.5 s).

Two findings of the analysis are only recorded in design.md.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

<!-- none -->

None, so the change sets `skip_specs: true` in `.openspec.yaml`. The change only rearranges the setup of tests. RobotCode's behaviour, and with it every requirement under `openspec/specs/`, stays the same. The fewer imports and the shorter run times are goals that design.md and tasks.md check, not requirements of RobotCode.

## Impact

- `tests/robotcode/language_server/robotframework/parts/conftest.py`: `open_temp_document` opens documents with a version. This applies to the eight modules that use the fixture.
- The three test modules: a project fixture with `scope="module"`. In `test_signature_help_documentation_links.py` this also affects the `document` fixture and the assertions that compare against `tmp_path`.
- Test time, measured on Robot Framework 7.5 with each module run alone. Each figure includes about 9 s for starting the shared language server.

  | module | before | after |
  |---|---|---|
  | hover | 51.1 s | 13.5 s |
  | documentation target | 23.6 s | 11.6 s |
  | signature help | 21.6 s | 13.0 s |

  That is about 58 s less per Robot Framework version, or about 8 to 9 minutes over the nine versions of `hatch run test:test`.
- No production code, no new dependency.
