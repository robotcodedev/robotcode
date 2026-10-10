# Tasks: vscode-guide

## 1. Site structure

- [ ] 1.1 Create the ten pages of D1 in `docs/src/content/docs/guides/vscode/` with title, one-sentence description, sidebar label and order, each with a short body. Verify that `npm run docs:build` succeeds without link errors.
- [ ] 1.2 Add `docs/src/routeData.ts` and register it as Starlight's `routeMiddleware` in `docs/astro.config.mjs` (D2). Verify in `npm run docs:preview`:
  - The sidebar of a Guides page shows the group "VS Code" right after "Overview" and before "Discovering tests".
  - The group lists Overview first and Troubleshooting last.
- [ ] 1.3 Limit `AreaOverview.astro` to pages one segment below the area, and add `<AreaOverview area="guides/vscode" />` to the group's overview (D3). Verify in the built site:
  - `/guides/` has exactly one link card for `/guides/vscode/` and none for the group's other pages.
  - `/guides/vscode/` has one card for each of the nine other pages.
  - `/reference/` and `/getting-started/` list the same cards as before.
  - `/llms.txt` lists the group's pages right after the Guides overview, in sidebar order.
- [ ] 1.4 Add `ThemeImage.astro` (with `markers` and `full`) and `ThemeVideo.astro` to `docs/src/components/` (D4, D5). Verify with a sample pair on a group page in `npm run docs:preview`:
  - The dark site shows the dark variant, and switching to light shows the light variant without a reload.
  - The network log of each theme has no request for the hidden image variant.
  - The hidden video variant is neither requested nor playing. If it is, add the script of D4 and check again.
  - With JavaScript disabled, the dark variants show.
  - The markers sit at the same spots on both variants.
  - With `full`, a click opens the original file.

## 2. Settings reference

- [ ] 2.1 Add `scripts/create_vscode_settings_doc.py`, the hatch script `create-vscode-settings-docs` and `docs/src/content/docs/reference/vscode-settings.md` with its frontmatter (D9), and generate the page. Verify:
  - Two runs give identical files.
  - The page has one `###` heading per property in `package.json` `contributes.configuration`, under `##` headings with the category titles in declared order.
  - The section of `robotcode.run.openOutputAfterRun` lists `none`, `report` and `log` with their descriptions.
  - The section of `robotcode.python` is marked deprecated with the extension's message.
  - The built page has the element `id="robotcode.analysis.cache.saveLocation"`, and the site builds without link errors.
  - A setting temporarily added to `package.json` appears under its category after regenerating. Revert it afterwards.
  - The sidebar lists the page after Diagnostic Modifiers.
- [ ] 2.2 Name the generator in `AGENTS.md` (generated pages) and `CONTRIBUTING.md` (list of generator commands). Verify that `hatch run create-vscode-settings-docs` runs as written there and leaves the page unchanged.

## 3. Capture

- [ ] 3.1 Add to `playground/robotcode-demo/vscode/` a helper that runs a shot under "Default Light Modern" and "Default Dark Modern" and clips detail shots (D6, D7), and list the guide scripts in the demo README. Verify with one sample pair:
  - Both PNGs exist with the expected size.
  - One shows the light and one the dark theme.
  - Neither shows a user name, host name or home directory path.

## 4. Pages

Each task captures its page's screenshot pairs with a `guide-<page>.js` script (D7), writes the page by the rules of D10, and checks every statement against `package.json`, the extension or language server code, or the harness. Each one is verified in `npm run docs:preview` against the scenarios of its requirement in `specs/vscode-user-guide/spec.md`, in both themes.

- [ ] 4.1 Overview (`index.mdx`). Content:
  - A window shot with markers and `full`, and the numbered list of the parts.
  - The language status items and the output channels.
  - Every command titled "RobotCode: …" except the two notebook commands, checked against `package.json`.
  - The cards of 1.3.

  Verify the scenarios of "Overview of the VS Code window" and "Full-size window screenshots".
