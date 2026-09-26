# Spec Delta

## ADDED Requirements

### Requirement: Published at robotcode.io

The site SHALL be the one published at https://robotcode.io and SHALL replace the previous VitePress site entirely. It SHALL be built from the repository's `docs/` directory, where its pages are edited directly, so that each page's edit link points to its file under `docs/src/content/docs/`.

#### Scenario: New paths on the published site
- **WHEN** a reader opens `https://robotcode.io/reference/config/`
- **THEN** the robot.toml configuration reference of the new site is shown

#### Scenario: Old path on the published site
- **WHEN** a reader opens `https://robotcode.io/03_reference/config`
- **THEN** the site's not-found page is returned

#### Scenario: What's new from the VS Code extension
- **WHEN** the VS Code extension opens `https://robotcode.io/news/` after an update
- **THEN** the news post list is shown with the newest post first

#### Scenario: Edit link
- **WHEN** a reader opens `https://robotcode.io/getting-started/neovim/`
- **THEN** the page links to `docs/src/content/docs/getting-started/neovim.mdx` in the GitHub repository

### Requirement: Generated reference pages

The generated CLI reference and the generated configuration reference SHALL be pages of the Reference area that declare their title and description and contain no top-level heading of their own. Their generators SHALL write them in place, and regenerating them with the documented commands SHALL change only their generated content.

#### Scenario: Regenerate the configuration reference
- **WHEN** the configuration reference is regenerated with the documented command without changes to the option model
- **THEN** the page is unchanged
- **AND** the site builds without errors

#### Scenario: Regenerate the CLI reference
- **WHEN** the CLI reference is regenerated with the documented command without changes to the command line
- **THEN** the page is unchanged
