# Design

## Context

- **The draft:** `playground/robotcode-demo/agent-sessions/trials/skill-sessions-v2-2026-10-31/skill-draft.diff`, against `next` 06139b5, which is still the tip of `next`. It changes `SKILL.md`, `references/repl.md` (19 929 B) and `references/debugging.md` (19 938 B). In the trials with Claude Code, Copilot CLI and Codex, all nine runs of `repl`, `debug` and `block` were right. In the trial `again`, which needs `status`, `result` and `restart`, Claude Code and Copilot were fully right, and Codex reported honestly that it can't reach the session from its sandbox.
- **Findings and measurements:** `playground/agent-skill-befunde.md`, with the sections on sandboxes of 2026-11-01 and 2026-11-02 and the maintainer's decisions.
- **Sandboxes, measured:**
  - The agents' sandboxes on Linux are per command: each command has its own, with its own processes. A detached session ends with its command.
  - Allowing the session folder and Unix sockets makes sessions work, but then all sessions of the user reach each other, and a sandboxed command can run statements in a session started outside. So that way is out.
  - A real debug task in one `bwrap` around the whole agent, with its own runtime folder, was right in all three agents, without any setting. Nothing outside saw the session.
  - On Windows, Claude Code has no sandbox, and `session start` fails in the sandboxes of Copilot and Codex.
  - Of the three CLIs, only Codex has a tool that writes to a running command.
- **Evals:** See D5. The fixture has `paths = ["tests"]`.
- **The review:** After the first round, the maintainer read and tried the skill: it explains what an agent doesn't need and repeats itself. `playground/agent-skill-befunde.md`, section "Durchsicht auf Überflüssiges und Wiederholungen", lists the places, about 27 KB of 138 KB.
- **Measured for this, in the same file, judged by how the agent worked and not by speed:**
  - Session first against a question at the start, 88 runs: 26 of 30 against 26 of 30 and 24 of 28. Claude Code, Copilot CLI and opencode go to sessions either way. Codex goes to its terminal with the question. Only Haiku's mistakes differ: asked to try something out, it went around the REPL with the question in 4 of 4 runs and used a session without it in 2 of 2, though with today's skill it also fed `printf` into the REPL in one of two runs.
  - Where a rule stays, 240 runs: 47, 49 and 51 of 60 against 48 of 60 for today's longer skill. That is within the noise, and the cases on the moved rules pass everywhere. The draft is the output `in-section` of `playground/robotcode-demo/agent-sessions/trials/skill-structure-2026-11-02/make_skill_variants.py`.
  - Haiku with the skill named in the prompt, 36 runs each: today's skill from 25 to 34, the shortened one from 23 to 36 or 34. Its weakness is loading the skill by itself, not the text.

## Goals / Non-Goals

**Goals:**
- The skill of the next release teaches sessions and stays honest about sandboxes.
- It says only what an agent needs, and each rule once.
- The evals and a new trial show that it works.

**Non-Goals:**
- Any code in robotcode, and any setting, rule or `sleep` that keeps a session alive or reachable across an agent's per-command sandboxes.
- Measuring macOS or `srt claude`. The sandbox runtime wraps the agent in the same sandbox as the per-command one, so it needs its own settings for the session folder and sockets; it stays unnamed until someone measures it.
- The pages of the AI agents guide, which belong to `docs-ai-agents-guide`.
- The version of the plugin, which changes at the release.
- The skill's `description`, see D12.
- The harness of the evals as a task of this plan: the maintainer chose to extend it directly (D5).

## Decisions

### D1: The draft is the base, with its cuts

The draft removes what agents don't need (the section on the VS Code debugger, hints for a person's console, repeated sentences) to stay under 20 000 B. These cuts stay, and D9 goes further.

Rejected: a new reference for sessions. It adds a reading step, and the trials show the agents find the text where it is.

### D2: The hint for sandboxes

`references/repl.md`, in place of the draft's paragraph. The way through the terminal is the question right above it (D8):

> **If a `robotcode session` command fails in a sandbox** — `Can't create the files of the session`, `Can't open the channel of the session`, `doesn't answer`, or the next command finds `No session '…' is open` — your agent runs each command in a sandbox of its own, and a session can't outlive that command or be reached from it. Don't try to leave the sandbox. Without a tool as described above, work out another way yourself. Sessions work as usual when the whole agent runs in one sandbox, such as a container or a virtual machine.

`references/debugging.md`, in place of the draft's sentence:

