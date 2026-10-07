# Design: completion-private-keywords

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-07.

- **What is private.** `KeywordDoc.is_private` is true on RF ≥ 6.0 when the keyword's tags contain `robot:private`. The tags include tags declared in the documentation (`library-documentation-extraction`). That holds for library and resource keywords alike.
- **Robot Framework at run time** (checked with RF 6.0 and 7.5):
  - RF warns only for user keywords, and only when the calling user keyword is in another file or when there is no calling user keyword. The latter also warns for a test case that calls a private keyword of its own suite file, which is robotframework/robotframework#5807.
  - RF puts tags from the documentation into output.xml, but its private check reads only `[Tags]` and `Keyword Tags`. So a keyword that is private through its documentation gets no warning; RobotCode does not follow that.
  - RF never warns for library keywords. Libdoc still marks them private and leaves them out of its HTML output.
  - None of RF's standard libraries has a private keyword on RF 6.0 or 7.5.
- **`PrivateKeyword` today.** Both analysis paths report it with the same condition: `result.is_resource_keyword and result.is_private and self._source != result.source`. They are `namespace_analyzer.py` (legacy) and `semantic_analyzer/analyzer.py` (SemanticModel). Library keywords are never reported.
- **Completion today.** `CompletionCollector.create_keyword_completion_items` builds three keyword lists:
  - after a library name, from `libraries[...].library_doc.keywords`, sort prefix `019_`;
  - after a resource name, from `resources[...].library_doc.keywords`, sort prefix `019_`;
  - without a prefix, from `namespace.keywords`, sort prefix `020_`.

  None of them looks at `is_private`. Library and resource names follow with `030_`. No regression output contains sort texts.
- **Shared rules.** `robotcode.robot.diagnostics.diagnostic_rules` already holds rules that both analyzers and the language server use, for example `is_variable_name_intentionally_unused`.
- **Settings.**
  - `CompletionConfig` (`robotcode.completion`) has `filter_default_language` and `header_style`; the collector receives it as `self.config`.
  - The IntelliJ plugin does not send the `completion` section yet. The planned `intellij-settings-pages` change sends every completion setting VS Code offers.

## Goals / Non-Goals

**Goals:**
- Completion, the legacy analyzer and the SemanticModel analyzer use one rule, so that completion hides exactly the keywords whose call would be reported.

**Non-Goals:**
- No change to what counts as private (`library-documentation-extraction`).
- No change to hover, signature help or the documentation pages; the latter already leave private keywords out.
- No setting in IntelliJ's settings page in this change; it comes with `intellij-settings-pages`.
- The REPL's own completion, which draws on the running session, is not touched.
- The lists after a library or resource name do not mark deprecated keywords, unlike the list without a prefix. That is the job of `completion-deprecated-keywords`.

## Decisions

### D1: One rule in `diagnostic_rules`

A function in `diagnostic_rules` gets a keyword and the path of the file that calls it. It returns the `PrivateKeyword` message, or `None` when the call is fine:
- the keyword is not private, or the calling file is the file that defines it: `None`;
- a resource keyword: "Keyword '<longname>' is private and should only be called by keywords in the same file.";
- a library keyword: "Keyword '<longname>' is private and should not be called from Robot Framework files.";
- any other keyword type: `None`.

Both analyzers replace their condition with this function. Completion hides a keyword when the function returns a message for the file being edited.

"Same file" means the file that contains the call, not the calling keyword. That keeps the existing behaviour for resource keywords and leaves out RF's warning for test cases in the defining suite file (#5807).

Alternatives considered:
- **Keep the condition in each place.** Three copies drift apart; the two analyzers already duplicate it.
- **A property on `KeywordDoc`.** The answer depends on the calling file, which the keyword does not know.

### D2: Completion filters, marks and sorts in the three lists

- In each of the three lists, a keyword for which D1 returns a message is skipped while `hide_private_keywords` is on.
- While it is off, the keyword is added with `labelDetails.description = "private"`. Its sort text puts it after the other keywords of the same list and before the next group: it gets the last rank of the sort key that `completion-deprecated-keywords` defines (D1 there), for example `020_2_` instead of `020_0_` in the list without a prefix. LSP has no tag for private items, and the server already announces `labelDetailsSupport`.
- The kind (`FUNCTION`), `detail` and the text edit stay as they are.

Alternative considered: putting "private" into `detail`. VS Code shows `detail` only for the selected item, so the mark would not be visible in the list.

### D3: The setting

- `CompletionConfig` gets `hide_private_keywords: bool = True`.
- `package.json` declares `robotcode.completion.hidePrivateKeywords`: boolean, default `true`, scope `resource`, like the other completion settings.
- IntelliJ gets the server default until `intellij-settings-pages` sends the completion section.

### D4: Library keywords are reported although RF stays silent

Library authors tag a keyword `robot:private` to hide it from users, and Libdoc honours that. RobotCode reports the call as it reports a private resource keyword from another file, with a message that fits a library (D1). This is a deliberate difference from RF's runtime, like the documentation tags in Context.

## Risks / Trade-offs

- [Projects that call private library keywords get new warnings, which also set the exit code of `robotcode analyze code`] → `PrivateKeyword` can be lowered or ignored with diagnostic modifiers. The release notes name the change.
- [Users who call private keywords of other files on purpose no longer see them in completion] → They switch the setting off and get them back, marked and sorted last.
- [RF may resolve #5807 differently, for example by rejecting `robot:private` in suite files] → Revisit the rule for suite files when RF decides; nothing in this change depends on it.
- [`semantic-model-completion` rebuilds how completion finds its context] → The filter sits in the keyword lists that both paths share. That change requires identical items with and without the SemanticModel, so it keeps the filter.

## Migration Plan

Nothing for users to do. Rollback is a revert.
