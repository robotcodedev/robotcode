# Tasks: python-3-15-support-matrix

## 1. Package metadata

- [x] 1.1 Add the classifier `"Programming Language :: Python :: 3.15"` directly after the one for 3.14 in `pyproject.toml` and in the `pyproject.toml` of the 11 packages under `packages/`; leave `requires-python` and the `robotframework` dependency as they are (design D5). Verify with a short script (`tomllib`) that each of the 12 files lists exactly the Python classifiers 3.10 to 3.15 and still has `requires-python = ">=3.10"`.

## 2. Test matrices

- [x] 2.1 Replace the `[[envs.devel.matrix]]` table in `hatch.toml` with the six tables of design D3; the `matrix.rf.dependencies` overrides stay. Verify:
  - `hatch env show --json` lists exactly the 33 `devel.*` environments of the spec table, among them `devel.py3.10-rf50` and `devel.py3.15-rf75`, and neither `devel.py3.11-rf50` nor `devel.py3.15-rf74`;
  - `hatch run devel.py3.10-rf50:python -c "import robot, sys; print(robot.__version__, sys.version_info[:2])"` prints RF 5.0.1 and `(3, 10)`;
  - `hatch run devel.py3.15-rf75:test` passes with a Python 3.15 that hatch finds on the `PATH`. For the run, put the interpreter and `HATCH_DATA_DIR` into the scratchpad, as for the run of 2026-10-13 (design Context).
- [x] 2.2 In the `test` job of `.github/workflows/build-test-package-publish.yml`, add `"3.15"` to `python-version` and the 21 `exclude` entries of design D2, without `os`. Verify with a short script (PyYAML) that expands the matrix: 99 jobs, 33 per operating system, and the 33 pairs of Python and RF version are the same as those of the `devel` environments from task 2.1.

## 3. Documentation

- [x] 3.1 In `README.md` and `docs/src/content/docs/getting-started/index.mdx`, add the table of supported combinations and the paragraph of design D6 to the requirements; the minimum lines stay. Verify that both tables match the spec table and that `npm run docs:build` passes.
- [x] 3.2 In `CONTRIBUTING.md`, extend "Adding a new Robot Framework version to the matrix" with the Python range from the classifiers and where it goes, add the paragraph for a new Python version, and add the note on `test:test` to "Running Tests" (design D4, D6). Verify that every file, setting and command the text names exists as written: `hatch env show` lists the `devel` environment it uses as an example.
- [x] 3.3 Update `AGENTS.md` (Python environments with `py3.15`, `devel` with 33 environments of supported combinations only, the note on `test:test`), `.github/copilot-instructions.md` and `.github/instructions/python-development.instructions.md` (design D6). Verify that `git grep -n "3.10–3.14" -- ':!openspec'` finds nothing.

## 4. CI

- [ ] 4.1 After the maintainer has pushed the commit, check its CI run: the `test` job runs 99 jobs, among them Python 3.15 with RF 7.5 on Linux, macOS and Windows, and all of them pass. Fix a failure on macOS or Windows before archiving (design, Risks).

## Workflow follow-up

- Archive the change once task 4.1 is done.
