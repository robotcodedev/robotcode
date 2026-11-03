# Design

## Context

The findings come from an independent review on 2026-11-02 against robotcode 2.8.0 (dev build), RF 7.5, on the skill at `88b5555`; 13 of them were reproduced a second time. Line numbers below refer to that commit, the skill folder is `plugins/robotcode/skills/robotcode/` on `next`.

What the code does today:

- A line breakpoint compares `bp.source == _normalize_source(frame.source)`. `login.robot` is made absolute against the current folder, so it only matches `./login.robot`, and nothing warns. `.breakpoints` prints only the base name. `hits` counts only after the condition has passed.
- `.abort` is `sys.exit(1)`. The comment says why: an exception from the logger callback is swallowed, `SystemExit` is the one Robot Framework lets through. It skips `output.close(runner.result)` in `TestSuite.run`, so the file has no end. `session stop`, `session restart` and the idle timeout send `.abort` at a stop.
- SIGTERM in `robot-debug` already takes another way (`_end_run`): Robot Framework's own graceful stop. The spec `session-termination` requires that the test fails with `Execution terminated by signal` and the output files are written.
- A graceful stop started from a listener at a keyword, as `.abort` would start it, was tried on RF 5.0, 6.0, 7.0 and 7.5: the file can be read in all four, the current test fails with `Execution terminated by signal`, the next one with `Test execution stopped due to a fatal error.`, and the test's teardown runs.
- `profile.build_command_line()` raises `ValueError` for a bad `{ expr }`; `handle_robot_options` doesn't catch it. An invalid `robot.toml` goes through `click.ClickException` and ends with 252.
- `config info desc` and `list` use `fnmatchcase(field, name)`, so `[profile].precedence` is a pattern with a character class.
- A dot command reports its errors with a plain `_echo`, so `session send` sees a statement that passed.

The maintainer's rule for the skill stays: text only where an agent would otherwise act wrongly, nothing that works by itself, nothing the agent sees in a message anyway, nothing twice.

## Goals / Non-Goals

**Goals:**
- An agent that follows the skill gets what the skill says, on the commands the review ran.
- What matters most survives compaction.
- The evals fail when such a thing goes wrong again, for the things that can be checked in a run.

**Non-Goals:**
- `config show` doesn't learn profiles: it stays the configuration as written, `profiles show` is what merges and evaluates. Decided by the maintainer.
- `session list` doesn't show a session's selection; the text says when to reuse a session.
- `.vars --user` stays as it is; the text says how to see a keyword's locals.
- No own reference for `robotcode doc`, no new mechanism for the version of the skill: `hatch run build:bump` already checks `metadata.version` at a release (`agent-plugin-release`).
- The news posts stay as released. Their `--break login.robot:42` becomes right through D1.
- Windows isn't measured again; the tests follow the rules for separators and paths.

## Decisions

### D1: A line breakpoint matches by the end of the path

A relative path matches when the source's path ends with its parts: `login.robot` hits every file with that name, `tests/login.robot` every path ending so. An absolute path, or one with `..`, which is made absolute against the current folder, matches exactly. Several files with that name all stop, as locations in gdb do.

The breakpoint keeps its location as given, for `.breakpoints` and for the warning of D2, and `restart` keeps it with the rest of the breakpoint.

Rejected: only documenting the path from the start folder. The docs and the news show the bare form, and with a project root and a start folder that differ the right relative path isn't obvious. Rejected: searching the suite for the file when the breakpoint is set: resources are imported later.

### D2: A warning at the end of the run

A breakpoint gets a `reached` mark when its location matches, before the condition is looked at. When the run has ended by itself, the debugger writes for each enabled breakpoint without the mark:

```text
[ WARN ] Breakpoint login.robot:42 was never reached.
```

It covers a mistyped path, the line of a test's name, a line that didn't run, and a mistyped keyword, which all look the same to an agent: the run went through. It comes in the run's output, so `session send` and `session wait` show it, and the exit code stays. After `.abort` or `.detach` it stays out, because the run didn't get that far or no longer had the debugger. A `restart` starts with no marks.

Rejected: a warning when the breakpoint is set: what can be reached isn't known then.

### D3: `.abort` goes the way of SIGTERM

`.abort` ends the run as a signal does: `_end_run` in a run, the end of the session in a REPL, with the debugger no longer stopping. `session stop`, `session restart` and the idle timeout get it because they send `.abort`. The file can be read, by the trial on four versions of Robot Framework. The exit code stays 253, so `robot-debug` has to return it for an aborted run instead of the number of failed tests.

