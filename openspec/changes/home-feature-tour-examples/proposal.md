# Proposal: home-feature-tour-examples

## Why

The feature tour on the home page shows one example for most of its features: one recording for Code intelligence, one terminal session each for the configuration, the CLI and the REPL, and two recordings for running and debugging. Each feature covers much more than that, so readers never see, for example, the Documentation Viewer, Go to Definition into a Python library, Robocop's diagnostics, the debugger at the REPL prompt or a profile used in CI. The recordings have no sound, so the keyboard shortcuts they use stay invisible.

## What Changes

- **Several examples per feature.** Every feature of the tour except Multi-IDE shows a series of examples. Readers select an example by its dot, as in the Multi-IDE and the running-and-debugging demos today:
  - **Code intelligence**: the existing recording of writing a test (content unchanged), the Documentation Viewer, Go to Definition from a keyword call into the Python library, Find References, diagnostics of RobotCode and Robocop, and the Keywords view.
  - **Run, debug & test explorer**: the Test Explorer and debugging recordings, plus the debugger stopping at a failure, a keyword run in the Debug Console, the log opened after a run, and a terminal session of `robotcode robot-debug`.
  - **One config everywhere**: the existing `robot.toml` session, plus completion and hover in `robot.toml` from the JSON schema, selecting a profile in VS Code and running tests with it, and a CI workflow that runs the same profile.
  - **Powerful CLI**: separate sessions for discovering tests by tag and by test metadata, `robotcode analyze code`, the results of a run and `robotcode doc`.
  - **Interactive REPL**: the existing session, plus the Browser library at the prompt, the REPL in VS Code, and the debugger attached at the prompt, stopping in a keyword of a resource file.
  - **Multi-IDE** stays as it is.
- **Terminal sessions in a series.** A series of examples can contain terminal sessions; the steps of a session appear one by one each time it is shown.
- **Keyboard shortcuts in the recordings.** The VS Code recordings are made with VS Code's screencast mode, which shows the shortcuts pressed. The four existing VS Code recordings (code intelligence, test explorer, debugging, Documentation Viewer) are recorded again with it, with the same content.
- **Texts.** The description of a feature names what its examples show where it does not yet, and links only to existing pages.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `documentation-site`: the Home page requirement says that the feature tour shows examples of the selected feature; the Home page demos requirement lists the examples of each feature, adds terminal sessions as examples of a series and requires the VS Code recordings to show the shortcuts they press.

## Impact

- Depends on `migrate-docs-to-starlight`, which adds the Home page demos requirement and must be archived first.
- `docs/src/components/home/FeatureTour.astro` (terminal slides, a series for every feature, texts and links), `docs/src/components/home/demo-player.ts` (terminal steps of a slide animate when the slide is shown), `docs/src/styles/home.css` if the terminal styles move, and new MP4 recordings in `docs/src/assets/screenshots/`.
- The example project `playground/robotcode-demo` (git-ignored): new and re-recorded scenes for the VS Code harness, screencast mode settings, Even Better TOML in the harness, a CI workflow file and new sections in `capture.sh` for the terminal output.
- The feature tour takes longer to play through; readers can select any example directly. The home page gets more recordings, which must not slow down its first load.
- Some examples show features that ship with v2.8.0 (`robotcode doc`, `discover --by-test-metadata`, the Documentation Viewer); the new site goes live with that release.
