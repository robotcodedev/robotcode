# Proposal: documentation-viewer-images

## Why

The Documentation Viewer, new in RobotCode 2.8, shows no images that documentation references by a path, such as `[images/doc/WebUI_global.png|WebUI Global]` in a resource file (issue #675). The deprecated Libdoc view showed them only by accident: its server delivered files from the language server's working directory, the workspace folder, so only paths relative to that folder worked. The viewer's page is a webview that gets its HTML as a message. A relative path there points to nothing, and the webview may load local files only from a fixed list of folders.

## What Changes

- **Images from local files.** The viewer shows images that documentation references by a path. This works with Robot Framework's syntax `[path|title]` and in Markdown documentation of Robot Framework 7.5, with `![title](path)`, a reference-style image or `<img src="path">`.
- **Where an image is looked up.** A relative path such as `x.png`, `./x.png` or `../x.png` is looked up first beside the file the documentation comes from, then from the root of the viewer's workspace folder. The closer file wins.
  - That file is the library or resource file; for a keyword, it is the keyword's own file.
  - A path that starts with `/` is looked up only from the workspace folder's root.
- **Which files are shown:**
  - For a file inside the workspace folder, `..` may go up as long as the image stays in the folder.
  - For a file outside it, such as a library in a virtual environment, only images in that file's folder and below are shown; the root of the workspace folder still comes next.
  - Paths with a drive letter or with backslashes are not looked up, on any platform.
  - `https:` images show as before. `http:` images do not.
- **The page and its Markdown.** The viewer embeds the images it finds into the page it shows. This does not reload the viewer, and *Open as Markdown* keeps the paths as they are written.
- **Unchanged:** hovers, `robotcode doc` on the command line, and the Libdoc HTML of *Open Documentation (deprecated)*. Image paths with spaces already stay images since e5c66d7b8.
- **Not part of this change:** a way to link from documentation to another library's page in the viewer. The reporter of #675 links to the old view's server URL for that.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-documentation-viewer`: images in documentation. This covers where the viewer looks them up, which files it shows, and that embedding them keeps the viewer and the Markdown of the page.
- `vscode-user-guide`: the page Documentation Viewer explains how to reference images in documentation.

## Impact

- **Code:** a new module `vscode-client/extension/documentationViewerImages.ts`, which looks up and embeds the images. `sendPage` in `vscode-client/extension/documentationViewer.ts` calls it. The Python side, the content security policy and the webview's options stay as they are.
- **Tests:** a new `vscode-client/test/documentationViewerImages.test.ts` among the VS Code extension tests, plus one smoke run in the isolated VS Code harness.
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx` gets a section about images. The `docs-guides-structure` change is still reworking the guides, so this section waits until that change is committed.
- **Users:** documentation with images shows them in the viewer, without any setup. A page with images travels as a larger message to the viewer, which suits the few simple images documentation usually has.
