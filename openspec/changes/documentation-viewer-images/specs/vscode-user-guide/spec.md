# Spec Delta

## ADDED Requirements

### Requirement: Images on the Documentation Viewer page

The page Documentation Viewer SHALL explain how documentation references images that a viewer shows. It SHALL say where a relative path and a path that starts with `/` are looked up, which files a viewer does not show, and that *Open as Markdown* keeps the paths as written.

#### Scenario: Images section
- **WHEN** a reader opens `/guides/vscode/documentation-viewer/`
- **THEN** a section uses an example layout to explain where the viewer finds the images of documentation: beside the documented file first, then in the root of the workspace folder
- **AND** it names the paths the viewer does not look up: `..` out of the workspace folder, `..` from a file outside it, drive letters, backslashes and `http:`
