# Proposal: python-3-15-support-matrix

## Why

Python 3.15 is released, and RobotCode does not declare it yet: the package classifiers, the CI matrix and the hatch `devel` matrix end at Python 3.14. A test run of the full suite on CPython 3.15.0 (Linux, 2026-10-13) passes with Robot Framework 7.3, 7.4 and 7.5, while RF 5.0 to 7.2 fail two tests each. RF up to 7.2 cannot initialize its XML library on Python 3.15, because `xml.etree.cElementTree` no longer provides `VERSION`; `robot` itself fails the same way. RF 7.5 is the first RF version that declares Python 3.15 on PyPI.

The CI tests every RF version on every Python version, 135 jobs on three operating systems, although many of these combinations are not supported by Robot Framework itself. For example, RF 5.0 declares Python up to 3.10 but is tested on 3.11 to 3.14. The README and the Get Started page say "Python 3.10 or newer" and "Robot Framework 5.0 or newer", which suggests that every combination is supported. Maintainer decision: RobotCode supports and tests only the combinations that Robot Framework officially supports, to keep the CI effort low. Other combinations may still work, but using them is the user's responsibility.

## What Changes

- RobotCode supports Python 3.15, with Robot Framework 7.5.
- Each Robot Framework version is supported on the Python versions that it officially supports, from Python 3.10 on. This also applies to the Python versions that are already supported, so RF 5.0 is then supported on Python 3.10 only:

  | Robot Framework | Python |
  |---|---|
  | 5.0 | 3.10 |
  | 6.0 | 3.10 – 3.11 |
  | 6.1, 7.0 | 3.10 – 3.12 |
  | 7.1, 7.2 | 3.10 – 3.13 |
  | 7.3, 7.4 | 3.10 – 3.14 |
  | 7.5 | 3.10 – 3.15 |

- The CI tests exactly these 33 combinations on Linux, macOS and Windows: 99 jobs instead of 135. The hatch `devel` matrix contains the same combinations.
- Each CI job tests with the Python of its combination. Until now Hatch created the test environments with the Python 3.12 it runs on itself, whatever Python the job had installed, as the first CI run of this change showed. A check step makes a job fail when its test environment runs another Python.
- Every RobotCode package lists Python 3.15 in its classifiers. `requires-python` stays `>=3.10` without an upper bound, and the Robot Framework dependency stays `>=5.0.0`.
- RobotCode does not check the combination at runtime. The VS Code extension, the IntelliJ plugin and the command line keep starting with any Python 3.10 or newer and Robot Framework 5.0 or newer.
- The README and the Get Started page show the table. They say that only these combinations are tested in CI, to keep the effort low, that other combinations may work but are the user's responsibility, and, as an example, that Robot Framework versions before 7.5 may not work with Python 3.15.
- The contributor documentation (`CONTRIBUTING.md`, `AGENTS.md` and the instruction files under `.github/`) describes the new matrix and how to derive it when a Robot Framework or Python version is added. The local `hatch run test:test` stays as it is and keeps running every Robot Framework version with the default Python; the documentation says that this can include unsupported combinations, where Robot Framework itself may fail, and that the CI is authoritative (maintainer decision).
- Release: the commit is `feat` without a BREAKING marker, although the narrower support also applies to the Python versions that are already supported (maintainer decision, as for the VS Code minimum 1.127).

## Capabilities

### New Capabilities

- `system-requirements`: The Python and Robot Framework versions RobotCode supports, the combinations it tests, and how the requirements are documented.

### Modified Capabilities

<!-- none: the minimum checks of `vscode-extension-compatibility` and `intellij-python-environment` (Python 3.10, Robot Framework 5.0) stay as they are -->

## Impact

- `pyproject.toml` and the `pyproject.toml` of the 11 packages under `packages/`: the classifier for Python 3.15.
- `hatch.toml`: the `devel` matrix.
- `.github/workflows/build-test-package-publish.yml`: the matrix of the `test` job.
- `README.md`, `docs/src/content/docs/getting-started/index.mdx`.
- `CONTRIBUTING.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/python-development.instructions.md`.
- Not affected: the code of the Python packages, the VS Code extension and the IntelliJ plugin, the tests and their regression outputs, and the other CI jobs.