This changes what `.abort` means, and the docs have to say so: teardowns run and the log and report are written, where it used to end at once. It is what SIGTERM does, and it keeps `.detach` apart, which lets the suite finish. Whoever doesn't want the teardowns passes `--skipteardownonexit`, which Robot Framework has for this. A teardown that hangs is ended by the second signal, as today.

Rejected: closing the XML by hand on the way out, which depends on Robot Framework's internals and on all open keywords; writing to a temporary file and moving it at the end, which would also keep the recorded run after an abort, but changes the paths in the log and doesn't help a debug run to its end.

A debug run to its end still replaces the recorded run, so the skill needs its sentence on `--output NONE` either way (D5).

### D4: Small corrections

- `config info desc` and `list`: `field == name or fnmatchcase(field, name)`.
- `results --help`: `robotcode results log -t "*Login*"`; `reference/cli.md` is regenerated.
- A `ValueError` from `build_command_line()` becomes a `click.ClickException`, the way of an invalid `robot.toml`, so each command exits with what it exits with for that (252 for those that run Robot Framework, 1 for `discover` and `analyze`). `profiles show` already reports it and shows the expression, which is what such a command is for; it gets a test.
- Dot commands: a method for an error of a dot command, which writes as `_echo` does; the session's interpreter overrides it and also marks the line as failed, as `_record_failure` does for a statement. It replaces `_echo` where a dot command couldn't do what was asked: an unknown or ambiguous name, `.doc` without a target, `.print` and `.set` of a variable that doesn't exist, `.break` that can't be parsed, the others of that kind found on the way. An answer such as "no breakpoints" isn't an error.

### D5: The corrections in the skill

Per file, with the number of the finding. What D1 to D4 solve needs no text.

**`SKILL.md`**

| # | Line | Correction |
|---|---|---|
| 1 | 82, 213–218 | `config show` is the configuration as written with the files merged; what is in effect is `robotcode [-p <name>] profiles show` (`-n` keeps expressions). `-p` isn't for `config`. |
| 2 | 188ff. | A debug run replaces the output file of the last run; to keep it add `--output NONE --log NONE --report NONE`. |
| 4, 27 | 123, 180 | Take the longname from `discover`; one from `results` holds only if that run had the same paths. Only the top folder keeps `__init__.robot`; below it, `-bl "Tests.Sub"`. |
| 5 | 177 | `--rerunfailed` with the path of the file from the project root. |
| 6, 14 | 112, 182 | Robot Framework's own options go before a path. Without `paths` in the configuration, pass the test folder, the same in every command. |
| 7 | 48, 51 | `discover tests` lists only tests; `discover tasks` or `discover all` for tasks. |
| 12 | 200 | A keyword's locals show after `.up`, or with `.print`. |
| 15, 34 | 30 | `No such command` as the first word after `robotcode` means a missing extra or a robotcode older than the skill; below it, a wrong subcommand. "Already installed" stays without the claim on the IDE extension's venv. |
| 16 | 222 | `results log --search`: a value that only passed through a variable isn't recorded unless it was logged. |
| 17 | 143 | Goes: the output says it. |
| 25 | 112, 114 | `rebot` only takes `-i`, `-e`, `-s`, `-t` of these. |
| 33, 35 | 213, 82 | `--format json` goes before the subcommand; the link for the merge order goes to `config.md`. |

**`references/debugging.md`**

| # | Line | Correction |
|---|---|---|
| 2 | 53, 203 | As in `SKILL.md`, by link. `.abort`: ends the run, teardowns run, the output is written. |
| 3 | 79 | The line must hold a keyword call; the `(path:line)` of `results` and `discover` is the test's name, where nothing stops. |
| 10 | 33 | Reuse a session only if it was started for this test; otherwise start a new one. |
| 12 | 130 | As in `SKILL.md`. |
| 20 | 59 | `--profile` goes: it belongs before the subcommand. |
| 21 | 29, 71, 198 | "Ending a session" becomes "Ending the run" for `.detach` and `.abort`. |
| 31 | 174–181 | `.commands` in a session: one `send` per line up to `end`. |
| 33 | 50, 70, 144, 187–194, 202 | A block at a terminal `(rdb)` doesn't work, in a session it does; `.kw` has the limit of `.source`; `.catch test` replaces the filters; `.debug on` only in a REPL. |
| 35 | 55 | The link's text promises no more than the target holds. |

