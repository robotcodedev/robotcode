## ADDED Requirements

### Requirement: A call of a deprecated keyword shows Robot Framework's reason

A call of a deprecated keyword SHALL produce a hint with the Deprecated tag, the code `DeprecatedKeyword` and the message `Keyword '<name>' is deprecated. <reason>`, where `<name>` is the keyword name without a library or resource prefix. The reason SHALL be the text that Robot Framework's run-time warning shows: the first paragraph of the documentation after the closing `*` of the `*DEPRECATED` marker, without leading and trailing whitespace.

#### Scenario: Reason after the marker
- **WHEN** a suite calls `After Marker` of the library `DepLib`, whose documentation is `*DEPRECATED!!* Use `New Kw` instead.`
- **THEN** the call gets a hint with the Deprecated tag, the code `DeprecatedKeyword` and the message `Keyword 'After Marker' is deprecated. Use `New Kw` instead.`

#### Scenario: Marker without text
- **WHEN** a suite calls `Plain Marker` of `DepLib`, whose documentation is `*DEPRECATED* Please use `New Kw`.`
- **THEN** the message is `Keyword 'Plain Marker' is deprecated. Please use `New Kw`.`

#### Scenario: Keyword of a resource file
- **WHEN** a suite calls `Old User Kw` of an imported resource file, whose `[Documentation]` is `*DEPRECATED!!* Use something else.`
- **THEN** the message is `Keyword 'Old User Kw' is deprecated. Use something else.`

#### Scenario: Only the first paragraph
- **WHEN** a suite calls `Two Paragraphs` of `DepLib`, whose documentation is `*DEPRECATED!!* Use `New Kw``, a second line `instead.`, an empty line and `More documentation.`
- **THEN** the message is `Keyword 'Two Paragraphs' is deprecated. Use `New Kw``, a line break and `instead.`, and does not contain `More documentation.`

#### Scenario: Closing asterisk on the second line
- **WHEN** a suite calls `Star On Second Line` of `DepLib`, whose documentation is `*DEPRECATED since 2.0,` followed by the line ``use `New Kw`.* Really.``
- **THEN** the message is `Keyword 'Star On Second Line' is deprecated. Really.`

### Requirement: Reason between the asterisks when nothing follows the marker

When the first paragraph of the documentation has no text after the closing `*`, the reason SHALL be the text between `*DEPRECATED` and the closing `*`, without leading and trailing whitespace, in the same message form. When that text is empty as well, the message SHALL be `Keyword '<name>' is deprecated.`

#### Scenario: Reason inside the marker
- **WHEN** a suite calls `Inside Marker` of `DepLib`, whose documentation is `*DEPRECATED since 2.0. Use `New Kw` instead.*`
- **THEN** the message is `Keyword 'Inside Marker' is deprecated. since 2.0. Use `New Kw` instead.`

#### Scenario: No reason
- **WHEN** a suite calls `No Reason` of `DepLib`, whose documentation is `*DEPRECATED*`
- **THEN** the message is `Keyword 'No Reason' is deprecated.`

### Requirement: The deprecated keyword message is the same on both analysis paths

The message of the `DeprecatedKeyword` diagnostic SHALL be identical whether the semantic-model analysis path is enabled or not, on every supported Robot Framework version. The language server and `robotcode analyze code` SHALL report the same message.

#### Scenario: Semantic model on and off
- **WHEN** a suite that calls `After Marker` of `DepLib` is analyzed once with `robotcode.experimental.semanticModel` off and once with it on
- **THEN** both report the message `Keyword 'After Marker' is deprecated. Use `New Kw` instead.`
