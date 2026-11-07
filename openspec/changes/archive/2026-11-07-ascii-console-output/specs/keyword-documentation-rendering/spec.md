# Spec Delta

## MODIFIED Requirements

### Requirement: Return and raises descriptions

When a return description exists it SHALL be shown with the return type (`**Return Type**: \`T\` — description`, or `**Returns**: description` without a type; on the console, `robotcode doc` writes `**Return Type**: \`T\` - description`); on the full page, the names in `T` link to their data types by the requirement "Data types" of `library-documentation-markdown`. Raised exceptions SHALL be listed with their descriptions.

#### Scenario: Return description without a return type
- **WHEN** a keyword without a return type documents a `Returns:` section on RF 7.5
- **THEN** the rendered documentation shows `**Returns**:` followed by the description
