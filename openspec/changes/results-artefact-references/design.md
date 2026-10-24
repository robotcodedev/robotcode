# Design

## Context

All of it lives in `packages/runner/src/robotcode/runner/cli/results/_html.py`, apart from the naming in `_extract_artifacts` of `results.py`:

- `_make_external_artifact(href, kind, base_dir, on_artifact)` handles every non-`data:` reference that `_is_external_url` does not count as external. `file:` is deliberately not external, but `_resolve_under` joins the raw string to `base_dir`, so `file:///tmp/x` becomes `<base>/file:/tmp/x`, and `%20` stays literal. It records an `ArtifactRef` with `resolved_path` and returns `resolved.as_uri()` for the message text. A reference outside `base_dir` is recorded as skipped `path-traversal` and leaves no URL.
- The built-in converter `_StdlibToMd` handles `<a>` and `<img>`. It ignores `<video>`, `<audio>` and `<source>`. For an `<a>` with a `data:` href it records the artefact and emits `[text]()`.
- The `html-to-markdown` branch converts first, then `_post_process_refs` rewrites the Markdown with two regexes in sequence: `_MD_IMG_RE` for `![alt](src)`, then `_MD_LINK_RE` for `[text](href)`. Their targets are `[^)\s]+`, so `<…>` destinations are not matched. In `[![](x.png)](x.png)` the image is rewritten first. The link regex then takes `[![](file:///…/x.png)` as a link with the text `![` and resolves the image's new `file://` URL as a relative path. The real link target `](x.png)` is left as it was.
- `_extract_artifacts` names embedded artefacts `embedded-{seq}{ext}` and every other one after its source file. `_unique_name` adds `-1`, `-2`, … per test directory. Decoded bytes travel out-of-band in `_EMBEDDED_DATA` (`_DataBox`).
- OperatingSystem writes `<a href="file://{path}">` with the path as given, without encoding: `file:///tmp/a b.txt` on POSIX, `file://C:\dir\a b.txt` on Windows, where `urlsplit` puts `C:\dir\a b.txt` into the netloc. Robot Framework's `get_link_path`, which SeleniumLibrary, Browser and the Screenshot library use, URL-encodes relative links (`pathname2url`).
- `html-to-markdown` 3.18.6 renders `<video>`/`<audio>` as `[video](src)`/`[audio](src)`, a destination with a space as `(<file:///tmp/a b.txt>)`, drops the `download` attribute (`[hello.txt](data:…)`) and keeps percent escapes (`My%20Test-1.png`).

## Goals / Non-Goals

**Goals:**
- One resolution of local references that both converters use, so they record the same artefacts.

**Non-Goals:**
- Changing the base-directory rule for relative references, or absolute paths without `file:`.
- `file:` URLs with a remote host (`file://server/share/…`). They fall outside the folder of the result file and stay links.
- `<source srcset>` in `<picture>`, `<track>`, `poster`.

## Decisions

### D1: One function from reference to local path

A helper resolves a non-external reference to `(path, absolute)`:
- A `file:` URL (`urlsplit` scheme `file`) gives an absolute path. The host has to be empty or `localhost`. A host that is a drive letter followed by `:` (OperatingSystem on Windows) is put in front of the path. Percent escapes are decoded and, on Windows, `/C:/…` becomes `C:\…` (`url2pathname`).
- Any other reference loses query and fragment, has its percent escapes decoded and is joined to `base_dir` as today.
- **Fallback for raw names:** when the decoded path does not exist but the undecoded one does, the undecoded one is used. OperatingSystem does not encode its paths, so a file literally named `100%41.txt` would otherwise be missed.

`_make_external_artifact` then decides with the existing `relative_to(base_dir)` check:
- **Inside, a file or missing:** an artefact as today. The message gets `as_uri()` of the decoded path, encoded once.
- **Inside, an existing folder:** no artefact. The message gets the folder's `as_uri()`.
- **Outside, from `file:`:** no artefact. The message keeps the original href.
- **Outside, relative:** skipped `path-traversal` as today.
- **Host that is neither empty, `localhost` nor a drive:** no artefact, the href stays.

