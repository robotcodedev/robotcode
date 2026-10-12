# Proposal: documentation-viewer-accessibility

## Why

Screen readers get wrong or noisy names from the Documentation Viewer. Its three fields are announced by their placeholders instead of the names the viewer sets for them, its outline entries start with the characters of their icons, and its toolbar is a loose row of controls without a group. This showed up while exploring the viewer's accessibility tree for end-to-end tests that find elements by role and name.

## What Changes

- **Names of the fields.** The target field, the outline's filter field and the field of the find bar are announced as "Target", "Filter the outline" and "Find in the page", the names the viewer already intends for them.
- **Outline entries.** An outline entry is announced by the title of its heading only, without the characters of its icons.
- **Toolbar.** The toolbar is announced as a toolbar named "Documentation Viewer". The Tab key still moves through its controls one by one.
- **Nothing visible changes.**

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-documentation-viewer`: the names that a viewer gives screen readers and other assistive technology for its fields, its outline entries and its toolbar.

## Impact

- **Code:** `vscode-client/documentationViewer/app.tsx` (fields and toolbar) and `vscode-client/documentationViewer/outline.tsx` (icons of the outline entries).
- **Docs:** none; the guides do not describe the viewer's accessibility.
- **Tests:** The VS Code viewer has no JavaScript tests. The names are checked in the isolated VS Code harness by the viewer's accessibility tree.
- **Users:** Nothing visible changes. Screen reader users hear the intended names, and the toolbar as one group.
