# Spec Delta

## MODIFIED Requirements

### Requirement: Troubleshooting in VS Code

The page Troubleshooting SHALL explain where RobotCode writes its output and logs in VS Code, how to check which RobotCode, Robot Framework and Python versions are used, how to copy them for a report, how to restart the language servers, how to clear the cache and restart them, and how to report an issue.

#### Scenario: Versions in use
- **WHEN** a reader opens `/guides/vscode/troubleshooting/`
- **THEN** a screenshot shows the language status items with the RobotCode, Robot Framework and Python versions

#### Scenario: Restart and report
- **WHEN** a reader opens `/guides/vscode/troubleshooting/`
- **THEN** the page explains "RobotCode: Restart Language Servers", "RobotCode: Clear Cache and Restart Language Servers" and "RobotCode: Report Issue..."

#### Scenario: Copy the versions
- **WHEN** a reader opens `/guides/vscode/troubleshooting/`
- **THEN** the page explains "RobotCode: Copy Environment Info", that it copies the versions of the workspace folder as a list for an issue, a forum post or a chat, and that the RobotCode menu offers it too, and the screenshot of the menu shows the entry