**`references/repl.md`**: 19 (35, 50, 90): `.cwd` and `.save` use the project root, relative imports `${CURDIR}`; 24 (38): the exit code of a run is not always the failed tests, 252 and 253 are not; 28 (144): what doesn't carry over into a saved test, `${_}` and `${CURDIR}`; 32 (42): `No session` after an idle timeout isn't the sandbox; 33 (3): a fresh REPL has only its own libraries.

**`references/config.md`**: 1 (35, 62, 79, 109, 110); 9 (48, 98, 145–148): `enabled` only gates a profile that is selected through `-p`, `default-profiles` or `inherits`; 4 (153).

**`references/workflows.md`**: 4 (39, 54, 60) points to `SKILL.md`; 5 (99–125): `--output full.xml`, read back as `results/full.xml`, with one line on what is relative to what; 6 (130): options first; 18 (128): `--no-break-on-exception`; 8 (79); 29 (84); 35 (77).

**`references/analyze.md`**: 8 (32): no path is the whole project; 22 (56): `# robotcode: ignore[KeywordNotUsed]` at column 0 rather than `-mi`; 29 (105).

**`references/authoring.md`**: 1 (38), 7 (54, 77), 30 (64): "duplicate imports".

**`references/large-projects.md`**: 6 (19), 26 (43): the count comes from `tail -5`, 11 (78): `-o`, because auto-discovery prefers `output.xml`.

**`references/results.md`**: 23 (20, 26, 107): `results diff` has no `-o`, `CURRENT` takes its place; 36 (120): RF 7.0+.

**`references/install.md`**: 15 (5, 90), 34 (5, 41).

**Text that breaks the maintainer's rule**, finding C: what the agent sees in a message (`repl.md:38, :40`, `debugging.md:51, :116, :170`) and what stands several times (`analyze.md:18`, `workflows.md:73` for the bitmask; `repl.md:100–108`, `debugging.md:60, :112` for attaching; `results.md:3, :107` for auto-discovery; `repl.md:91`; `install.md:5, :17`; `repl.md:132`) goes.

### D6: Order and length of `SKILL.md`

Claude Code keeps the first 5000 tokens of a skill after compaction, and the Agent Skills specification recommends under 5000 for the body. Today it is about 6000 (cl100k, an estimate), and the end of "Debugging a run", "A real test case", configuration and results lie behind that line. The target is 4800 by the same estimate, so that the whole file stays.

| Section, in the new order | Now | Target | What changes |
|---|---|---|---|
| Introduction, environment | 305 | 200 | |
| Pick the mode | 873 | 750 | |
| Selecting one test or suite | 545 | 350 | Metadata filters shrink to one line; `results.md` and Discovery hold them |
| Running, with global options and formats | 585 | 400 | "Output formats" goes into global options |
| Interpreting results | 300 | 260 | |
| Debugging, a real test case | 747 | 600 | The question stays in the reference |
| REPL | 330 | 200 | Own heading instead of under "Library & keyword information"; the question stays in the reference |
| Discovery | 461 | 300 | |
| Static analysis | 207 | 130 | |
| Documentation (`doc` and the lookup priority) | 620 | 350 | Fewer examples |
| Configuration | 300 | 230 | |
| Tests or tasks | 350 | 150 | Details go to `authoring.md` |
| Concepts | 234 | 0 | Goes: the flags stand under Selecting, the commands to look things up under Discovery |
| Large projects, workflows | 141 | 120 | |

Sections that say what to do when stay in `SKILL.md`; what moves is detail that belongs to one mode. The Contents stay out, because the rule on tables of contents is for references.

### D7: The `description`

It stays as it is. Two shorter wordings lost against it in a direct comparison, with the same body of the skill, Sonnet, case 02, five runs each:

| `description` | Passed |
|---|---|
| As it was, 1022 characters | 5 of 5 |
| Its first sentence, the rest shortened, 931 characters | 2 of 5 |
| What the skill does first, then a softer instruction to use it first, 733 characters | 1 of 5 |

The failures read the raw `output.xml` before they had the skill, or didn't load it. What the `description` says works before the skill is loaded, and which of its words do it isn't clear from these runs, so nothing is changed by guesswork. The guides' advice to put the key use case first and to keep room under the limit loses against this measurement. 1022 of 1024 characters is within the limit; an edit later has to take out as much as it adds, and has to be measured the same way.

### D8: The docs

