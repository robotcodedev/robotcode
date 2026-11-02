# Design

## Context

- **The draft:** `playground/robotcode-demo/agent-sessions/trials/skill-sessions-v2-2026-10-31/skill-draft.diff`, against `next` 06139b5, which is still the tip of `next`. It changes `SKILL.md`, `references/repl.md` (19 929 B) and `references/debugging.md` (19 938 B). In the trials with Claude Code, Copilot CLI and Codex, all nine runs of `repl`, `debug` and `block` were right. In the trial `again`, which needs `status`, `result` and `restart`, Claude Code and Copilot were fully right, and Codex reported honestly that it can't reach the session from its sandbox.
- **Findings and measurements:** `playground/agent-skill-befunde.md`, with the sections on sandboxes of 2026-11-01 and 2026-11-02 and the maintainer's decisions.
- **Sandboxes, measured:**
  - The agents' sandboxes on Linux are per command: each command has its own, with its own processes. A detached session ends with its command.
  - Allowing the session folder and Unix sockets makes sessions work, but then all sessions of the user reach each other, and a sandboxed command can run statements in a session started outside. So that way is out.
  - A real debug task in one `bwrap` around the whole agent, with its own runtime folder, was right in all three agents, without any setting (Claude Code 60 s, Copilot 38 s, Codex 107 s). Nothing outside saw the session.
  - On Windows, Claude Code has no sandbox, and `session start` fails in the sandboxes of Copilot and Codex.
  - Of the three CLIs, only Codex has a tool that writes to a running command.
- **Evals:** Cases 07–10 of `evals/robotcode/` expect `robotcode repl` and `robotcode robot-debug` by regular expression, so they would fail on `robotcode session start …`. `run.py` starts `claude` with whatever plugin is installed, so it can't test a skill that isn't released. The fixture has `paths = ["tests"]`.

## Goals / Non-Goals

**Goals:**
- The skill of the next release teaches sessions and stays honest about sandboxes.
- The evals and a new trial show that it works.

**Non-Goals:**
- Any code in robotcode, and any setting, rule or `sleep` that keeps a session alive or reachable across an agent's per-command sandboxes.
- Measuring macOS or `srt claude`. The sandbox runtime wraps the agent in the same sandbox as the per-command one, so it needs its own settings for the session folder and sockets; it stays unnamed until someone measures it.
- The pages of the AI agents guide, which belong to `docs-ai-agents-guide`.
- The version of the plugin, which changes at the release.

## Decisions

### D1: The draft is the base, with its cuts

The draft removes what agents don't need (the section on the VS Code debugger, hints for a person's console, repeated sentences) to stay under 20 000 B. These cuts stay.

Rejected: a new reference for sessions. It adds a reading step, and the trials show the agents find the text where it is.

### D2: The hint for sandboxes

`references/repl.md`, in place of the draft's paragraph:

> **If a `robotcode session` command fails in a sandbox** — `Can't create the files of the session`, `Can't open the channel of the session`, `doesn't answer`, or the next command finds `No session '…' is open` — your agent runs each command in a sandbox of its own, and a session can't outlive that command or be reached from it. Don't try to leave the sandbox. If your shell tool can keep a process running and write to its input, start `robotcode repl` in it directly: write one input, wait until the output ends with the prompt `>>> `, read the answer, then write the next. Otherwise work out another way yourself. Sessions work as usual when the whole agent runs in one sandbox, such as a container or a virtual machine.

`references/debugging.md`, in place of the draft's sentence:

