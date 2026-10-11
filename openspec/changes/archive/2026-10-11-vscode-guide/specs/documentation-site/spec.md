## MODIFIED Requirements

### Requirement: Area overview pages

The overview pages of the Getting Started area (`/getting-started/`), the Guides area (`/guides/`) and the Reference area (`/reference/`) SHALL list every other page of their area as a link card with the page's title and description, in sidebar order. A group of pages inside an area SHALL be listed as one link card to the group's first page, which SHALL list the other pages of the group the same way. The Getting Started overview SHALL also state the requirements for using RobotCode.

#### Scenario: Complete overview
- **WHEN** the site is built
- **THEN** `/reference/` contains one link card for each page of the Reference area, showing that page's declared title and description

#### Scenario: Group inside an area
- **WHEN** the site is built
- **THEN** `/guides/` contains one link card to `/guides/vscode/` and no link card to another page of the VS Code group
- **AND** `/guides/vscode/` contains one link card for each other page of the group
