## MODIFIED Requirements

### Requirement: Documentation Viewer page

The page Documentation Viewer SHALL describe the Documentation Viewer with the content of the former section "VS Code" of the `robotcode doc` guide, with screenshots and a screen recording of a viewer in use. That guide SHALL keep only a short section that links to the page, and the home page's feature tour SHALL link to the page for the Documentation Viewer.

#### Scenario: Viewer page
- **WHEN** a reader opens `/guides/vscode/documentation-viewer/`
- **THEN** it explains how to open a viewer, the target field with its place and its suggestions, the bookmarks with the view Documentation Bookmarks, the outline and filter, links, find, arranging viewers and Open as Markdown
- **AND** a screen recording shows a viewer in use

#### Scenario: Guide without the viewer's description
- **WHEN** a reader opens `/guides/browsing-documentation/`
- **THEN** its section "VS Code" holds only a short paragraph with a link to `/guides/vscode/documentation-viewer/`

#### Scenario: Feature tour link
- **WHEN** a reader follows the Documentation Viewer link of the Code intelligence feature on the home page
- **THEN** `/guides/vscode/documentation-viewer/` is shown
