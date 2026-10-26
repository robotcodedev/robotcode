# Design: code-action-and-selection-range-fixes

## Context

See proposal.md for the motivation. The code of this change runs the same on both analysis paths:
- Surround, Extract Keyword and their selection check `get_valid_nodes_in_range` in `parts/code_action_refactor.py`;
- Create local variable, Create suite variable, Add argument and the placeholders of Create Keyword (`_format_create_keyword_args`) in `parts/code_action_quick_fixes.py`;
- the insertion of a new keyword, `create_insert_keyword_workspace_edit` in `parts/code_action_helper_mixin.py`;
- the protocol handlers `textDocument/codeAction` and `codeAction/resolve` in `common/parts/code_action.py`;
- the loop over the positions in `parts/selection_range.py`.

`parts/` is `packages/language_server/src/robotcode/language_server/robotframework/parts/`, `common/` its sibling. Each finding below was checked on 2026-10-26 in the code and with the language server on Robot Framework 5.0.1, 6.0.2 and 7.5, or in the Robot Framework sources:

- **Extract Keyword** compares the source of a `VariableDefinition`, a `str`, with the `source` of the Robot Framework model, which is a `Path` from Robot Framework 6.1 on. Nothing matches, so the new keyword gets no `[Arguments]` and no `RETURN` (on 6.0.2 it gets both). Hover and Go to Definition compare with `namespace.source`, a `str`.
- **The selection check** walks only the test or keyword where the selection starts, so a selection that reaches into the next test passes. It rejects `BREAK` and `CONTINUE` for Surround and Extract alike.
- **Inline IF:** the block of an inline IF ends one column behind its line, at the END token that Robot Framework adds. A selection to the end of the line covers its header and branches but not the block, so they are checked one by one. Before Robot Framework 6.1, `InlineIfHeader` is a subclass of `IfHeader`, and the check rejects it as a block header; from 6.1 on, it is not, and the same selection passes.
- **Surround** writes `==` where it means `=`, so at the last line its range ends one line behind the document. It computes the selection with `Range.extend`, which adds its offsets to both ends (`packages/core/src/robotcode/core/lsp/types.py`), so the end counts the start twice: with four spaces of indentation, the selection of `message` ends 14 characters too late and that of `Fail    Not Implemented` one too early. The third title reads "TRY...EXCEPT..FINALLY".
- **Extract Keyword** replaces the selected lines up to the start of the next line. Without a keyword section, the new keyword goes to the end of the last line. When the selection includes the last line, the second edit lies inside the first one, which the protocol forbids.
- **Create Keyword** turns every argument without a literal name into `${argN}`, also `@{…}` and `&{…}`, and writes a name the call gives twice twice.
- **Create local variable and Create suite variable** always write `${name}`, and Create local variable `Set Variable`. Create local variable inserts before the line of the statement, also before `ELSE IF`, `EXCEPT` and `[Arguments]`.
- **Create suite variable** sets the end line of its selection to the line of the insertion, before its start when it creates a section. With neither a settings nor a Variables section, it inserts at the top of the file, before a `Language:` line. Robot Framework then no longer reads the language, and it no longer recognizes a localized section header after it.
- **Add argument** appends after the last argument, also behind `&{…}` and behind an argument whose default value needs the new one. The User Guide puts free named arguments "absolutely last" and lets default values use earlier arguments, on all supported versions.
- **New section headers** take `namespace.languages.languages[-1]`, which is always English, because Robot Framework adds English last. Create suite variable writes `*** Variables ***` as fixed text.
- **UTF-16:** the code action handlers convert the incoming range and the incoming diagnostics from UTF-16, the diagnostics in place, but return the edits, the selection passed to `_robotcode.codeActionShowDocumentSelectAndRename` and the diagnostics without converting them back. Rename converts its edits with `range_to_utf16`.
- **Selection ranges** stop at the first position without a node (`break`), so the result is shorter than the list of positions.

## Goals / Non-Goals

**Goals:**
- Each finding of D1 is fixed, with a test through the handlers that passes with the fix and fails without it.

