# Tasks: home-feature-tour-examples

## 1. Series with terminal slides

- [x] 1.1 In `FeatureTour.astro`, let a slide be a screenshot, a recording or a terminal session, turn every feature's panel into a series (Code intelligence starts with its existing recording), and remove the panel kinds `video` and `terminal` (D1). Verify that `npm run docs:build` succeeds and that the home page in `npm run docs:preview` shows the same examples as before, now with dots on every feature.
- [x] 1.2 Make the steps of a terminal slide replay whenever the slide is shown, hold with pause, hover and out of view, and show complete under reduced motion (D2). Verify with a Playwright check against the preview, for a series with two terminal slides:
  - a selected terminal slide shows its first step first and all steps after `steps × STEP_DELAY`
  - selecting it again starts it from the first step
  - with `reducedMotion: "reduce"` it shows all steps at once
  - the window keeps its height between slides
- [x] 1.3 Give the videos in slides `preload="none"`, except the first slide of the first feature (D3). Verify in the preview that loading the home page requests no recording besides that one, and that each recording plays when its slide is shown.

## 2. Harness

- [x] 2.1 Turn on screencast mode in the VS Code harness with the settings and the key filter of D4 (`screencast.js`). Repeat the test frame at the size the home page shows recordings. Verify that F12 and Ctrl+Space appear, that Enter, Escape, End and typed text do not, and that no click indicator of VS Code appears. Document `screencast.js` in the playground README.
- [x] 2.2 Install Even Better TOML into the harness from a VSIX and map `robot.toml` to the checkout's `docs/public/schemas/robot.toml.json` (D6). Verify that completion in `robot.toml` offers the settings and that a hover shows a setting's description.

## 3. VS Code recordings

- [x] 3.1 Switch scene 1 from API calls to the shortcuts (D4), then record scenes 1–4 again with screencast mode (D5). Verify each new MP4 against the old one: same content and length within a few seconds, shortcuts visible. Keep the old file wherever more than the overlay differs, and report it.
- [x] 3.2 Record the Code intelligence scenes Go to Definition, Find References, Diagnostics and Keywords view (D6). Verify that each MP4 is 2072×1182 H.264, 8–15 s long, shows its shortcut in the overlay and starts and ends on a calm frame.
- [x] 3.3 Record the Run, debug & test explorer scenes stopping at a failure, Debug Console and log after a run (D6). Verify the same as 3.2. For stopping at a failure, verify that no breakpoint is set and that the debugger stops at the failing keyword of `Login Works`.
- [x] 3.4 Record the configuration scenes `robot.toml` schema and profile in VS Code, and the REPL scene in VS Code (D6). Verify the same as 3.2. For the profile, verify that the run uses the `ci` profile's `BASE_URL`.
- [x] 3.5 Convert the recordings with the README's `ffmpeg` command into `docs/src/assets/screenshots/vscode-<topic>.mp4`. Verify that `git status` shows only the new and replaced recordings there and that each one plays in the preview.

## 4. Terminal sessions

- [x] 4.1 Add the sessions of D7 to `capture.sh` and the CI workflow file to the demo project. Verify that `./capture.sh` runs through and prints every new section.
- [x] 4.2 Put the abridged output into the slides of Run, debug & test explorer, One config everywhere, Powerful CLI and Interactive REPL, in the spec's order. Verify that every command and output line in `FeatureTour.astro` appears in the output of `capture.sh`, abridged but not changed.

## 5. Texts, links and checks

- [x] 5.1 Adjust the feature descriptions and links (D8). Verify that `npm run docs:build` succeeds without link errors and that `/llms-full.txt` contains the new descriptions but no terminal session.
- [x] 5.2 Run a Playwright check of the home page against the spec's scenarios: the order of the examples per feature, the window titles, selecting each example, holding, pause, reduced motion, enlarging a recording, and a terminal slide replaying. Verify that all checks pass.
- [x] 5.3 Run Lighthouse on the home page for mobile and desktop. Verify that performance, accessibility, best practices and SEO are no lower than after 98d8b0ea (desktop performance 99, the rest 100), and that the number of requests on load did not grow.
- [x] 5.4 Run `openspec validate home-feature-tour-examples --strict`, and verify that it passes.
