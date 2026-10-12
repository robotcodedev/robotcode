# Design: documentation-viewer-accessibility

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-12, with `@vscode-elements/elements` 2.5.1 and the viewer's accessibility tree in VS Code 1.141 (Playwright's aria snapshot).

- **Fields.** `vscode-textfield` renders an `<input>` inside its shadow root. The viewer sets `aria-label` on the `vscode-textfield` element for the target field ("Target"), the outline's filter field ("Filter the outline") and the find field ("Find in the page"). The input does not get it, so its name is its placeholder: "Library, resource or suite file, as Name::arg1::arg2 or path" and "Filter" in the accessibility tree. The find bar was not open during the check; for its field ("Find") this follows from the same code.
- **Label property.** `vscode-textfield` has a property `label` that it renders as `aria-label` of its input. `vscode-label` sets this property on the field it is linked to with `for`. vscode-elements marks the property `@internal`, with the note that `vscode-label` sets it.
- **Outline.** Each outline row (`role="treeitem"`) contains a span for the arrow that expands and collapses it and a span for its icon, both drawn as codicons by CSS, followed by the title. The entry's name therefore starts with the characters of these icons.
- **Toolbar.** `vscode-toolbar-container` is a container without a role or key handling. Each `vscode-toolbar-button` renders its own `<button>`, named by its `label` and with the role `switch` when it is toggleable. Every control is its own Tab stop, and the accessibility tree lists them without a group.
- **Tests.** The VS Code viewer has no JavaScript tests; the isolated VS Code harness can read its accessibility tree.

## Goals / Non-Goals

**Goals:**
- The names that the viewer already sets reach assistive technology, and outline entries are named by their titles alone.
- The toolbar is one named group.

**Non-Goals:**
- No change to the keyboard behavior of the toolbar: no single Tab stop and no arrow keys between its controls.
- No change to the outline's keys, which already follow the tree pattern (requirement "Moving through the outline with keys").
- No review of the page content, which is the documentation as `robotcode doc lib` produced it.
- No change to anything visible.

## Decisions

### D1: The field names through the `label` property of `vscode-textfield`

The three fields get their names through `label` instead of `aria-label`. The `aria-label` on the `vscode-textfield` element is removed, because it does not reach the input. A short comment at the fields says why `label` is used although vscode-elements marks it internal.

Alternatives considered:
- **`<vscode-label for=…>`.** That is the way vscode-elements documents, but the label is visible and does not fit the compact toolbar; a visually hidden label is more markup and ends up setting the same property.
- **`aria-labelledby` on the input.** The input is inside the shadow root, and an ID reference does not reach across the shadow boundary.

### D2: The icons of an outline entry are hidden from assistive technology

The arrow span and the icon span of an outline row get `aria-hidden="true"`. The entry's name is then its title. Clicking the arrow keeps working, and the entry still reports whether it is expanded.

Alternative considered:
- **`aria-label` with the title on the treeitem.** It works, but it repeats the title and overrides the content instead of removing the cause.

### D3: The toolbar as a named `toolbar`, without its own focus management

`vscode-toolbar-container` gets `role="toolbar"` and `aria-label="Documentation Viewer"`, the name of the viewer; screen readers add the role "toolbar" themselves. WAI-ARIA 1.2 lets authors manage the focus of a toolbar's descendants ("MAY"), so the Tab order stays as it is.

Alternative considered:
- **The toolbar pattern of the ARIA Authoring Practices.** It makes the toolbar a single Tab stop with the arrow keys between its controls. The controls have their `<button>` or `<input>` inside their own shadow roots, and in the target field Left and Right must move the cursor, so this is much more work for little gain. The maintainer chose the named group alone.

## Risks / Trade-offs

- [`label` is internal in vscode-elements, and a new version could change it] → The comment at the fields points to it; the check in tasks 2.1 shows the names after an update of vscode-elements.
- [The VS Code viewer has no JavaScript tests] → The scenarios are checked in the isolated VS Code harness by the accessibility tree and by the keyboard.

## Migration Plan

Nothing for users to do. Rollback is a revert.
