# Spec Delta

## Purpose

Defines how `robotcode results log` turns HTML log messages into text and which images and files of those messages it records as artefacts for `--extract`.

## ADDED Requirements

### Requirement: Percent-encoded references

A relative link target or image source in an HTML message SHALL refer to the file named by its path with percent escapes decoded and without query and fragment, with and without `html-to-markdown`. The message SHALL link to that file with its path encoded once.

#### Scenario: Screenshot named after a test
- **WHEN** SeleniumLibrary's `Capture Page Screenshot    My Test-{index}.png` logged `<a href="My%20Test-1.png"><img src="My%20Test-1.png" width="800px"></a>` and `robotcode results log --extract DIR` is run
- **THEN** `My Test-1.png` is copied to the test's subdirectory of `DIR`
- **AND** the message links to `My%20Test-1.png`, not to `My%2520Test-1.png`

#### Scenario: Link with a fragment
- **WHEN** a test logs `<a href="notes.txt#part">notes</a>` as HTML, `notes.txt` lies next to the result file, and `robotcode results log --extract DIR` is run
- **THEN** `notes.txt` is copied to the test's subdirectory of `DIR`

### Requirement: file: links

A `file:` URL in an HTML message SHALL refer to the local path it names, with and without `html-to-markdown`. When that path lies inside the folder of the result file, it SHALL be an artefact like a relative reference. When it lies outside, it SHALL NOT be an artefact, and the message SHALL keep the link.

#### Scenario: File created in the output directory
- **WHEN** OperatingSystem's `Create File    ${OUTPUT DIR}/my data.csv` logged `Created file '<a href="file://…/my data.csv">…</a>'.` (with the path as OperatingSystem writes it on the platform, such as `file:///…` or `file://C:\…`) and `robotcode results log --extract DIR` is run on the result file in `${OUTPUT DIR}`
- **THEN** `my data.csv` is copied to the test's subdirectory of `DIR`
- **AND** no artefact of that message is skipped

#### Scenario: Standard file URL
- **WHEN** a test logs `<a href="file:///…/report.pdf">report</a>` as HTML, where the URL is the standard file URL of `report.pdf` next to the result file, and `robotcode results log --extract DIR` is run
- **THEN** `report.pdf` is copied to the test's subdirectory of `DIR`

#### Scenario: File outside the folder of the result file
- **WHEN** OperatingSystem's `Create File    ${TEMPDIR}/outside.txt` logged its message and `robotcode results log` is run on a result file in another folder
- **THEN** the message lists no artefact
- **AND** the message text links to `outside.txt` in `${TEMPDIR}`

#### Scenario: Relative reference leaving the folder
- **WHEN** a test logs `<img src="../shot.png">` as HTML and `robotcode results log` is run
- **THEN** the image is listed as skipped with reason `path-traversal`, as before

### Requirement: Links to folders

A link in an HTML message whose target is an existing folder SHALL NOT be an artefact, with and without `html-to-markdown`. The message SHALL keep the link.

#### Scenario: Directory created in the output directory
- **WHEN** OperatingSystem's `Create Directory    ${OUTPUT DIR}/downloads` logged its message and `robotcode results log --extract DIR` is run on the result file in `${OUTPUT DIR}`
- **THEN** the message lists no artefact, neither extracted nor skipped

### Requirement: Videos and audio

A `<video>` or `<audio>` element in an HTML message SHALL be shown as a link `[video](…)` or `[audio](…)` to its file, and that file SHALL be recorded as an artefact of kind `file`. The file is taken from the element's `src` or from the `src` of a `<source>` element inside it. This SHALL hold with and without `html-to-markdown`.

#### Scenario: Video recorded by Browser
- **WHEN** a test logged `</td></tr><tr><td colspan="3"><video width="1280" height="720" controls><source src="browser/video/videos/page%40x.webm" type="video/webm"></video>` as HTML, `browser/video/videos/page@x.webm` lies next to the result file, and `robotcode results log --extract DIR` is run
- **THEN** the message shows `[video](…)` linking to `page@x.webm`
- **AND** `page@x.webm` is copied to the test's subdirectory of `DIR`

#### Scenario: Audio with a src attribute
- **WHEN** a test logs `<audio src="sound.mp3" controls></audio>` as HTML, `sound.mp3` lies next to the result file, and `robotcode results log --extract DIR` is run
- **THEN** the message shows `[audio](…)` and `sound.mp3` is copied to the test's subdirectory of `DIR`

### Requirement: Images inside links

For an image inside a link in an HTML message, the image SHALL be recorded once as an artefact of kind `image`, and the link target SHALL be recorded as an artefact of kind `file` only when it is another file. In the message text, both the image and the link SHALL point to the resolved files. This SHALL hold with and without `html-to-markdown`.

#### Scenario: Screenshot file of SeleniumLibrary
- **WHEN** a test logged `</td></tr><tr><td colspan="3"><a href="selenium-screenshot-1.png"><img src="selenium-screenshot-1.png" width="800px"></a>` as HTML and `robotcode results log --extract DIR` is run
- **THEN** the message has exactly one artefact, the image `selenium-screenshot-1.png`, and it is extracted
- **AND** no artefact of the message is skipped

#### Scenario: Thumbnail linking to the full image
- **WHEN** a test logs `<a href="full.png"><img src="thumb.png"></a>` as HTML, both files lie next to the result file, and `robotcode results log --extract DIR` is run
- **THEN** `thumb.png` is recorded as an image and `full.png` as a file, and both are copied

#### Scenario: File link with a space in the path
- **WHEN** `html-to-markdown` is installed and OperatingSystem logged `Created file '<a href="file:///…/my data.csv">…</a>'.` for a file next to the result file
- **THEN** `my data.csv` is recorded as an artefact

### Requirement: Embedded files in the message text

An embedded `data:` link in an HTML message SHALL be shown as `_(embedded <link text> — see artefacts)_`, and as `_(embedded data — see artefacts)_` when the link has no text, with and without `html-to-markdown`.

#### Scenario: Embedded text file
- **WHEN** a test logs `<a href="data:text/plain;base64,SGVsbG8gd29ybGQK" download="hello.txt">hello.txt</a>` as HTML and `robotcode results log` is run
- **THEN** the message text is `_(embedded hello.txt — see artefacts)_`

### Requirement: Names of extracted embedded files

`--extract` SHALL write an embedded `data:` link that has a `download` attribute under the last path component of that attribute, made safe as test directory names are and not using a name that Windows reserves for devices. When two files of a test get the same name, the later one SHALL get a counter. Embedded files without a usable `download` name SHALL keep the name `embedded-N` with the extension of their media type.

#### Scenario: download attribute
- **WHEN** a test logs `<a href="data:text/plain;base64,SGVsbG8gd29ybGQK" download="hello.txt">hello.txt</a>` as HTML and `robotcode results log --extract DIR` is run
- **THEN** the test's subdirectory of `DIR` contains `hello.txt` with the content `Hello world`

#### Scenario: Same name twice
- **WHEN** a test logs two embedded links with `download="hello.txt"` and different content and `robotcode results log --extract DIR` is run
- **THEN** the test's subdirectory of `DIR` contains `hello.txt` and `hello-1.txt`

#### Scenario: Name with a path
- **WHEN** an embedded link has `download="../../evil.txt"`
- **THEN** it is written as `evil.txt` inside the test's subdirectory of `DIR`

#### Scenario: Unusable name
- **WHEN** an embedded `text/plain` link has `download=".."` and is the first embedded file of the test without a usable name
- **THEN** it is written as `embedded-0.txt`
