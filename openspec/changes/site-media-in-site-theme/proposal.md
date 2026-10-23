# Proposal

## Why

The VS Code guide shows its screenshots and recordings in the site's light or dark theme. The rest of the site does not:

- **Home page feature tour, About page:** they show editors in a dark theme only, which stands out on the light site.
- **Get Started with VS Code:** it still uses three small clips from the previous site, with an older VS Code.
- **Duplicate files:** the home page keeps its own dark copies of recordings the guide already has as light and dark pairs, 8.7 MB in total.

Decided on 2026-10-11 to plan now and maybe implement later.

## What Changes

- **Feature tour on the home page:**
  - Its recordings and its screenshots of VS Code, PyCharm and Neovim exist in a light and a dark variant. The tour shows the variant of the site's theme, in its window and in the enlarged view, and follows a theme switch.
  - Neovim is also taken with a light color scheme (maintainer's decision).
- **Recordings shared with the guide:** the tour uses the guide's recording pairs for the 11 scenes they share. Three scenes are recorded as new pairs: diagnostics while typing, the Keywords view and the log after a run. The home page's dark copies are deleted.
- **About page:** its two recordings use the guide's pairs.
- **Get Started with VS Code:** its three clips are recorded again in both themes. They show adding RobotCode to the workspace recommendations, creating a Python environment and running the first test.
- **Captures:** the playground scripts take the new pairs: the VS Code scenes and screenshots, PyCharm with its light and dark theme, and Neovim with a light and dark background. For the Python environment clip, the isolated harness uses the real Python extension instead of its stub.

Not in this change: the GIFs of the highlighting tip, which show one custom color scheme; the Mason screenshot on the Neovim page; the hero pictures and logos.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `documentation-site`: new requirements for screenshots and recordings in the site's theme on the home page, the About page and Get Started with VS Code.

## Impact

- **Docs site:**
  - `docs/src/components/home/FeatureTour.astro`, possibly `docs/src/components/home/demo-player.ts`.
  - `docs/src/content/docs/about.mdx` and `docs/src/content/docs/getting-started/vscode.mdx`.
  - `docs/src/assets/screenshots/`: the dark files of the tour and the About page are removed, while files that other pages show stay, and light and dark pairs are added.
- **Captures:** the git-ignored `playground/robotcode-demo/` (`vscode/`, `pycharm/`, `nvim/`).
- **Sequencing:** the home page requirements this change builds on are still pending in `migrate-docs-to-starlight` and `home-feature-tour-examples`. Its own requirements are added, not modified, so it can be archived after them.
- **Repository size:** minus 8.7 MB of dark home page recordings, plus three new recording pairs and the light variants of 14 screenshots.