- `guides/cli/robot-debug.md`: the row of `.abort` (line 205), what `--break` matches, the warning, what `.breakpoints` shows.
- `guides/cli/sessions.md`: the exit code of `send` for a dot command (lines 105–114); what `session stop` leaves (line 190).
- `reference/cli.md`: regenerated with `hatch run create-cmd-line-docs`.
- Other pages that say `.abort` writes no reports, found with `grep`.
- The guide of `docs-ai-agents-guide`: the prose at `running-what-you-need.md:64` and `a-profile-for-the-ci-server.md:49`; the excerpt at line 111 comes with task 3.8 of that change.

### D9: The evals

New cases:

| # | Case | Query, in short | Checks |
|---|---|---|---|
| 21 | profile-effective-config | Which output directory does a run with the `ci` profile use? | `must_run` `-p ci` with `profiles show` or `--dry`; `must_answer` `results/ci` |
| 22 | debug-keeps-recorded-run | Step through `Login Works`, then say how many tests the last full run had and how many failed | `drive: debug`; `must_run` the debug start with `--output NONE`; `must_answer` 5 |
| 23 | debug-break-bare-file | Stop at line 25 of `login.robot` and say what `${response}` is | `drive: debug`; `must_answer` the value |
| 24 | pinned-rerun | Keep this run's results in a file of its own, rerun only the failures | `must_run` `--rerunfailed`; `must_not_run` `--output results/`; `must_answer` the result |
| 25 | tasks-discover | Which tasks are in the `tasks` folder? (`prepare` creates it) | `must_run` `discover tasks` or `discover all`; `must_answer` the name |
| 26 | author-a-test | Add a test for order 7 returning `gadget` and make sure it works | `must_run` `analyze code` and a run by `-bl` or `-t`; `must_not_run` a run of the single file |
| 27 | config-add-profile | Add a profile `nightly` for the smoke tests, writing to `results/nightly`, and check that it takes effect | `must_run` that profile with `profiles show`, `--dry` or `discover` |
| 28 | large-project-counts | This project has tens of thousands of tests: how many, and which tags? | `must_run` `discover tags` and a bounded count; `must_not_run` grep over `.robot` |
| 29 | other-work-no-skill | How many lines does `README.md` have? | `skills: []`, the skill must not load |

Some cases can't fail on the old text, because a good agent recovers (25) or the fix lies in the tool (23); they guard the new text and the tool from here on. Round 1 shows which.

`run.py` gets three small things: a case with `"skills": []` fails if the skill was loaded; the prompt of a Haiku model names the skill only when the case expects it; `--no-skill` runs without a copy of the skill, turns off an installed one where the agent allows it, and drops the check on loading. The README replaces "there is no official runner": `claude plugin eval` runs a plugin's skills with and without it, and skill-creator can tune a `description`; both are for Claude, while this harness runs several agents and checks the way.

The rounds, by the maintainer's rule that nothing small gets its own run and few tokens are used:

| Round | When | Who | What |
|---|---|---|---|
| 1 | Before any correction, against `88b5555` | Sonnet | Cases 21–29, once |
| 2 | When everything is implemented | Sonnet, Copilot CLI | All cases, once |
| | | Opus, Haiku with the skill named | 21–29, and 08, 13, 16, 18, 19 for the debugger, the REPL, selection and global options, once |
| | | Sonnet with `--no-skill` | 01–06, 08, 13, 18, 21, once, for the comparison |
| 3 | At the very end | Codex, opencode | All cases, once |

What fails in round 2 goes back to the text or the check, and only those cases run again. A failed run of Haiku in cases 13 and 16 isn't new by itself (about two of three pass).

## Risks / Trade-offs

- [`.abort` no longer ends at once] → A teardown runs, which can take its time; the second signal and `--skipteardownonexit` remain. `session stop` and `restart` wait for it too, so the tests look at a teardown that hangs.
- [Matching by file name stops in a file nobody meant] → Only when two files share a name and the path is left out; the stop shows the file, and the longer path narrows it.
- [The warning for a keyword breakpoint in a run that simply didn't reach it] → It says what happened, and it doesn't change the exit code.
- [A shorter `SKILL.md` loses something agents relied on] → Round 2 measures it; what's missing goes back.
- [A new `description` loads less often] → Round 2 and D7.
- [Round 2 over all cases costs tokens] → It runs once, with two agents, and the others on a selection.

## Migration Plan

No migration. Plugin and robotcode are released together, so the skill's text on the new behaviour holds from the same release.