**Non-Goals:**
- No change to the model branches or to the rules of `semantic-model-feature-tests`: the name, the target and the other argument rules of Create Keyword, and Assign keyword result to variable, stay as they are.
- No new Surround variants (IF, FOR, WHILE, GROUP) and no other placeholders than `EXCEPT    message` and `Fail    Not Implemented`; that is decided for later.
- No better variable analysis for Extract Keyword; `semantic-model-workspace-refactorings` plans it on the model.
- Disable for this line belongs to `disable-diagnostic-for-line`.
- No other selection range steps; they change after `semantic-model-cleanup`.

## Decisions

### D1: The fixes and their labels

The labels are used in tasks.md.

| Label | Fix |
|---|---|
| CR2 | Extract Keyword finds its arguments and return values again from Robot Framework 6.1 on (D2). |
| CR3 | Surround accepts `BREAK` and `CONTINUE`; Extract Keyword keeps rejecting them (D3). |
| CR4 | After Surround, exactly `message` or the `Fail    Not Implemented` of the FINALLY branch is selected (D4). |
| CR5 | A selection that reaches into the next test or keyword disables Surround and Extract Keyword (D3). |
| CR6 | The edits of Extract Keyword do not overlap and stay within the document (D5). |
| CR7 | The edit of Surround stays within the document (D4). |
| CR8 | An inline IF is a valid selection on Robot Framework 5.0 and 6.0 too (D3). |
| CR9 | The title reads "Surround with TRY...EXCEPT...FINALLY". |
| QF5 | Create Keyword writes `@{args}`, `&{kwargs}` and each name once (D6). |
| QF6 | Create local and suite variable write a list or dictionary where the code uses one (D7). |
| QF7 | From Robot Framework 7.0 on, Create local variable writes `VAR` (D7). |
| QF8 | New section headers are in the language of the file; a new Variables section comes after a `Language:` line (D10). |
| QF9 | Create local variable writes before the whole IF or TRY and is not offered for `[Arguments]`, `[Tags]` and `[Timeout]`; Add argument writes before the argument whose default needs the variable (D8, D9). |
| QF11 | Create suite variable selects exactly the new value (D10). |
| QF12 | Add argument writes before `&{…}` (D9). |
| QF13 | Code action ranges reach the editor in UTF-16 (D11). |
| SR9 | Selection ranges return one result per position (D12). |

### D2: Extract Keyword compares sources like hover (CR2)

The two comparisons use `namespace.source`, the `str` that the variable definitions of the file carry, as hover and Go to Definition do. The fix stays this small, because `semantic-model-workspace-refactorings` replaces the variable analysis of Extract Keyword with one on the model.

*Alternative considered:* compare normalized paths of `model.source`. Rejected: it adds a conversion where the namespace already holds the right value.

### D3: One selection check for both actions (CR3, CR5, CR8)

`get_valid_nodes_in_range` keeps serving both actions, with three changes:
- A selection whose end lies behind the test or keyword where it starts is invalid.
- `BREAK` and `CONTINUE` are rejected only for Extract Keyword (the flag that already rejects `RETURN` for it). Surround puts them into the TRY branch, where Robot Framework allows them inside a loop; only FINALLY forbids them, on all supported versions.
- The check for block headers leaves out `InlineIfHeader`, as it already does from Robot Framework 6.1 on, where that class is no longer an `IfHeader`.

*Alternative considered:* treat the inline IF block as one statement and ignore Robot Framework's END token in its range. Rejected: it changes how every version checks inline IF, while leaving out one class matches what 6.1 and later already do.

### D4: Surround computes its ranges from the template (CR4, CR7, CR9)

The selection ends at its start plus the length of the placeholder: `message`, or `Fail    Not Implemented` for TRY...FINALLY. At the last line, the replaced range ends at the end of that line, and the body still contains it. The third title gets its third dot.

*Alternative considered:* let `Range.extend` set absolute ends. Rejected: other callers rely on its offsets.

### D5: Extract Keyword never writes overlapping edits (CR6)

When the new keyword would be inserted inside the replaced lines, its text joins the replacing edit. All edit ranges end within the document.

*Alternative considered:* insert at the start of the line after the replaced lines. Rejected: at the end of the file there is no such line.

