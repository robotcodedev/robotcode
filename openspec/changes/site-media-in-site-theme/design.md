# Design

## Context

See proposal.md for the motivation. The current state, as of 2026-10-11:

- **Feature tour:**
  - `FeatureTour.astro` lists its slides as `{ video, duration, alt }` or `{ image, alt }`, with dark files from `docs/src/assets/screenshots/`. These are 14 `vscode-*.mp4` recordings and 5 `vscode-*.png`, 5 `pycharm-*.png` and 4 `neovim-*.png` screenshots, all 2072×1182 pixels.
  - The durations are written into the list.
  - `demo-player.ts` plays every `<video>` of the shown panel and slide from the start, and pauses them otherwise.
  - The enlarged view copies `currentSrc` and `currentTime` of the slide's video or image.
- **About page:** `about.mdx` shows `vscode-code-intelligence.mp4` and `vscode-run-tests.mp4` with plain `<video autoplay>` tags.
- **Get Started with VS Code:** `getting-started/vscode.mdx` shows three clips from the previous site: 320×550, 600×114 and 600×180 pixels, dark.
- **Guide components:** `ThemeImage` and `ThemeVideo` find a pair `<name>-light`/`<name>-dark` in `src/assets/screenshots/vscode/` by name. `ThemeVideo` gives a variant its source only when it is shown and near the viewport.
- **Recordings shared with the guide:**

  | Scene | Home page today | Guide pair |
  | --- | --- | --- |
  | 1 | `vscode-code-intelligence` | `writing-new-test` |
  | 2 | `vscode-run-tests` | `test-explorer-run` |
  | 3 | `vscode-debug` | `running-stepping` |
  | 4 | `vscode-documentation-viewer` | `viewer-browsing` |
  | 5 | `vscode-go-to-definition` | `finding-go-to-definition` |
  | 6 | `vscode-find-references` | `finding-peek-references` |
  | 9 | `vscode-debug-failure` | `running-stop-at-failure` |
  | 10 | `vscode-debug-console` | `running-evaluate-in-console` |
  | 12 | `vscode-robot-toml` | `config-robot-toml-editing` |
  | 13 | `vscode-profile` | `config-profile-debug` |
  | 14 | `vscode-repl` | `repl-start` |

  Scenes 7 (diagnostics), 8 (Keywords view) and 11 (log after a run) have no pair yet.
- **Capture scripts** in the git-ignored `playground/robotcode-demo/`:
  - `vscode/scene*.js` with `guide-recordings.sh` for the recordings.
  - `vscode/shots.js` for the home page's VS Code screenshots.
  - `pycharm/shots.sh`, which shoots in the IDE's current theme.
  - `nvim/screenshot.sh`, which renders Neovim via tmux, `ansi2html.py` and headless Chromium.
- **The harness** runs RobotCode as a development extension, with a stub instead of the Python extension.

## Goals / Non-Goals

**Goals:**

- One file per scene and theme, shared by the guide, the home page and the About page.
- The tour's playback rules (`demo-player.ts`) keep working unchanged.

**Non-Goals:**

- No new scenes or slides, and no changes to the tour's texts or order.
- No changes to the guide's components beyond what the About page and Get Started need.

## Decisions

### D1 One video element per slide, with a source that follows the theme

Each video slide keeps a single `<video>`. It carries the URLs of both variants as `data-light` and `data-dark`. A small script sets `src` to the variant of the current `data-theme` before the player starts it. When the theme changes, it swaps the source and restores `currentTime` and the play state. The player and the enlarged view need no change, because they work with the one video and its `currentSrc`.

- *Alternative:* two `<video>` elements per slide with Starlight's `light:sl-hidden` and `dark:sl-hidden`, like `ThemeVideo`. Rejected, because the player starts every video of a shown slide, so the hidden variant would load and play.

### D2 Screenshots as two images with Starlight's classes

A screenshot slide renders both variants with `light:sl-hidden` and `dark:sl-hidden`, lazily loaded, as `ThemeImage` does. The enlarged view copies the visible variant.

### D3 Files and names

- **Recordings:** the tour's VS Code recordings come from `screenshots/vscode/`, which holds the guide's pairs. The three new pairs are added there as well, for example as `tour-diagnostics`, `tour-keywords-view` and `tour-log-after-run`.
- **Screenshots:** the tour's screenshots become `screenshots/tour/<editor>-<subject>-{light,dark}.png`.
- **Removed:** the dark `screenshots/vscode-*.mp4`, `vscode-*.png`, `pycharm-*.png` and `neovim-*.png` files are deleted.
- **Durations:** the tour takes the longer of the two variants of each pair, measured from the files.
- **Lookup:** the tour finds its files with `import.meta.glob`, like the guide's components.

### D4 Captures in both themes

- **VS Code:**
  - `guide-recordings.sh` gets scenes 7, 8 and 11.
  - `shots.js` takes its screenshots with the theme helper of `guide.js` (`ctx.pair`).
- **PyCharm:** `shots.sh` runs once with the IDE's light theme and once with its dark theme. The theme is switched through the `ij` driver.
- **Neovim:** `screenshot.sh` runs once with `background=light` and once with `background=dark`. `ansi2html.py` takes the matching page background. That the color scheme in `init.lua` has a light variant is to be checked first.

### D5 About and Get Started with VS Code use ThemeVideo

- **About page:** it shows `writing-new-test` and `test-explorer-run`.
- **New clips:** the three Get Started clips become new pairs in `screenshots/vscode/`, for example `getting-started-add-recommendation`, `getting-started-create-environment` and `getting-started-first-test`.
- **Size:** each is recorded as a full window and cropped to the part its step shows. Its width and height go to `ThemeVideo`, so the clips stay readable at the page's width, like the guide's detail screenshots.

### D6 The real Python extension for one recording

The clip "Python: Create Environment" needs the Python extension's command, and the harness has only a stub. For this recording, the real `ms-python.python` replaces the stub, copied into the harness's extensions folder like Even Better TOML. Taking it from the maintainer's VS Code installation needs their go-ahead first. After the recording, the stub returns.

## Risks / Trade-offs

- **[Risk] Two open changes.** The home page requirements this change builds on are still pending in `migrate-docs-to-starlight`, whose last tasks are the v2.8.0 deploy, and in `home-feature-tour-examples`. → Archive those two first. This change only adds requirements, so its own archive does not conflict with them.
- **[Risk] The menu of a development extension.** "Add to Workspace Recommendations" may be missing from the Extensions view's menu for an extension loaded for development. → Check first; if it is missing, install the packaged RobotCode VSIX in the harness for this clip.
- **[Trade-off] A light Neovim** looks less familiar than a dark one. → The maintainer decided on it.
- **[Risk] Light and dark takes differ in length.** → The tour takes the longer one (D3), so neither variant is cut short.
- **[Trade-off] Repository size:** minus 8.7 MB of dark home page recordings, plus three new recording pairs and the light variants of 14 screenshots. Overall the repository gets smaller.

## Migration Plan

None. The old file names are only referenced inside the site.