> If a `session` command fails in a sandbox, handle it as for the REPL (see [repl.md](repl.md#driving-the-repl-from-an-agent)): if your shell tool can keep a process running and write to its input, start `robotcode robot-debug` in it and write each command to it, waiting until the output ends with `(rdb) `.

- The signs are robotcode's own messages, not the texts of the system (`Read-only file system`, `Permission denied`), which differ between Linux and Windows.
- No way for an agent without such a tool, by the maintainer's decision to leave that to the agent. In the measurements, Claude Code and Copilot found one (148 s and 751 s).
- Rejected: the settings that allow the session folder and sockets, and the rule that runs `robotcode session` outside the sandbox. What runs in a sandbox should stay in it.

### D3: What of the old way goes

The draft still has three places from before sessions:

- `SKILL.md`, line 295 of the draft: "`robot-debug`/`repl` are interactive terminal sessions — run them in a terminal …" becomes: they wait at their prompt, so run them as a session and end the stop with `.continue` / `.detach` / `.abort`. The hint on `Ctrl-D` at `(rdb)` stays, and the missing `repl` extra also names `session`.
- `references/repl.md`, line 117 of the draft: "This is what the piped fallback relies on." goes, because that fallback is gone.
- `references/debugging.md`, the sentence in D2.

### D4: Where the two additions go

- **Names of suites:** in `SKILL.md`, in the paragraph "To run or debug one specific test, task, or suite, select it by its longname", because the agent had read past the rule on longnames and guessed the name itself: "The top suite is named after `paths`, not after the project's folder (`paths = ["tests"]` gives `Tests`); take names for `-s` and `-bl` from `robotcode discover suites`."
- **Search:** in `SKILL.md`, in the paragraph "Use `robotcode results` to inspect a finished run", right after the rule against `grep`, because the agent used `grep` to check whether Firefox ran: "To find out whether a value or an argument occurred in a run, use `robotcode results log --search <text>`: it shows only the tests where it appears, also as an argument of a keyword."

`SKILL.md` has no limit of 20 000 B: agents load it through the skill mechanism. Whether `log --search` finds an argument of a keyword gets checked on a real run before the sentence goes in.

### D5: Evals

| Case | Change |
|---|---|
| 07 repl-explore-no-file | The query names Robot Framework, because without that Haiku and Sonnet don't load the skill, not with the old one either; `must_run` `robotcode session start repl` and `robotcode session send`; the rubric says session |
| 08 debug-why-test-fails | `must_run` `robotcode session start debug`, with `-t` or `-bl` on the same line, and `robotcode session send`; the rubric says session and that the agent stops it or says how to end it |
| 09 debug-break-at-line | `must_run` `robotcode session start debug`, with the `--break`, and `robotcode session send`; the rubric as in 08 |
| 10 repl-interactive-breakpoint | `must_run` `robotcode session start repl` and `robotcode session send`; the rubric as in 08 |
| 11 (new) suite-name-from-paths | "Run only the checkout suite."; `must_not_run` a name that starts with the folder of the fixture (`Demo Project` and its spellings) |
| 12 (new) results-search-value | Asks whether the last run used a value that a test passes to a keyword; `must_run` `robotcode results` with `--search`; `must_not_run` `grep` on XML |

`robotcode session stop` is not in `must_run`: when someone asks for a stop, leaving the session paused and saying how to end it is right, as Haiku and Opus did.

`run.py` gets an option `--plugin-dir`, passed on to `claude`, and the README says when to use it. Without it, the harness would test the released skill. It stays a small change: the harness knows nothing else about the plugin.

### D6: The guide

`guides/cli/sessions.md`, the section "Where sessions can't run" (its heading stays, so links keep working):

> A session has to write that folder, open its channel and keep running after the command that started it has returned. Whether it can depends on what the sandbox of an AI agent covers:
>
> - **A sandbox around the whole agent**, such as a container, a dev container or a virtual machine: sessions work there without any setting, and nothing outside that sandbox sees them. An agent's own sandbox for each command has to be off in there; Codex's is on by default (`--sandbox danger-full-access`).
> - **A sandbox for each command**, which Codex uses by default and Claude Code and GitHub Copilot CLI offer: a session can't outlive the command that started it. `session start` says what it can't do and exits with code `252`. An agent with a tool that writes to a running command, as Codex has, can drive `robotcode repl` or `robotcode robot-debug` in its own terminal instead. Claude Code and Copilot CLI have no such tool and have to find another way.
>
> This was checked on Linux and on Windows, where Claude Code has no such sandbox; the way through the terminal only on Linux. macOS is not checked.

### D7: Checks

- **Evals:** Cases 07–12 with Haiku, Sonnet and Opus against the working copy, in an environment without the variables of this agent session.
- **Trial:** `all.sh` with the final skill in a fresh lab, with the three agents and the tasks `repl`, `debug`, `block` and `again`. Then the task `debug` with each agent's per-command sandbox on, and `whole_sandbox.sh` with the three agents.
- **Sizes and links:** `wc -c` on both references, anchors of the changed links, `scripts/sync_manifests.py --check` in the plugin repo, and `npm run docs:build` for the guide.

## Risks / Trade-offs

- [The hint makes `repl.md` too long] → Removing the sentence of D3 pays for most of it. `wc -c` decides, and any further cut comes from text that repeats itself.
- [Agents without a write tool take long in a per-command sandbox] → Accepted by the maintainer; they find a way (148 s and 751 s), and a sandbox around the whole agent avoids it.
- [An agent ignores "Don't try to leave the sandbox", or its tool asks the user anyway] → The trial shows it. The agent's own permission system decides in the end.
- [The regular expressions of the evals are too tight] → The runs across three models show it. Where the behavior is right, the expression gets wider, not the skill longer.
- [Measured on two systems only] → The guide says so.

## Migration Plan

None. The skill reaches users with the next release, through the existing `agent-plugin-release` flow: version on `next`, sync, tag, `main`.
