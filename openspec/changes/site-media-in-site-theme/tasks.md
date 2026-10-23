# Tasks: site-media-in-site-theme

## 1. Captures

- [ ] 1.1 Add scenes 7, 8 and 11 to `guide-recordings.sh`, record them in both themes and encode them as the pairs of D3 in `docs/src/assets/screenshots/vscode/`. Verify:
  - A contact sheet of each take shows the expected steps.
  - An OCR of the frames finds no personal data.
- [ ] 1.2 Let `vscode/shots.js` take the tour's five VS Code screenshots in both themes (D4), as `screenshots/tour/vscode-<subject>-{light,dark}.png`. Verify:
  - Each pair shows the same state in both themes.
  - The pair helper's check for personal data passes.
- [ ] 1.3 Take the five PyCharm screenshots with the IDE's light and dark theme and the waits of D4, as `screenshots/tour/pycharm-<subject>-{light,dark}.png`. Verify that each pair shows the same state and no personal data.
- [ ] 1.4 Check that the color scheme in `nvim/init.lua` has a light variant, then take the four Neovim screenshots with a light and a dark background (D4), as `screenshots/tour/neovim-<subject>-{light,dark}.png`. Verify that each pair shows the same state.

## 2. Feature tour

- [ ] 2.1 Switch the tour's video slides to the theme-following source of D1, using the pairs of D3 and durations measured from the longer variant. Verify in a browser check of `/` in both themes:
  - The tour plays the variant of the site's theme, and no file of the other variant is requested.
  - Switching the theme while a recording plays continues from the same point.
  - The enlarged view shows the variant of the theme.
- [ ] 2.2 Switch the tour's screenshot slides to the pairs of D2. Verify in the same browser check that the screenshots and their enlarged view follow the theme.
- [ ] 2.3 Delete the dark files of D3, and only those. Verify that `npm run docs:build` has no link errors, that no deleted name is referenced anywhere in `docs/src`, and that `neovim-mason-import-errors.png` and the PyCharm screenshots of the v2.8.0 news post are still there.

## 3. About page

- [ ] 3.1 Show `writing-new-test` and `test-explorer-run` with `ThemeVideo` in `about.mdx`. Verify in a browser check that `/about/` plays the variant of the site's theme and follows a theme switch.

## 4. Get Started with VS Code

- [ ] 4.1 Check whether the Extensions view offers "Add to Workspace Recommendations" for RobotCode in the harness; if not, install the packaged VSIX there for the clip. Record the clip in both themes, cropped to the Extensions view (D5).
- [ ] 4.2 Ask the maintainer before copying the real Python extension into the harness (D6). Record "Python: Create Environment" with Venv, a Python version and `requirements.txt` in both themes, cropped to the Command Palette and its pickers. Put the stub back afterwards.
- [ ] 4.3 Record running First Test Case from its play button, with `Hello world` in the Debug Console, in both themes, cropped to the editor and the console.
- [ ] 4.4 Replace the three old clips in `getting-started/vscode.mdx` with `ThemeVideo` and the new pairs, and delete the old files. Verify:
  - The browser check shows the variant of the theme.
  - The build has no link errors.
  - An OCR of the new frames finds no personal data.

## 5. Integration

- [ ] 5.1 Run the complete browser check of the theme behavior on `/`, `/about/`, `/getting-started/vscode/` and one guide page, in both themes and with a switch. Verify that it passes, that `npm run docs:build` succeeds and that the repository has no unreferenced screenshot or recording left.

## Workflow follow-up

- Archive `migrate-docs-to-starlight` and `home-feature-tour-examples` before this change is archived.