- [ ] 4.2 Writing code. Content:
  - Completion with documentation, signature help, hover, inlay hints and semantic highlighting.
  - The quick fix Create Keyword, rename, formatting and a new Robot Framework file.
  - A link to `/guides/vscode-highlighting/`.

  Verify the scenarios of "Writing code in VS Code".
- [ ] 4.3 Finding information. Content:
  - Go to Definition into `ShopLibrary.py`.
  - References and CodeLens, the outline, workspace symbols.
  - The Keywords view and its actions.

  Verify the scenarios of "Finding information in VS Code".
- [ ] 4.4 Documentation Viewer (D8).
  - Move the section "VS Code" of `browsing-documentation.md` into `documentation-viewer.mdx` and leave a pointer paragraph in the guide.
  - Add screenshot pairs, and record the viewer from `scene4.js` in both themes.
  - Change the link in `FeatureTour.astro`.

  Verify:
  - The scenarios of "Documentation Viewer page".
  - `git grep -n 'browsing-documentation/#vs-code'` finds nothing.
  - The build has no link errors.
- [ ] 4.5 Test Explorer (D11). Content:
  - Where the entries come from (`robotcode discover` with `robot.toml` and `.robotignore`) and when the tree updates.
  - The tree of workspace folders and suites, and filtering by text and tags, with the filter syntax taken from the harness.
  - The run profiles of each kind, with the names VS Code shows, and the configure button.
  - A full-window shot pair with passed and failed tests and the failure message at the failing line.
  - The test output, a suite with an error, and discovery errors in the Problems view.
  - `robotcode.testExplorer.enabled` with a link to its entry in the settings reference.

  Verify the scenarios of "Test Explorer in VS Code".
- [ ] 4.6 Running and debugging (D11). Content:
  - The icons beside the tests and Run/Debug Current File.
  - The `launch.json` configurations from `package.json`, with their purposes.
  - A debug session with breakpoint, Debug Console and inline values.
  - The log after a run and "RobotCode: Select Configuration Profiles".
  - A link to the Test Explorer page.

  Verify the scenarios of "Running and debugging in VS Code".
- [ ] 4.7 Configuration. Content:
  - Where a setting belongs: `robot.toml`, user or workspace settings, or folder settings.
  - The Python environment (screenshot) and the profiles.
  - Several workspace folders.
  - Links into `/reference/vscode-settings/`.

  Verify the scenarios of "Configuration in VS Code".
- [ ] 4.8 Diagnostics and linting. Content:
  - Diagnostics in the editor and the Problems view.
  - Enabling and disabling Robocop.
  - Severity changes and modifiers, with a link to `/reference/diagnostics-modifiers/`.
  - Unused keywords and variables.
  - When to clear the cache.

  Verify the scenarios of "Diagnostics and linting in VS Code".
- [ ] 4.9 REPL. Content: "RobotCode: Start Terminal REPL" with a screenshot and a link to `/guides/repl/`. Verify the scenarios of "REPL in VS Code", including that no page of the group mentions notebooks (`grep -ri notebook docs/src/content/docs/guides/vscode/` finds nothing).
- [ ] 4.10 Troubleshooting. Content:
  - The output channels and logs.
  - The language status items with their versions (screenshot).
  - Restart Language Servers, Clear Cache and Restart Language Servers, and Report Issue.

  Verify the scenarios of "Troubleshooting in VS Code".
- [ ] 4.11 End `getting-started/vscode.mdx` with a link to `/guides/vscode/`. Verify the scenario "From the setup to the group".

## 5. Integration

- [ ] 5.1 Verify the whole change:
  - `npm run docs:build` succeeds without link errors.
  - A browser check in `npm run docs:preview` covers every scenario of the three delta specs, with the site in both themes.
  - Every screenshot and recording of the group exists as a light and dark pair and shows no personal data.
  - `openspec validate vscode-guide --strict` passes.

## Workflow follow-up

- The pages go live with the next deploy of the site.
- Archive the change after the maintainer has reviewed the pages.
