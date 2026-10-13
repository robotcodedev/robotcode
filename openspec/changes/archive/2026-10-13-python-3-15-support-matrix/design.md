# Design: python-3-15-support-matrix

## Context

See proposal.md for the motivation. The current state:

- The Python classifiers of the newest patch release of each Robot Framework minor version on PyPI, checked on 2026-10-13. That is the release hatch installs with `robotframework~=X.Y.0`:

  | RF minor | newest release | Python classifiers |
  |---|---|---|
  | 5.0 | 5.0.1 | 3.6 – 3.10 |
  | 6.0 | 6.0.2 | 3.6 – 3.11 |
  | 6.1 | 6.1.1 | 3.6 – 3.12 |
  | 7.0 | 7.0.1 | 3.8 – 3.12 |
  | 7.1 | 7.1.1 | 3.8 – 3.13 |
  | 7.2 | 7.2.2 | 3.8 – 3.13 |
  | 7.3 | 7.3.2 | 3.8 – 3.14 |
  | 7.4 | 7.4.2 | 3.8 – 3.14 |
  | 7.5 | 7.5 | 3.8 – 3.15 |

- A run of the test suite with CPython 3.15.0 on Linux (2026-10-13, every `test.rfXX` environment, hatch's data directory and interpreter redirected with `HATCH_DATA_DIR` and `HATCH_PYTHON`):
  - RF 7.3, 7.4 and 7.5 pass.
  - RF 5.0 to 7.2 fail the same two tests, which use the XML library as sample data: `test_library_name_in_an_import_links_to_the_documentation_viewer` and `TestLinksWithinThePage::test_code_and_names_in_builtin_and_xml`. Up to 7.2, RF imports `xml.etree.cElementTree` and reads its `VERSION`, which Python 3.15 no longer provides there. A suite with `Library    XML` fails the same way with `robot` and RF 7.2.
  - Every dependency installs from wheels for 3.15, including those with compiled parts (debugpy, coverage, PyYAML, html-to-markdown).
  - No API that Python 3.15 removes is used by RobotCode.
- The `test` job of `.github/workflows/build-test-package-publish.yml` has the dimensions `os` (3), `python-version` (3.10 to 3.14) and `robot-version` (`rf50` to `rf75`), 135 jobs in total. Each job installs its Python with `actions/setup-python`, installs Hatch with `pypa/hatch@install` and runs `hatch run test.<rf>:test`. The hatch `test` environment pins no Python. For such an environment Hatch prefers the Python version it runs on itself and only then falls back to any compatible interpreter; `HATCH_PYTHON` overrides both (`hatch/env/virtual.py`, Hatch 1.18.1). Locally, `hatch run test:test` therefore uses the Python that Hatch runs on.
- The first CI run of this change (run 38390955334, attempt 1) showed that the jobs did not test the Python of their matrix entry. The job for macOS, Python 3.14 and RF 7.5 ran its tests with `/Library/Frameworks/Python.framework/Versions/3.12`, although `actions/setup-python` had installed 3.14. None of the three jobs for Python 3.15 showed the `DeprecationWarning` for `ElementTree.VERSION` that RF 7.5 raises only on Python 3.15, while the local run on 3.15 shows it. `actions/setup-python` v6 provides the path of the Python it installs as the output `python-path`.
- The hatch `devel` matrix in `hatch.toml` is one `[[envs.devel.matrix]]` table, Python 3.10 to 3.14 × all nine RF versions (45 environments). Hatch allows several matrix tables per environment; each table adds the product of its own variables (hatch documentation, "Advanced environment configuration > Matrix"). The `matrix.rf.dependencies` overrides apply to every table.
- In a GitHub Actions matrix, an `exclude` entry removes every combination that matches all of its keys. An entry without `os` therefore applies to all three operating systems.
- The existing specs `vscode-extension-compatibility` and `intellij-python-environment` check only the minimum: Python 3.10 or newer with Robot Framework 5.0 or newer.

## Goals / Non-Goals

**Goals:**
- Declare Python 3.15, and make the CI matrix, the `devel` matrix and the documentation follow one rule: the Python versions each Robot Framework version officially supports.

**Non-Goals:**
- Any check, warning or refusal of an unsupported combination at runtime (spec "Unsupported combinations are not refused").
- Changes to the tests. The two failing tests are only run for unsupported combinations, which the CI no longer runs.
- The `test` matrix and the other hatch environments (`rfbeta`, `rfmaster`, `rfdevel`, `lint`, …).
- The news entry for the release.

## Decisions

### D1: Source of "officially supports"

A Robot Framework version supports the Python versions in the classifiers of its newest patch release on PyPI, the one hatch installs. The classifiers can be read the same way for every release, from the PyPI JSON API or the project page.

Rejected: the RF release notes. They are prose that has to be read release by release.

### D2: CI matrix with `exclude`

The `test` job keeps its three dimensions. `python-version` gains `"3.15"`, and an `exclude` list removes the 21 combinations that are not supported. The entries have no `os`, so they apply to every operating system:

| Python | excluded |
|---|---|
| 3.11 | rf50 |
| 3.12 | rf50, rf60 |
| 3.13 | rf50, rf60, rf61, rf70 |
| 3.14 | rf50, rf60, rf61, rf70, rf71, rf72 |
| 3.15 | rf50, rf60, rf61, rf70, rf71, rf72, rf73, rf74 |

That leaves 33 combinations on each operating system, 99 jobs. The steps, job names and artifact names stay as they are.

Alternatives:
- A dimension whose values are objects with the Python and RF version, one entry per supported combination (33). It lists the supported set directly, but every step, job name and artifact name would have to change from `matrix.python-version` and `matrix.robot-version` to the object's fields.
- `include` with pairs of Python and RF version: GitHub Actions overwrites the values added by one `include` entry with those of the next one, so this would need one entry per operating system and combination (99).
- A preceding job that builds the matrix from `hatch env show`: an extra job and a script, for a list that changes only when an RF or Python version is added.

### D3: `devel` matrix as one table per Python range

The single table is replaced by six, one for each group of RF versions with the same Python range, in the order of the documentation table:

| Python | RF |
|---|---|
| 3.10 | rf50 |
| 3.10, 3.11 | rf60 |
| 3.10 – 3.12 | rf61, rf70 |
| 3.10 – 3.13 | rf71, rf72 |
| 3.10 – 3.14 | rf73, rf74 |
| 3.10 – 3.15 | rf75 |

The environment names stay `devel.py<python>-<rf>`. A new RF version is either added to the table of its Python range or gets a new table.

Rejected: one table per Python version. It has as many tables, but repeats every RF version on several lines and does not mirror the documentation table.

### D4: `test` matrix unchanged

`hatch run test:test` keeps running all nine RF versions with the default Python (maintainer decision). With a default Python newer than an RF version supports, Robot Framework may fail there, as RF 5.0 to 7.2 do on Python 3.15. `CONTRIBUTING.md` and `AGENTS.md` say so and name the CI as authoritative.

Rejected: a fixed Python per `test.rfXX` environment, the newest one its RF version supports. The CI would have to move to the `devel` environments, because a fixed Python overrides the interpreter of the job, and every contributor would need six Python versions locally.

### D5: Package metadata

The 12 `pyproject.toml` files (the root package and the 11 packages) gain the classifier `Programming Language :: Python :: 3.15`. `requires-python = ">=3.10"` and `robotframework>=5.0.0` stay without an upper bound, because unsupported combinations are not refused (spec).

### D6: Documentation

- `README.md`, the long description on PyPI, and `docs/src/content/docs/getting-started/index.mdx` keep "Python 3.10 or newer" and "Robot Framework 5.0 or newer" as the minimum. Each adds the table of supported combinations from the spec and a short paragraph:
  - only these combinations are tested in the CI, to keep the effort low;
  - other combinations may work, but using them is the user's responsibility;
  - for example, Robot Framework versions before 7.5 may not work with Python 3.15.

  Changed after the implementation (maintainer decision, aea2d308): the Get Started page no longer shows the table, which read as if each Robot Framework version ran only with the Python versions the CI tests. Its Python line says instead that the Python version has to be one the Robot Framework version supports, with Python 3.15 from Robot Framework 7.5 on as the example. The README keeps the table and the paragraph.
- `CONTRIBUTING.md`:
  - the section "Adding a new Robot Framework version to the matrix" says to take the Python range from the release's classifiers (D1) and where to add it (D2, D3, the documentation table);
  - a short paragraph next to it covers a new Python version: the classifier in all 12 `pyproject.toml`, `python-version` and the `exclude` entries in the CI, a `devel` table, the documentation table;
  - "Running Tests" gets the note from D4.
- `AGENTS.md`: the Python environments include `py3.15`, the `devel` matrix has 33 instead of 45 environments and only contains supported combinations, and `test:test` gets the note from D4.
- `.github/copilot-instructions.md` and `.github/instructions/python-development.instructions.md`: "Python 3.10–3.15 × Robot Framework 5.0–7.5, only the combinations Robot Framework supports" instead of "Python 3.10–3.14 × Robot Framework 5.0–7.5".

### D7: Release

The commit is `feat` without a BREAKING marker (maintainer decision). git-cliff lists `feat` commits under "Features" (`cliff.toml`), while it skips `chore` and `ci` commits, so the change appears in the changelog.

### D8: The Python of the CI jobs

The steps of the `test` job that run Hatch get `HATCH_PYTHON: ${{ steps.setup-python.outputs.python-path }}` (maintainer decision). Hatch then creates `test.<rf>` with exactly the Python the job installed, whatever Python Hatch itself runs on.

A step before the tests runs `hatch run test.<rf>:python -c …`. It prints the Python version of the test environment and fails when its major and minor version differ from the job's `python-version` (maintainer decision), so that a job can no longer test another Python unnoticed. It also creates the environment, and the test step reuses it.

Alternatives:
- Installing Hatch with pip into the Python of the job, so that Hatch prefers that version: it relies on Hatch's preference staying as it is, and it replaces `pypa/hatch@install`.
- Running the `devel` environments in the CI, whose Python is fixed: the bigger restructuring that D2 and D4 avoid.

## Risks / Trade-offs

- [Combinations that the CI tested until now, such as RF 6.1 on Python 3.13, lose their coverage, and a regression there goes unnoticed] → They are documented as untested and the user's responsibility. Every RF version stays tested on all the Python versions it declares.
- [A later RF patch release declares a newer Python, for example a 7.4.3 with Python 3.15] → The procedure in `CONTRIBUTING.md` (D6) reads the classifiers of the newest patch release whenever an RF or Python version is added. Such a release can be added the same way.
- [Python 3.15 has not run on macOS or Windows yet. On Windows, UTF-8 mode is the default from 3.15 on (PEP 686), so `open()` without an encoding reads UTF-8 there] → The first CI run with D8 runs the suite with Python 3.15 and RF 7.5 on both. A failure there is fixed before the change is archived.
- [With D8, jobs that ran Python 3.12 until now run the Python of their matrix entry, so failures may appear that the CI did not see before] → Task 4.1 looks at every failure of that run. Failures that this change causes are fixed before it is archived, others are reported to the maintainer.
- [`hatch run test:test` fails locally once the default Python is 3.15] → Documented (D4). `hatch run test.rf75:test` or the `devel` environments cover 3.15.

## Migration Plan

Users need do nothing. Rollback: revert the commit.