> If a `session` command fails in a sandbox, handle it as for the REPL (see [repl.md](repl.md#start-or-reuse-a-repl)).

- The signs are robotcode's own messages, not the texts of the system (`Read-only file system`, `Permission denied`), which differ between Linux and Windows.
- No way for an agent without such a tool, by the maintainer's decision to leave that to the agent. In the measurements, Claude Code and Copilot found one.
- Rejected: the settings that allow the session folder and sockets, and the rule that runs `robotcode session` outside the sandbox. What runs in a sandbox should stay in it.

### D3: What of the old way goes

The draft still has three places from before sessions:

- `SKILL.md`, line 295 of the draft: "`robot-debug`/`repl` are interactive terminal sessions — run them in a terminal …" goes with the Gotchas (D10). The warning against starting one without input and waiting stays, once with the REPL and once with the debugger. `references/install.md` names `session` among the commands of the `repl` extra.
- `references/repl.md`, line 117 of the draft: "This is what the piped fallback relies on." goes, because that fallback is gone.
- `references/debugging.md`, the sentence in D2.

### D4: Where the two additions go

- **Names of suites:** in `SKILL.md`, in the section on selecting one test or suite (D10), in the paragraph on selecting by longname, because the agent had read past the rule on longnames and guessed the name itself: "The top suite is named after `paths`, not after the project's folder (`paths = ["tests"]` gives `Tests`); take names for `-s` and `-bl` from `robotcode discover suites`."
- **Search:** in `SKILL.md`, in the paragraph "Use `robotcode results` to inspect a finished run", right after the rule against `grep`, because the agent used `grep` to check whether Firefox ran: "To find out whether a value or an argument occurred in a run, use `robotcode results log --search <text>`: it shows only the tests where it appears, also as an argument of a keyword."

`SKILL.md` has no limit of 20 000 B: agents load it through the skill mechanism. Whether `log --search` finds an argument of a keyword gets checked on a real run before the sentence goes in.

### D5: Evals

Done on `next`: the first round with this plan (`4362bec`), the rest directly on the maintainer's decision (`35baf03`, `dce5bf2`). This records what they check.

`run.py` runs the cases with several agents and models (`--agent claude:haiku --agent copilot --agent codex --agent opencode:…`), each run in a fresh copy of the project and, on Linux, in one bubblewrap sandbox around the whole agent. `--plugin-dir` takes the skill from a folder, so it can test what isn't released. Besides the regular expressions, it checks that the skill was loaded, the agent's answer (`must_answer`) and, with `drive`, how the agent drove the REPL or the debugger: not through a fixed list of inputs or a FIFO, not several steps at once, and a session stopped, or said to be open.

| Case | What it covers |
|---|---|
| 07–10 | A task in the REPL or the debugger, through a session or at the prompt. Case 07 names Robot Framework, because without that Haiku and Sonnet don't load the skill, not with the old one either |
| 11, 12 | Names of suites, searching a finished run |
| 13, 14 | A plain "try it out", a `FOR` block |
| 15, 16 | A session started earlier, a breakpoint set during the run |
| 17 | The agent's own sandbox for each command |
| 18, 19 | One test by longname, a global option before the subcommand |

`robotcode session stop` is not in `must_run`: when someone asks for a stop, leaving the session paused and saying how to end it is right, as Haiku and Opus did.

### D6: The guide

`guides/cli/sessions.md`, the section "Where sessions can't run" (its heading stays, so links keep working):

> A session has to write that folder, open its channel and keep running after the command that started it has returned. Whether it can depends on what the sandbox of an AI agent covers:
>
> - **A sandbox around the whole agent**, such as a container, a dev container or a virtual machine: sessions work there without any setting, and nothing outside that sandbox sees them. An agent's own sandbox for each command has to be off in there; Codex's is on by default (`--sandbox danger-full-access`).
> - **A sandbox for each command**, which Codex uses by default and Claude Code and GitHub Copilot CLI offer: a session can't outlive the command that started it. `session start` says what it can't do and exits with code `252`. An agent with a tool that writes to a running command, as Codex has, can drive `robotcode repl` or `robotcode robot-debug` in its own terminal instead. Claude Code and Copilot CLI have no such tool and have to find another way.
>
> This was checked on Linux and on Windows, where Claude Code has no such sandbox; the way through the terminal only on Linux. macOS is not checked.

### D7: Checks

- **First round, done:** Cases 07–12 with Haiku, Sonnet and Opus, and the trial with the three agents, with a per-command sandbox, around the whole agent and on Windows (tasks 2.4 and 3.1–3.4).
- **The rework:** Cases 01–06 and 08–19 against the working copy with Haiku (three times), Sonnet, Opus, Copilot CLI, opencode with a model through Copilot, and Codex. What decides is how the agent worked, by the checks and the rubric. Per agent, it must not fall below the skill before the rework.
- **Sizes and links:** `wc -c` on both references, every link and its anchor in the whole skill, `scripts/sync_manifests.py --check` in the plugin repo.

### D8: A question at the start of both references

By the maintainer's decision, this replaces "a session first, the terminal only when it fails in a sandbox". By the checks both are equal (see Context), and with the question an agent that has such a tool doesn't need a failed attempt first.

`references/repl.md`, under "Start or reuse a REPL":

> **Can your shell tool keep a command running and write to its input?** Tools such as `write_stdin` or `send_to_terminal` do that; a background process that you feed through a file or a FIFO doesn't count.
>
> - **Yes:** start `robotcode repl` there and work at its prompt: write one input, wait until the output ends with the prompt `>>> `, read the answer, then choose the next input from what you saw. `.exit` ends it.
> - **No:** run the REPL as a **session**. It runs in the background and keeps its state — variables, imports, open browsers and connections — between your commands, and each command returns with the answer to one input: send one input, read the answer, then choose the next input from what you saw.

`references/debugging.md` says the same under a new section "Start or reuse a debug session", with `robotcode robot-debug` and the prompt `(rdb) `. That section moves from the end to right after the contents, as in `repl.md`, and the headings "… from an agent" go, because every reader of the skill is an agent. `SKILL.md` says the same in short with the REPL and the debugger.

The wording asks for the tool rather than whether the agent "can work interactively": both behaved the same in the measurements, and the maintainer chose this one. The two names can change with the versions of those agents.

### D9: What goes

All four groups of the review, with the places in `playground/agent-skill-befunde.md`:

- **What works automatically:** the input of the REPL, paging and colors, `doc browse` in an agent session, the language server in an editor, "comes from the extra …", the console output staying visible. For people, this stays in `guides/ai-agents/how-the-skill-works`.
- **What the agent sees anyway or can't send:** `Ctrl-D`, `.exit` at a stop, error messages word for word, the format of the banner, `No profiles defined.`
- **What is explained several times:** see D10, and whole blocks such as the contents of `SKILL.md`, the section on installing there, the example shared by `repl.md` and `authoring.md`, and the validation at the end of `repl.md`.
- **What isn't for agents:** phrases that trigger the skill in references (`SKILL.md` has them), general Robot Framework knowledge, `.clear`, the section on the REPL's exit code at a terminal, xUnit output, `repl-server`, `testdoc`.

### D10: Where a rule stays

In `SKILL.md`, in the section on its topic. The other places link there, and a reference adds only what its topic needs. The Gotchas go, because 13 of their 14 points repeat the sections above them.

| Rule | Section |
|---|---|
| One test or suite by longname, not by a `.robot` file | "Selecting one test or suite", new; it also takes the options that work everywhere |
| A real test: the debugger, not the REPL | "A real test case: the debugger, not the REPL", under debugging |
| `discover`, not grep | Discovery |
| Not reading `output.xml`; how to report | Interpreting results |
| `output.xml` is no sign of the end of a run | Running tests |
| `robotcode doc` first | Documentation lookup priority |
| Global options before the subcommand | Global options worth knowing |
| Trying before installing, no isolated runners | The start of `SKILL.md`; the rest in `references/install.md` |
| The exit code of `analyze` | Static analysis |

The maintainer's reason for this place: `-bl` works for running, debugging, discovering and more, so it needs one place to link to. Rejected: all rules in the Gotchas, far from the commands they concern; all rules in the mode list, where `-bl` would hang on one mode. Measured, none of the three differs beyond the noise (see Context).

### D11: What is wrong rather than repeated

- `references/workflows.md`, `references/authoring.md` and the examples in `SKILL.md` show `robotcode robot-debug` without saying how to drive it, because the first round only touched three files. The options hold either way, so the examples stay, and the text links to how to drive it.
- The section "A session, end to end" of `references/debugging.md` hands over a single `.robot` file, uses no session and shows `(rdb)`, which answers of a session don't have. It goes; the section on starting already shows the flow.
- `references/results.md` says `report.html` where the tree of keywords is in `log.html`.
- `references/debugging.md` doesn't say that several steps in one shell command, or a shell loop over inputs, skip reading the answers. Opus did that with every variant, so a sentence goes in with "One `send` per command".

### D12: Naming the skill with smaller models

Haiku hardly loads the skill by itself for questions on a finished run, and it does far better when the prompt names the skill (see Context). The maintainer chose to say so in the guide, which `docs-ai-agents-guide` does in `how-the-skill-works` and `troubleshooting`. Not changed for now: the skill's `description`, and a line in the project's `AGENTS.md`.

## Risks / Trade-offs

- [A reference gets too long] → D9 leaves both well under the limit. `wc -c` decides.
- [A rule that stands once gets read past] → Cases 04, 05, 11, 18 and 19 check the moved rules, and they passed in all variants.
- [With the question, Haiku goes around the REPL for a plain "try it out"] → Measured and accepted by the maintainer: by the checks it is equal overall, and case 13 shows it.
- [The names `write_stdin` and `send_to_terminal` change] → The question describes what the tool does; the names are only examples.
- [Agents without a write tool go through more in a per-command sandbox] → Accepted by the maintainer; they find a way, and a sandbox around the whole agent avoids it.
- [An agent ignores "Don't try to leave the sandbox", or its tool asks the user anyway] → The trial shows it. The agent's own permission system decides in the end.
- [The regular expressions of the evals are too tight] → The runs across three models show it. Where the behavior is right, the expression gets wider, not the skill longer.
- [Measured on two systems only] → The guide says so.

## Migration Plan

None. The skill reaches users with the next release, through the existing `agent-plugin-release` flow: version on `next`, sync, tag, `main`.
