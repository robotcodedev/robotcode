## ADDED Requirements

### Requirement: The preview shows reports and logs in the IDE's theme

The built-in preview SHALL show reports and logs of Robot Framework 7.0 and later in the IDE's theme, light or dark, on every page of the tab, also after a link. When the IDE's theme changes, an open preview tab SHALL follow it without loading its page again. A browser that "Open in Browser" or another target of "Open output target" opens SHALL keep its own theme.

#### Scenario: Report in the light theme

- **WHEN** the IDE's theme is light and the report of a run with Robot Framework 7.5 opens in the built-in preview
- **THEN** the report shows Robot Framework's light theme

#### Scenario: Log in the dark theme

- **WHEN** the IDE's theme is dark and the user clicks "Open Log" in the tab of a run with Robot Framework 7.5, with "Open output target" set to "Built-in preview"
- **THEN** the log shows Robot Framework's dark theme

#### Scenario: The IDE's theme changes with a preview tab open

- **WHEN** the report's preview tab shows the light theme and the user switches the IDE to a dark theme
- **THEN** the report shows the dark theme without being loaded again

#### Scenario: Link from the report to the log

- **WHEN** the IDE's theme is light and the user clicks the link to the log in the report's preview tab
- **THEN** the log shows the light theme

### Requirement: The page's own theme switch in the preview

In the built-in preview, a choice made with the theme switch of a report or a log SHALL be kept, also when the page is loaded again, until the IDE's theme changes.

#### Scenario: The report's own theme switch

- **WHEN** the IDE's theme is light, the user switches the report in the preview tab to the dark theme with the report's own switch, and the configuration runs again
- **THEN** the preview tab shows the new report in the dark theme
- **AND** after the IDE's theme changes, the report follows the IDE's theme again
