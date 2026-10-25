# results-html-messages Specification

## Purpose

Defines how `robotcode results log` turns HTML log messages into text and which images and files of those messages it records as artefacts for `--extract`.

## Requirements

### Requirement: Screenshot messages that close the table row

An HTML log message that starts with markup closing the current table row of `log.html` and opening a new one (`</td></tr><tr><td colspan="3">`), as the screenshot keywords of SeleniumLibrary and Browser log it, SHALL be converted like the same message without that markup: its text is shown and its images and linked files are recorded as artefacts.

#### Scenario: Embedded screenshot
- **WHEN** a test logs `</td></tr><tr><td colspan="3"><img alt="screenshot" src="data:image/png;base64,…" width="800px">` as HTML and `robotcode results log --extract DIR` is run
- **THEN** the message shows the placeholder for an embedded image and the decoded PNG is written to the test's subdirectory of `DIR`

#### Scenario: Screenshot file
- **WHEN** a test logs `</td></tr><tr><td colspan="3"><a href="shot.png"><img src="shot.png" width="800px"></a>` as HTML, `shot.png` exists next to the result file, and `robotcode results log --extract DIR` is run
- **THEN** `shot.png` is copied to the test's subdirectory of `DIR`

### Requirement: Supported html-to-markdown versions

`robotcode results` SHALL convert HTML messages with `html-to-markdown` only when version 3.18 or newer is installed. When an older version is installed, or its version cannot be read, the result SHALL be the same as without `html-to-markdown`.

#### Scenario: html-to-markdown 3.17.2 installed
- **WHEN** `html-to-markdown` 3.17.2 is installed and `robotcode results log --extract DIR` is run on a test with an embedded screenshot message
- **THEN** the message text and the extracted files are the same as without `html-to-markdown`

#### Scenario: html-to-markdown 2.x installed
- **WHEN** `html-to-markdown` 2.30.0 is installed and `robotcode results log --extract DIR` is run on a test that logs an embedded image as HTML
- **THEN** the image is extracted

#### Scenario: html-to-markdown 3.18 or newer installed
- **WHEN** `html-to-markdown` 3.18.0 or newer is installed
- **THEN** HTML messages are converted with `html-to-markdown`

### Requirement: Version of the html extra

The `html` extra of `robotcode-runner` SHALL require `html-to-markdown` 3.18 or newer.

#### Scenario: Installing the extra over an old version
- **WHEN** `pip install robotcode-runner[html]` is run in an environment with `html-to-markdown` 3.17.2
- **THEN** pip installs `html-to-markdown` 3.18 or newer
