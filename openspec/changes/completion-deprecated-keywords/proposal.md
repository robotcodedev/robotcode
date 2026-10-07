# Proposal: completion-deprecated-keywords

## Why

Robot Framework warns at run time whenever a deprecated keyword is called. Keyword completion still offers deprecated keywords in the same order as every other keyword. Only the list without a prefix strikes them through; after a library or resource name they look like any other keyword. Users who want to steer away from deprecated keywords cannot hide them.

## What Changes

- **Deprecated keywords are struck through in every keyword list**: also after `Library.` and after `resource.`, not only in the list without a prefix.
- **They sort after the other keywords** of the same list. Private keywords of other files, when shown (change `completion-private-keywords`), still come last.
- **Setting `robotcode.completion.hideDeprecatedKeywords`**, off by default. When it is on, completion does not offer deprecated keywords at all, in any list and from any file, also from the file being edited, because Robot Framework warns about every call.
- What counts as deprecated does not change: documentation starting with `*DEPRECATED`, as Robot Framework and the `DeprecatedKeyword` hint already use it.

## Capabilities

### New Capabilities

- `deprecated-keywords`: how keyword completion treats keywords that are deprecated: marking, order and the setting that hides them.

### Modified Capabilities

_None._

## Impact

- **Code:**
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`: mark, sort and filter the three keyword lists.
  - `packages/language_server/src/robotcode/language_server/robotframework/configuration.py`: the setting.
  - `package.json`: the setting for VS Code.
- **IntelliJ:** The plugin does not send completion settings yet, so the server's default applies: deprecated keywords are shown, struck through and sorted last. A switch in the settings comes with `intellij-settings-pages`.
- **Users:** Completion lists change order: deprecated keywords move down. Nothing is hidden unless the setting is switched on.
- **Tests:** completion of deprecated keywords in all three lists, with the setting on and off.
