## ADDED Requirements

### Requirement: Messages of the language server appear as plain text

The plugin SHALL show the text of the language server's `window/showMessage` messages as the server sends it, with every character, although LSP4IJ converts that text from Markdown.

#### Scenario: Pattern in a message

- **WHEN** the language server shows "No profile matches '*base*'."
- **THEN** the notification shows `'*base*'` with both asterisks and without italics

#### Scenario: Angle brackets in a message

- **WHEN** the language server shows an error that contains `(<unknown>, line 1)`
- **THEN** the notification shows `(<unknown>, line 1)`
