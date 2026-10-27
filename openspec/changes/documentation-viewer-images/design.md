# Design: documentation-viewer-images

## Context

See proposal.md, section Why, for the problem.

**How the viewer builds a page today:**
- The extension runs `robotcode doc lib`. Its JSON has the page's `markdown`, the documented file as `source`, and a `keywords` list with each keyword's own `source`.
- `sendPage` renders the Markdown with `markdown.api.render` and posts the HTML to the webview.
- The page parses the HTML inert and removes `style`, `on…` and `data-vscode-context` attributes.
- `assignAnchors` gives the keyword headings their anchors by order: the i-th `h3` under the `h2` "Keywords" is `keywords[i]`, if the counts match.

**What the webview allows:**
- It gets its HTML once. Pages arrive as messages.
- Its content security policy allows images from `${cspSource}`, `https:` and `data:`.
- Its `localResourceRoots` are the extension's `out/documentationViewer` and the Markdown extension.

**Changing the roots reloads the webview.** I checked this in the VS Code 1.142 source:
- A new `webview.options` value goes through `$setOptions` to the `contentOptions` setter and then `doUpdateContent`.
- The webview host then builds a new iframe from the same HTML and drops the messages it has not delivered yet.
- Equal options are skipped. The extension API has no way to change only the roots.

**What the prototype showed.** On 2026-10-27 and 2026-10-28 a scratch prototype tried the lookup rule: beside the source first, then the root, with `asWebviewUri` and extra roots.
- It ran on Linux, on native Windows, in a multi-root workspace, over Remote-SSH from Linux to Windows, and with Markdown documentation on Robot Framework 7.5.
- Every variant found the expected file.
- Each new root reloaded the viewer, and the page was rendered twice.

## Goals / Non-Goals

**Goals:**
- Images of local files in the page, without reloading the viewer.
- One rule for Robot Framework's syntax and Markdown documentation.
- The same result in remote windows as in local ones.

**Non-Goals:**
- **Hovers.** VS Code's Markdown renderer drops relative image paths in LSP hovers, since the language client sets no base URI. Hovers are left for later.
- **IntelliJ.** It has no documentation viewer.
- **No size limit or cache** for images.

## Decisions

### D1: Images are embedded as `data:` URIs in the rendered HTML

After `markdown.api.render` and before the page is posted, the extension finds the file of each `<img>`. It reads the file with `vscode.workspace.fs.readFile` and replaces the `src` with a `data:` URI that holds the file's MIME type and its content in base64.

The reasons:
- The webview gets no new roots, so it does not reload.
- The content security policy already allows `data:`.
- `workspace.fs` reads in the extension host, which also works in remote windows.
- `json.markdown` stays as it is, so *Open as Markdown* and kept pages keep the paths.

The maintainer chose this on 2026-10-27, from these alternatives:
- **Folders as extra `localResourceRoots`** (the prototype). It reloads the viewer for each new folder and renders the page twice.
- **Workspace folders plus the Python path as fixed roots.** These reload only when the path changes. But the extension does not know the full path: robot.toml's `python-path`, the profiles and the interpreter's `sys.path` apply only in the Python process.
- **The file system root as root.** It never reloads, but the webview may then load any local file whose webview URL appears in documentation.
- **Images sent as messages, shown as `blob:` URLs.** No roots and no reload, but more code on both sides, and the content security policy would need `blob:`.
- **A `FileSystemProvider` scheme of our own as the only fixed root.** The VS Code source loads webview resources of any scheme through its file service, but nobody has tried this.
- **The language server's HTTP server, as in the old view.** It needs a port, port forwarding in remote windows, and it belongs to the deprecated view.

Documentation has a few simple images, so the larger page message is fine, and there is no size limit and no cache.

### D2: The lookup rule needs no Python path

**Where the folders come from:**
- The folder of the documented file comes from the `source` in the JSON. A library that Robot Framework finds through the Python path has its source there anyway.
- The root is the root of the workspace folder the page belongs to, `folder` in `sendPage`. The old view served the language server's working directory, which is this folder.

**Order:**
- A relative path is looked up beside the documented file first, if the file is known, then in the root.
- A path that starts with `/` is looked up only in the root.
- The first file that exists wins.

**Limits,** checked on the resolved path, so `pics/../logo.png` counts as `logo.png`:
- **Documented file inside the workspace folder:** the image must lie inside the folder.
- **Documented file outside the workspace folder:** the image must lie in that file's folder or below.
- **Lookup in the root:** the image must lie inside the folder.

**Paths that are not looked up,** on all platforms so that Windows behaves like Linux:
- a `src` with a URL scheme such as `https:`, `http:`, `data:` or `file:`
- one that starts with `//` or `#`
- a drive letter
- a backslash

The prototype found backslash paths on Windows only because Node accepts `\` as a separator.

**Preparing the path:**
- The `src` is decoded like a URL, so `%20` becomes a space, and loses its query and fragment.
- If the renderer keeps the written path in `data-src`, that path comes first, as in the prototype.
- Case follows the file system: Windows and macOS find `Images/Logo.png` for `images/logo.png`, Linux does not.

### D3: Keyword documentation uses the keyword's own file

The rendered HTML has no keyword anchors yet. The extension walks the headings in the same order as `assignAnchors`:
- An `<img>` between the i-th `h3` of the "Keywords" section and the next `h2` or `h3` uses `keywords[i].source`.
- Every other image uses the page's `source`. A keyword without a `source` uses the page's too.
- If the number of headings differs from the number of keywords, all images use the page's `source`. `assignAnchors` gives up in the same case.

The alternative was to resolve images per keyword in the Markdown before rendering. It was rejected because D1 keeps the Markdown as written, and mapping rendered images back to Markdown text is less reliable than the heading order the page already relies on.

### D4: The MIME type comes from the file extension

These extensions are embedded: `png`, `jpg`, `jpeg`, `gif`, `svg`, `webp`, `bmp`, `ico` and `avif`. A file with another extension is not embedded and is not shown.

An SVG in an `<img>` runs no scripts. This list is an assumption of this design, not a decision of the maintainer.

### D5: Code location and tests

- A new module `vscode-client/extension/documentationViewerImages.ts` takes the HTML, the workspace folder, the page's `source` and the keywords, and returns the HTML with the embedded images.
- Apart from file reads it has no side effects, so `vscode-client/test/documentationViewerImages.test.ts` can test it with temporary folders, as `documentationViewerBookmarks.ts` is tested.
- `sendPage` calls it after rendering. The check of `seq` and `disposed` comes after that call, because the call waits for file reads.

## Risks / Trade-offs

- **[Pages with images travel as larger messages and are read again on each render]** → Accepted. Documentation has a few simple images.
- **[A library adds `h3` headings in its keyword section, so the counts no longer match]** → All images of that page are looked up beside the page's `source`. The page assigns no keyword anchors in that case either.
- **[Documentation that relied on the old view, which served paths relative to the workspace folder]** → It keeps working through the lookup in the root. Only an image with the same path beside the documented file now wins.
- **[A large file referenced as an image]** → It is embedded as it is. There is no limit, as decided.
