# Proposal: results-artefact-references

## Why

Runs of SeleniumLibrary 6.9.0, Browser 20.6.0, RF's Screenshot and OperatingSystem libraries (RF 7.5) show that `robotcode results log` misses or breaks many file references in HTML messages, with and without `html-to-markdown`:

- **Percent-encoded names:** libraries link their files through Robot Framework's `get_link_path`, which URL-encodes the path. A screenshot named after a test (`Capture Page Screenshot    My Test-{index}.png`, `Take Screenshot    name=my shot`) is logged as `My%20Test-1.png`. `--extract` reports `missing-source`, and the message shows the link encoded twice (`My%2520Test-1.png`).
- **`file:` links:** OperatingSystem logs a link `file://<path>` for nearly every keyword (`Created file`, `File … exists`, `Removed file`, …), with the path not encoded (`file:///tmp/my dir/a b.txt`, on Windows `file://C:\…`). Each one is resolved as a relative path below the result folder (`…/out/file:/tmp/…`). Even without `--extract` the log lists a broken link under every such message, and `--extract` copies none of these files, also when they lie in the output directory. With `html-to-markdown` a path with a space is not looked at at all.
- **Videos:** Browser logs a recorded video as `<video><source src="browser/video/videos/page%40….webm"></video>`. The built-in converter drops the element, so the message is empty. `html-to-markdown` shows `[video](…)`, but the encoded `@` makes the file `missing-source`.
- **Linked images with `html-to-markdown`:** for `<a href="x.png"><img src="x.png"></a>`, as SeleniumLibrary, Browser and the Screenshot library log their files, the link is rewritten twice. Every screenshot gets an extra artefact skipped as `missing-source`, and the message keeps an unresolved link target.
- **Embedded files:** the built-in converter shows `<a href="data:…" download="hello.txt">hello.txt</a>` as an empty link `[hello.txt]()`. Both converters extract it as `embedded-0.txt`, and the name given in `download` is lost.

## What Changes

- Relative references are resolved with their percent escapes decoded and without query and fragment.
- A `file:` URL is resolved to the path it names. Inside the folder of the result file it is an artefact like a relative reference. Outside that folder it is no artefact, and the message keeps the link. Relative references that leave the folder stay skipped as `path-traversal`.
- A link to a folder is no artefact.
- `<video>` and `<audio>` (their `src` or a `<source src>`) are shown as `[video](…)` / `[audio](…)` by both converters, and their file is an artefact.
- With `html-to-markdown`, a link around an image is resolved once: the image and, when it is another file, the link target are recorded, and both targets in the message point to the resolved files. Link targets in angle brackets (`<file:///tmp/my dir/a b.txt>`) are resolved too.
- The built-in converter shows an embedded file as `_(embedded hello.txt — see artefacts)_`, as `html-to-markdown` does.
- `--extract` writes an embedded file with a `download` attribute under that name, made safe for every file system. Embedded files without one keep `embedded-N`.

Not part of this change: absolute paths without `file:` (`<img src="/abs/x.png">`) keep today's handling.

## Capabilities

### New Capabilities

- `results-html-messages`: How `robotcode results log` converts HTML log messages and finds their artefacts. The pending change `results-html-converter-version` introduces it too; whichever of the two is archived first creates the spec.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/runner/src/robotcode/runner/cli/results/_html.py`: resolution of local references, the built-in converter (media, embedded links, `download`), the Markdown post-processing of the `html-to-markdown` path and a pass that reads `download` names before that conversion.
- `packages/runner/src/robotcode/runner/cli/results/results.py`: `--extract` names embedded files after `download`.
- Tests: a new suite `tests/robotcode/runner/cli/results/suites/links.robot` with OperatingSystem and HTML messages like those of the libraries above, tests in `test_log.py` that run with both converters, unit tests for the `file:` forms.
- Docs: the `--extract` sections of `docs/src/content/docs/guides/analyzing-results.md`.
- Order: implement after `results-html-converter-version`. Its floor brings `html-to-markdown` 3.18 into the development environment, which the tests of this change need for messages with the table-row prefix.
