# Spec Delta

## MODIFIED Requirements

### Requirement: Embedded files in the message text

An embedded `data:` link in an HTML message SHALL be shown as `_(embedded <link text> - see artefacts)_`, and as `_(embedded data - see artefacts)_` when the link has no text, with and without `html-to-markdown`.

#### Scenario: Embedded text file
- **WHEN** a test logs `<a href="data:text/plain;base64,SGVsbG8gd29ybGQK" download="hello.txt">hello.txt</a>` as HTML and `robotcode results log` is run
- **THEN** the message text is `_(embedded hello.txt - see artefacts)_`
