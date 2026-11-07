# Spec Delta

## MODIFIED Requirements

### Requirement: Supported VS Code versions

The VS Code extension SHALL run in VS Code 1.131.0 and every newer version, and SHALL declare 1.131.0 as its minimum, so that VS Code does not install it in an older version. The README and the Get Started page of the documentation SHALL name VS Code 1.131 as the minimum.

#### Scenario: Oldest supported version
- **WHEN** the extension is installed in VS Code 1.131.0 and a folder with Robot Framework files is opened
- **THEN** the extension activates, and its language features, test discovery and Keywords view work

#### Scenario: Older VS Code
- **WHEN** this version of the extension is installed in VS Code 1.130
- **THEN** VS Code does not install it, because it is not compatible

#### Scenario: Documented minimum
- **WHEN** a user reads the requirements in the README or on the Get Started page
- **THEN** both name VS Code 1.131 as the minimum

### Requirement: Node.js runtime of the extension

The extension SHALL run on Node.js 24, the Node.js of VS Code's extension host from VS Code 1.123 on, desktop and remote alike, and SHALL NOT need JavaScript syntax or Node.js APIs that Node.js 24.18, the version of VS Code 1.131.0, lacks.

#### Scenario: Extension host of the oldest supported version
- **WHEN** the extension activates in the extension host of VS Code 1.131.0, which runs Node.js 24.18
- **THEN** it activates without an error caused by syntax or an API that Node.js 24.18 does not support

#### Scenario: Remote window
- **WHEN** the extension runs in a WSL, SSH or dev container window of VS Code 1.131.0, whose remote extension host runs Node.js 24.18
- **THEN** it activates as in a local window
