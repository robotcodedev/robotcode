# Proposal

## Why

The documentation explains how to set RobotCode up in VS Code, but not how to work with it there. What exists is scattered:

- `getting-started/vscode.mdx` covers installation and a first test.
- The Documentation Viewer is a section at the end of the `robotcode doc` guide.
- The highlighting page is a tip for experienced users.

Several topics have no page at all: running and debugging, the Test Explorer, the language status items, where a setting belongs, Robocop and troubleshooting. Most of the extension's settings appear nowhere in the documentation. The maintainer wants a complete overview with screenshots of how to work with RobotCode in VS Code, including where to set what and how to get the documentation of keywords and libraries.

## What Changes

- A new group **VS Code** in the Guides area, right after the Guides overview. It has one page per task, each with screenshots of a real project:
  - an overview of the window with a numbered picture of where things are
  - writing code
  - finding information
  - the Documentation Viewer
  - the Test Explorer
  - running and debugging
  - configuration
  - diagnostics and linting
  - the REPL
  - troubleshooting
- **Documentation Viewer:** the section "VS Code" of the guide `guides/browsing-documentation.md` becomes the group's Documentation Viewer page. The guide keeps `robotcode doc` and links to the new page, and so does the home page's feature tour.
- **Screenshots in both themes:** every screenshot and screen recording of the group exists in VS Code's light and dark theme, and a page shows the one that matches the site's theme. A screenshot of the whole window opens in full size when clicked.
- **Generated settings reference:** a new Reference page **VS Code settings** lists every setting of the extension, grouped by its categories. A script generates it from `package.json`, like the CLI and `robot.toml` references.
- **Guides overview:** the Guides overview lists the group as one card that leads to the group's overview page.
- **Unchanged:**
  - `guides/vscode-highlighting.mdx` stays where it is, as a tip for experienced users.
  - Robot Framework notebooks are not documented, because they are unfinished.
  - The AI integration keeps its own guide.

## Capabilities

### New Capabilities

- `vscode-user-guide`: the pages that teach working with RobotCode in VS Code, and their screenshots.
- `vscode-settings-reference`: the generated reference of the extension's settings.

### Modified Capabilities

- `documentation-site`: "Area overview pages" now lists a group of pages inside an area as one link card to the group's overview.

## Impact

- **New pages:**
  - `docs/src/content/docs/guides/vscode/`: ten pages.
  - `docs/src/content/docs/reference/vscode-settings.md`: generated.
- **Changed pages:**
  - `guides/browsing-documentation.md` loses its VS Code section.
  - `getting-started/vscode.mdx` links to the new group.
  - `src/components/home/FeatureTour.astro` changes its Documentation Viewer link.
- **Site code:**
  - New screenshot and recording components for theme pairs in `docs/src/components/`.
  - A route middleware labels the group "VS Code".
  - `AreaOverview.astro` lists only the direct pages of an area.
  - `docs/astro.config.mjs` registers the middleware.
- **Media:** new screenshots and recordings in `docs/src/assets/screenshots/vscode/`, each in a light and a dark variant.
- **Scripts:**
  - New `scripts/create_vscode_settings_doc.py` and a hatch script `create-vscode-settings-docs` in `hatch.toml`.
  - `AGENTS.md` and `CONTRIBUTING.md` name the new generated page.
- **Outside the repository:** capture scripts in the git-ignored `playground/robotcode-demo/vscode/`.
- **Not affected:** the extension, the language server and `package.json`.
