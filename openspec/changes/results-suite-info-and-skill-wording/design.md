# Design

## Context

Everything below was tried on 2026-11-03 with robotcode from `main` aa8017cf6, RF 7.5.1, in the session project of the guide's recordings.

- **`results log --suite-info`:**
  - `_LogCollector.visit_suite` in `results.py` collects every suite with a test left after the filters, in the order of the run, so a suite comes before the suites and the tests below it.
  - `--format json` therefore has the parent suites: for `-bl "Tests.Orders.Order Coffee"`, `suites` holds `Tests` with its metadata and `Tests.Orders`.
  - The text renderer (`_render.py:393-400`) looks up the suite of each test and prints only that header, so `Tests` never shows, also not with `-bl "Tests"`.
- **The file of a run:**
  - `-o/--output` is an option of `summary`, `show`, `log` and `stats`; `diff` takes its files as arguments.
  - `robotcode results -o X summary` answers `No such option '-o'`, and `robotcode results summary X` answers `Got unexpected extra argument`, both with exit code 2.
  - In the recordings: `results -o` in `another-browser` and `a-task`, a file as an argument in `a-profile-for-the-ci-server` and `before-a-push`. `SKILL.md` asks to read `references/results.md` before any `results` command, and in these four cases the agent hadn't.
- **`robotcode session start`:** it prints `Started session repl-31b82175.`, for a debug session followed by the output up to the first stop. `SKILL.md` says "prints its ID" in "Debugging a run" and in "REPL". `--format json` prints an object with `id`.
- **`SKILL.md`** has a body of about 4136 tokens (cl100k), and the target of `skill-review-fixes` is at most 4800.
- **The evals:** a case has `query`, `must_run`, `must_not_run` and `must_answer`, with regular expressions over the commands. In the fixture `demo-project`, `Login Works` in `tests/login.robot` fails on purpose and calls `Login With Credentials`.

## Goals / Non-Goals

**Goals:**
- The text output of `--suite-info` answers what the top suite's documentation and metadata are, without the Python API.
- An agent names the file of another run right at the first try, without opening a reference.

**Non-Goals:**
- A change to `robotcode results` for how it takes its file, or a better error message there. The maintainer chose the sentence in the skill; a file as an argument stays an idea in case the eval shows that the sentence isn't enough.
- A change to what `session start` prints.

## Decisions

### D1: The text output walks the list of suites

The renderer goes through `data.suites` in its order. When a test has another suite than the one before it, the renderer prints the headers from where it stopped up to and including that suite. Because the collector adds a suite before what lies below it, the suites printed that way are that suite and the ones above it that haven't been printed yet.

```python
remaining_suites = iter(data.suites or [])
...
if with_suite_info and t.suite != current_suite:
    current_suite = t.suite
    for suite in remaining_suites:
        out.append("")
        out.append(_render_suite_header_md(suite, full_paths=full_paths))
        if suite.full_name == t.suite:
            break
```

`suite_index` goes, and `_render_suite_header_md` no longer gets `None`.

Rejected:
- Finding the parents by splitting the long name at its dots: a suite's own name can contain dots.
- A `parent` field in `LogSuite`: it changes the JSON output for something the order already says.

### D2: One level of heading

All suites stay at `## Suite:` with their long name, and tests at `### Test:`. The long name shows the nesting.

Rejected: a heading level per depth. Markdown has six levels, and the level of a test would depend on how deep its suite lies.

### D3: Every suite gets a header

A suite without documentation and metadata gets a header too, as in `log.html`: name, source and status say something, and the rule stays simple.

Rejected: a header only for a parent that has documentation or metadata. It saves a few lines, but a reader can't tell from a missing header whether the suite is plain or left out.

### D4: The sentence on the file of another run

It goes into the first paragraph of "Interpreting results" in `SKILL.md`, after the sentence that asks to read the reference:

> For a run other than the last one, `-o <file>` goes after the subcommand: `robotcode results summary -o <file>`.

`diff` needs no word: the list below that paragraph says `diff BASELINE [CURRENT]`.

`references/results.md` keeps its section on `-o`, which says what the option accepts and how the file is found without it. The new sentence only says where the option goes, and it is in `SKILL.md` because that is what the agents read before a short query.

### D5: The wording on starting a session

- "Debugging a run": "`robotcode session start debug <options>` runs to the first stop and prints `Started session <ID>.` and the output up to that stop".
- "REPL": "`robotcode session start repl` prints `Started session <ID>.`".

`references/repl.md` already shows the sentence, and `references/debugging.md` stays as it is. There is no eval case of its own: one session in 13 did this, and the agent corrected itself in the next command.

### D6: The eval case and its rounds

`evals/robotcode/cases/30-results-of-another-run.json`, with the query *"Run the login suite with its results in a folder of their own, so that `results/` stays as it is, and tell me which keywords the failed test called in that run."*

- The console of a run doesn't show the keywords, so the agent needs `robotcode results log`, and a folder of its own means naming the file.
- `must_run`: `robotcode results` with a subcommand and `-o` or `--output` after it.
- `must_not_run`: `results -o …` and `results <subcommand> <file>`. A first wrong try fails the case even if the agent corrects itself, because that try is what the sentence is meant to save.
- `must_answer`: `Login With Credentials`.

Rounds, following the maintainer's rule to spend few tokens on evals:
- Before the sentence: Sonnet, 3 runs.
- With the sentence: Sonnet, 3 runs, and GitHub Copilot CLI once.
- Codex and opencode don't run for one sentence.

A wrong way goes back to the text and a right way with a failed check goes back to the check, and only that case runs again. If the case passes on the old text, its query changes once, because the recordings showed the mistake in chained commands right after a run. If it still passes, the result goes into the findings, and the sentence stays, as the maintainer decided it.

## Risks / Trade-offs

- [The text output with `--suite-info` gets longer] → Only with the option, which is off by default.
- [A script reads the text output] → The JSON output doesn't change, and it is the form for scripts.
- [The sentence says part of what `references/results.md` says] → It only says where the option goes. The requirement "One place for a rule" of `agent-skill-guidance` lets a rule stay in the section on its topic, which "Interpreting results" is.
- [The sessions on the guide's pages show the old forms] → They stay as recorded, and the guide says that they show one run of one agent.
