# Tasks: documentation-viewer-images

## 1. Looking up and embedding images

- [ ] 1.1 Create `vscode-client/extension/documentationViewerImages.ts` with a function that takes the rendered HTML, the workspace folder, the page's `source` and the keywords, and returns the HTML with embedded images (design D1, D2, D4).
  - For each `<img>`, it reads `data-src` or else `src`, skips the paths that are not looked up, decodes the path and drops its query and fragment.
  - It looks up beside the documented file first, within that file's limit, and then in the root of the workspace folder.
  - It reads the first file that exists with `vscode.workspace.fs` and writes it into `src` as a `data:` URI.
  - Verify with `npm run compile` and `npm run lint`.
- [ ] 1.2 Assign images to keywords by the order of the `h3` headings in the "Keywords" section, as `assignAnchors` does (design D3).
  - An image in the i-th keyword's section uses `keywords[i].source`.
  - If the counts differ or a keyword has no `source`, the page's `source` is used.
  - Verify with the tests of 1.3.
- [ ] 1.3 Add `vscode-client/test/documentationViewerImages.test.ts`. It builds its files in a temporary folder, with paths from `path.join` and URIs from `vscode.Uri.file`.
  - It covers every scenario of the requirements "Where a viewer looks up an image" and "Which image files a viewer shows".
  - It also covers a path with `%20` and with a space, `data-src`, an unknown file extension, `data:` and `https:` images left as they are, and the fallback when the heading count differs.
  - Verify with `xvfb-run -a npm test`.

## 2. Images in the viewer

- [ ] 2.1 In `sendPage` in `vscode-client/extension/documentationViewer.ts`, call the new function after `markdown.api.render` when there is HTML, and check `seq` and `disposed` after it. `lastPage.markdown` stays `json.markdown` (design D1, D5). Verify with `npm run compile`, `npm run lint` and `xvfb-run -a npm test`.
- [ ] 2.2 Do a smoke run in the isolated VS Code harness on Linux with the prototype's test project. It has `WebUI.resource`, `MyLib`, `ExtLib` outside the workspace folder, and `MdLib` in Markdown format on Robot Framework 7.5.
  - Check the scenarios of "Images in documentation", "Where a viewer looks up an image" and "Which image files a viewer shows" by the width of each loaded image.
  - Check the scenarios of "Images keep the viewer and the page's Markdown": a marker set in the page and the open find bar survive a link to a page with images, and *Open as Markdown* shows the paths as written.
  - Verify by the harness output.
- [ ] 2.3 Do one run in a Remote-SSH window to the Windows VM, where the extension host runs on Windows. Check that an image beside a resource file and one in the root of the workspace folder show, and that the drive letter and backslash paths of the scenario "Drive letters and backslashes" do not. Verify by the widths in the harness output.

## 3. Documentation

- [ ] 3.1 After the `docs-guides-structure` change is committed, add a section on images to `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, as the requirement "Images on the Documentation Viewer page" describes.
  - It gets an example layout, with `images/doc/` in the root and `resources/global/WebUI.resource`.
  - It explains the lookup order, paths with `/`, the limits, the paths that are not looked up, `https:`, and that *Open as Markdown* keeps the paths.
  - Verify with `npm run docs:build` and in the dev server.

## Workflow follow-up

- Commit the planning artifacts as `docs(openspec)`, and the code and the guide in separate commits.
- Tell the reporter of #675 when the change has shipped, but only when asked to.
- Archive the change after review.
