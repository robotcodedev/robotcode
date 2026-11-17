# Design: deprecated-keyword-reason

## Context

See proposal.md for the problem. Verified facts:

- **RobotCode.** `KeywordDoc.deprecated_message` ([library_doc.py:1112](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)) returns the `message` group of `DEPRECATED_PATTERN = ^\*DEPRECATED(?P<message>.*)\*(?P<doc>.*)` ([library_doc.py:812](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)). Without `DOTALL`, the pattern only looks at the first line of the documentation. Its `.*` is greedy, so it reaches the last `*` of that line. Both analyzers build the message with the same f-string, `Keyword '{result.name}' is deprecated` + `: {deprecated_message}` (only when the message is not empty) + `.` ([namespace_analyzer.py:897](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py), [semantic_analyzer/analyzer.py:2241](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py)). Whether a keyword counts as deprecated (`KeywordDoc.is_deprecated`: the libdoc flag `deprecated` or a match of the same pattern) is a separate question and not affected. `LibraryDoc.deprecated_message` has the same logic but is not used anywhere.
- **Robot Framework.** `StatusReporter._warn_if_deprecated` (`robot/running/statusreporter.py`) warns when the documentation starts with `*DEPRECATED` and contains another `*`. The reason is `doc.split("*", 2)[-1].strip()`, and the warning is `Keyword '<full name>' is deprecated.` followed by a space and the reason. The documentation it receives is the short documentation: the lines up to the first empty line, joined with line breaks (`getshortdoc`, from `librarykeywordrunner.py` and `userkeywordrunner.py`). The code is the same on RF 5.0, 6.1, 7.0 and 7.5.
- **Observed** for a suite that calls keywords of a library `DepLib.py` and of a resource file (RobotCode 2.8.0 from main with the flag off, RF 7.5 and 5.0 give the same warnings):

  | Documentation | RobotCode today | Robot Framework |
  |---|---|---|
  | `*DEPRECATED!!* Use `New Kw` instead.` | `is deprecated: !!.` | `is deprecated. Use `New Kw` instead.` |
  | `*DEPRECATED* Please use `New Kw`.` | `is deprecated.` | `is deprecated. Please use `New Kw`.` |
  | `*DEPRECATED since 2.0. Use `New Kw` instead.*` | `is deprecated: since 2.0. Use `New Kw` instead..` | `is deprecated. ` |
  | `*DEPRECATED*` | `is deprecated.` | `is deprecated. ` |
  | `*DEPRECATED!!* Use `New Kw`` / `instead.` / empty line / `More documentation.` | `is deprecated: !!.` | `is deprecated. Use `New Kw`` + line break + `instead.` |
  | `*DEPRECATED since 2.0,` / ``use `New Kw`.* Really.`` | `is deprecated.` | `is deprecated. Really.` |
  | resource keyword, `[Documentation]    *DEPRECATED!!* Use something else.` | `is deprecated: !!.` | `is deprecated. Use something else.` |

- **Libraries.** The wheels of AppiumLibrary 3.2.1 (`*DEPRECATED!!* Use `Expect Element` instead`), RequestsLibrary 0.9.7 (`*DEPRECATED* Please use `GET On Session` instead.`, 8 keywords) and Browser 21.0.0 (`*DEPRECATED* Opens a new browser instance. …`) write the reason after the marker. Only BuiltIn writes it inside the marker (`*DEPRECATED since RF 5.0. Use native IF/ELSE or `Run Keyword If` instead.*`). SeleniumLibrary 6.9.0 has no keyword with `*DEPRECATED`.
- **Shared rules.** `diagnostic_rules.py` already holds message functions that both analyzers call, e.g. `private_keyword_call_message` ([diagnostic_rules.py:23](../../../packages/robot/src/robotcode/robot/diagnostics/diagnostic_rules.py)).
- **Tests.** No test checks the `DeprecatedKeyword` message, and no regression baseline contains it. `test_private_keywords.py` ([test_private_keywords.py:82](../../../tests/robotcode/language_server/robotframework/parts/test_private_keywords.py)) runs a module-scoped language server once per analysis path (`legacy`, `model`), with a library and a resource file written to a temp directory. It checks with `namespace.semantic_model` that the path is really the one requested.

## Goals / Non-Goals

**Goals:**
- The reason Robot Framework shows, for every documentation form in the table, and BuiltIn's reason.
- One place that builds the message, so the two analysis paths cannot drift apart.

**Non-Goals:**
- Which keywords count as deprecated (`is_deprecated`, `DEPRECATED_PATTERN`). The completion requirements of `deprecated-keywords` rely on it.
- The full name in the message (`DepLib.After Marker`, as Robot Framework writes it). The hint sits on the call, which already shows the name.
- Variables in the documentation of user keywords, which Robot Framework 7.5 replaces before it warns.
- `LibraryDoc.deprecated_message`, which is not used.

## Decisions

### D1: The reason follows Robot Framework's rule on the short documentation

`KeywordDoc.deprecated_message` takes the short documentation (`robot.utils.getshortdoc`, the function Robot Framework uses). If that starts with `*DEPRECATED` and contains another `*`, it splits it like Robot Framework, `split("*", 2)`. The reason is the third part, stripped. If that is empty, the reason is the second part without the leading `DEPRECATED`, stripped. Otherwise there is no reason. Because the rule is Robot Framework's own, on the same input, the reason matches the run-time warning on every supported version. The only difference is the fallback that keeps BuiltIn's reason.

Alternatives considered:
- Fix the regular expression (`DOTALL`, a lazy match, a group after the `*`): it would have to reproduce the first-paragraph cut and the first-`*` split in a pattern, which is harder to read than the split itself and easy to get subtly different.
- Exactly Robot Framework's rule without the fallback: BuiltIn's deprecated keywords would lose the reason that RobotCode shows today. Rejected by the user.

### D2: One shared message function

A function `deprecated_keyword_message(keyword: KeywordDoc) -> str` in `diagnostic_rules.py` returns `Keyword '<name>' is deprecated.`, followed by a space and the reason when there is one. Both analyzers call it in place of their f-strings, as they already do with `private_keyword_call_message`. Severity, tag, code and range stay at the call site.

Alternative considered: change the f-string in both analyzers. That leaves two copies of a format that the specs require to be identical.

### D3: Robot Framework's message form also for the fallback

A reason from between the asterisks is written in the same form: `Keyword 'Run Keyword Unless' is deprecated. since RF 5.0. Use …`. Decided by the user. Rejected alternatives: continuing the word (`is deprecated since RF 5.0. …`), which reads better for BuiltIn but gives a second form, and the colon of today (`is deprecated: since RF 5.0. …`), also a second form.

### D4: Line breaks of the first paragraph stay

When the first paragraph spans several lines, the reason keeps the line breaks, as in Robot Framework's warning. The language server and the editors show such a message on several lines. `analyze code` prints it as it is. Alternative considered: join the lines with spaces, as the `doc` command does for `short_doc`. That would make RobotCode's text differ from Robot Framework's.

## Risks / Trade-offs

- [The message text changes for every deprecated keyword] → The code `DeprecatedKeyword` stays the same, so `# robotcode: ignore[DeprecatedKeyword]` and the diagnostics modifiers keep working. Only tools that match the text see the new wording, which is now Robot Framework's.
- [`*DEPRECATED!!*` with nothing after the marker gives the reason `!!`] → None of the checked libraries uses that form. Accepted with the fallback.
- [A paragraph-long reason makes a long hint] → Robot Framework's warning has the same length. Libraries keep the deprecation note short in practice.