Where a kept href contains a space (OperatingSystem's raw paths), both converters write it as `<…>`, as `html-to-markdown` does.

Alternatives considered:
- Counting `file:` URLs as external (never an artefact): rejected by the user. Files that a test writes into the output directory are to be extracted.
- Skipping outside `file:` URLs as `path-traversal`: rejected by the user. OperatingSystem links to `${TEMPDIR}` and the like would add a skipped line to every such message.

### D2: Media elements in the built-in converter

`_StdlibToMd` keeps a stack of open `video`/`audio` elements.
- A `src` on `video`/`audio`, or a `src` on a `source` inside one of them, emits `[video](url)` or `[audio](url)` through `_make_external_artifact` with kind `file`. A reference that resolves to nothing emits `[video]()`, as an unresolvable `<a>` emits `[text]()` today.
- The `html-to-markdown` branch needs no own code. Its `[video](…)` goes through the link handling of D3.
- The kind stays `file`, because the JSON contract documents `"image" | "file"`.

### D3: One pass over the Markdown of html-to-markdown

`_post_process_refs` uses one regex with two alternatives, applied in one `re.sub`:
- a link whose text may contain images (`\[(?:!\[…\]\(…\)|[^\]])*\]\(target\)`);
- a stand-alone image.

For a link, the images in its text are rewritten with the image handler, then the link target with the link handler. Each target is resolved exactly once. Both handlers also accept `<…>` destinations, without the brackets in the resolved reference. They write `<…>` back when the new URL contains a space, which `as_uri()` never produces. The deduplication per message (`dedup_artefacts`) still merges image and link of the same file into the image.

Rejected: the `visitor` option of `html-to-markdown` 3.18.6, which could rewrite URLs during the conversion. It binds the conversion to more of an API that changed between 2.x, 3.0 and 3.18, and the built-in converter needs its own handling anyway.

### D4: Embedded links in the built-in converter

For an `<a>` with a `data:` href, `_StdlibToMd` emits `_(embedded ` at the start tag and ` — see artefacts)_` at the end tag, with the link text in between. When the link has no text it emits `data`. The `html-to-markdown` branch already renders `_(embedded {text or 'data'} — see artefacts)_`.

### D5: download names

`_make_embedded_artifact` takes an optional name and stores it next to the bytes in `_DataBox`. A `get_embedded_name(ref)` gives it to `_extract_artifacts`.
- **No JSON field:** the name only matters for extraction, and `extractedTo` shows it.
- **Where the name comes from:** the built-in converter passes `a.get("download")`. The `html-to-markdown` branch drops the attribute, so before converting it runs a small `HTMLParser` over the message and maps the `href` of every `<a>` with a `data:` href and a `download` attribute to that name. The pass runs only when the message contains `download`. `_replace_link` looks the URI up. A URI that `html-to-markdown` changed is not found and keeps `embedded-N`.
- **In `_extract_artifacts`**, the name is the part after the last `/` or `\`, cleaned with `_slugify` (the rule for test directory names). A name that is empty or only dots counts as missing. A stem that Windows reserves (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, case-insensitive) gets a leading `_`.
- **Naming and safety:** `_unique_name` handles collisions, and the existing `relative_to(test_dir)` check stays. `seq_embedded` counts only embedded files without a name, so the first unnamed one is still `embedded-0`.

### D6: Tests with both converters

- A new suite `tests/robotcode/runner/cli/results/suites/links.robot` with the fixture `links_output` writes its files into the folder of `${OUTPUT FILE}` and logs with OperatingSystem and `Log … HTML`, the way the libraries do: encoded names, `file:` links, a folder, a video with the table-row prefix, audio, linked images, a thumbnail, embedded files with `download`.
- On Windows CI, OperatingSystem's own messages produce the `file://C:\…` form, so no case has to imitate it.
- The new tests in `test_log.py` run once per converter through a parametrized fixture `html_converter` in `conftest.py`:
  - the built-in converter by `monkeypatch.setitem(sys.modules, "html_to_markdown", None)` and `importlib.reload(_html)`;
  - `html-to-markdown`, skipped when it is not installed.
  - The fixture reloads `_html` after `monkeypatch` has restored `sys.modules`. `results.py` uses `_html` through its module attribute, so the reloaded module takes effect in the in-process CLI runner.
- Unit tests for D1 build hrefs from `tmp_path` in both forms, `"file://" + str(path)` (OperatingSystem) and `path.as_uri()`. They run on every platform of the CI.

## Risks / Trade-offs

- [Many OperatingSystem messages now link real files in the output directory, so `--extract` copies files a test only touched (such as `File Should Exist`)] → They are files the log references, the same as relative links. Copies of one file within a test are deduplicated to one.
- [The raw-name fallback picks the wrong file when both the decoded and the undecoded name exist] → Only names containing `%XX`; the decoded name wins, as Robot Framework's own links are encoded.
- [Reloading `_html` in tests] → Same pattern and safeguard as the version check test of `results-html-converter-version`.

## Migration Plan

None. Embedded files with `download` get new names in `--extract`; the guide documents it.