### D6: Placeholders follow Robot Framework's order of arguments (QF5)

The positional arguments become `${argN}` up to the first `@{…}`, which becomes `@{args}` and takes the rest of them. Named arguments become `${name}`, each name once. A `&{…}` becomes `&{kwargs}` at the end. That is the order of a user keyword's `[Arguments]`: positional, variable number, named-only, free named.

*Alternative considered:* keep one `${argN}` per argument and only drop repeated names. Rejected: a list or dictionary passes any number of arguments at run time.

### D7: Variables in the kind the code uses (QF6, QF7)

The prefix before the name in the code decides the kind: `$` scalar, `@` list, `&` dictionary. Create local variable writes `VAR` from Robot Framework 7.0 on: the User Guide of 7.0 introduces it to replace `Set Variable` and to be used instead of `Create List` and `Create Dictionary`. Before 7.0 it writes these keywords. The placeholder is `value`, for a dictionary `key=value`, and it is selected afterwards.

*Alternative considered:* keep `Set Variable` on every version. Rejected: on 7.0 and newer it is the form the User Guide moves away from.

### D8: Where Create local variable writes (QF9)

For a variable in an `ELSE IF` or `EXCEPT` header, the new line goes before the IF or TRY block that holds the header, with its indentation. Before the header itself, it would land in the previous branch or in the TRY body and run only on that path. In `[Arguments]` the action is not offered: Robot Framework evaluates default values before the body runs, so no body variable can feed them. The same holds for `[Tags]` and `[Timeout]`; there, too, only Create suite variable is offered.

*Alternatives considered:*
- Offer it in `[Arguments]` and write before the line. Rejected: the code would still fail.
- Keep offering it in `[Tags]` and `[Timeout]`. Rejected by the user on 2026-10-26, for the same reason.

### D9: Where Add argument writes (QF9, QF12)

The new `${name}=` goes after the last argument, but before `&{…}` and before the first argument whose default value uses `${name}`, so that the default can use it.

*Alternative considered:* report that the variable cannot be added. Rejected: inserting earlier gives working code.

### D10: New sections (QF8, QF11)

A section header that a code action writes is in the language of the file: the language of its `Language:` line, otherwise the first language other than English that the workspace configures, otherwise English. `create_insert_keyword_workspace_edit` and Create suite variable use the same rule. Without a settings section, Create suite variable writes its new Variables section directly before the first section, so it always follows a `Language:` line. Its selection ends on the line where it starts.

*Alternative considered:* the language of the existing section headers of the file. Rejected: it needs a lookup per header, and the `Language:` line and the configuration already decide which languages Robot Framework reads.

### D11: Ranges to the editor in UTF-16 (QF13)

The common handlers convert what they return, as rename does:
- the ranges of the edits, after `textDocument/codeAction` and after `codeAction/resolve`;
- the diagnostics, back to the ranges the editor sent. The handler converted them in place, and several actions share one diagnostic, so each one is converted back once.

The parts convert the range they pass to `_robotcode.codeActionShowDocumentSelectAndRename`, because only they know that this argument is a range in a document.

*Alternative considered:* convert the arguments of known commands in the common handler. Rejected: the common part would have to know a command of the Robot Framework part.

### D12: An empty range for a position without a node (SR9)

A position without a node gets a result with the empty range at the position, and the loop goes on.

*Alternative considered:* the range of the whole document. Rejected: Expand Selection would jump to the whole file from a place with nothing to select.

## Risks / Trade-offs

- **[The selection check accepts or rejects other selections than before]** → One test per case (CR3, CR5, CR8). The inline IF change matters only before Robot Framework 6.1, where the class hierarchy differs.
- **[A part forgets to convert its command range to UTF-16]** → The QF13 test covers Add argument; all parts build the command through the same constant `SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND`, which a search finds.
- **[The language rule picks a configured language for a file written in English]** → Only new headers are affected, and Robot Framework reads them either way.
- **[`VAR` from Robot Framework 7.0 on changes the generated code]** → Intended (D7).

## Migration Plan

Nothing to migrate. Each fix can be reverted on its own, with its tests.
