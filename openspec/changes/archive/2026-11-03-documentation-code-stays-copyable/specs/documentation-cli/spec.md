# Spec Delta

## ADDED Requirements

### Requirement: Links in the viewer go to the heading

A link to a heading in RobotCode's documentation viewer SHALL go to the heading, also when a line of a code block before it reads the same.

#### Scenario: Example that names the next keyword
- **WHEN** the example of the keyword `Start Coverage` has the preformatted line `` | `Stop Coverage` `` and `Stop Coverage` is the next keyword of the page
- **THEN** a link to `Stop Coverage` goes to its heading, not to the line of the example
