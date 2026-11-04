# Design

## Context

See `proposal.md` for the motivation. The Troubleshooting page is sorted by what the reader sees the agent do, and each entry is one paragraph: the symptom in bold, the cause, what helps. Its first entry covers an agent that doesn't use `robotcode` at all, and it links to "When the agent loads the skill" on How the Skill Works.

Measured on 2026-11-04 with Claude Code 2.1.316, in a demo config without claude.ai sync. The scripts and results stayed in the session's scratchpad, not in the repo.

- **Window and budget:** Haiku 4.5 reports a 200K window. Its debug log says `Skill listing over budget: 17 skills, 8609 chars > 8000 budget`. Haiku 5.5, Sonnet 5.5 and Opus 5.5 report 1M.
- **Room:** Claude Code's own skills take about 6850 characters and kept their text in all runs. Our entry takes 1045.
- **Overflow, with two invented skills of about 350 characters each:** with 864 uses, ours kept its text and the two unused skills lost theirs. Never used, ours lost its text and the two kept theirs. `skillListingBudgetFraction: 0.02` gave all of them their text.

Which skills were loaded, in 3 runs each, with invented skills with telling names, ours much used, and read tools only:

| Task | Haiku 4.5, 8000 characters | Haiku 4.5, budget 2 % | Haiku 5.5, 1M |
| --- | --- | --- | --- |
| Write a test with the Browser library | ours 3/3, others 0/3 | ours 0/3, others 3/3 | ours 0/3, others 1/3, none 2/3 |
| Question on the Browser library | ours 1/3, others 2/3 | others 3/3 | others 2/3, none 1/3 |
| Question on best practices | others 3/3 | others 3/3 | others 2/3, none 1/3 |

Not run, read in the sources only:

- **Codex** (tag `rust-v0.166.0`, `codex-rs/ext/skills/src/render.rs`, `config.rs`): 2 % of the window in tokens, `skills.max_context_tokens`, 8000 characters when the window is unknown. Long descriptions are cut first, then only names stay, then skills are left out with a warning.
- **VS Code** (`main`, `computeAutomaticInstructions.ts:477`): 15,000 characters in list order, the rest by name up to 5000 characters.
- **Copilot CLI:** only one sentence in its changelog, without a number.

## Goals / Non-Goals

**Goals:**

- A reader who sees the symptom learns why it happens and what helps, whichever agent they use.

**Non-Goals:**

- Telling readers which model to use.
- Listing every agent's limits. They change with each version.

## Decisions

### On the Troubleshooting page only

The entry goes on Troubleshooting because a reader arrives there with this symptom. It isn't repeated on How the Skill Works, so nothing is explained twice.

### Described for all agents, with Claude Code as the example

The text speaks of agents in general: some tie the limit to the context window, others use a fixed size. Claude Code is the one example with figures, because that is what we measured. An entry about Claude Code alone was the first draft; the maintainer asked for a general description.

### The agreed text

The entry comes right after the first one, because both are about which skill the agent uses:

> **The agent loads `robotcode` although another skill fits better, or skips `robotcode` although it fits.** Agents choose a skill from a list of the installed skills and their descriptions, and that list has a limited size. Some agents tie the limit to the context window, so it is tighter with a small window; others use a fixed size. In Claude Code, for example, it is 1 % of the window: 8000 characters at 200K, most of which its own skills already use, and `claude --debug` warns when the list overflows. With several skills installed, the list can overflow. Descriptions are then shortened or dropped, often leaving only the name, and the agent can no longer tell what the skill is for. Which skill is hit first depends on the agent: the one used least, the one with the longest description, or the last one in the list. Name the skill you want in your request, and remove or turn off skills you don't need. Some agents also let you raise the limit, such as Claude Code with [`skillListingBudgetFraction`](https://code.claude.com/docs/en/settings-reference#skilllistingbudgetfraction) and Codex with `skills.max_context_tokens`.

The three cases in "Which skill is hit first" are, in order, Claude Code, Codex and VS Code. Copilot CLI isn't named, because its changelog gives no number and doesn't say whether it means the list or a single skill.

### What the entry leaves out

- **Run results and the 6850 characters:** they change with each Claude Code version.
- **Advice on the model:** the view that a small model isn't the right choice for writing tests isn't measured. 200K itself is enough for the skill: 149 eval runs ended at about 28,000 tokens in the median and about 40,000 at most, though with short tasks in a small demo project.
- **`skillOverrides`:** Claude Code's documentation says "Plugin skills are not affected by `skillOverrides`".

### The skill's `description` stays

Fitting two skills of 350 characters beside ours at 200K would need a `description` of about 400 characters instead of 1022. With 931 characters, Sonnet already passed case 02 only 2 of 5 times against 5 of 5, and this would affect everyone on a larger window too. The maintainer decided that it stays.

### Check the advice to name the skill first

Naming a skill is the advice the page already gives, but it wasn't tested with only the name left in the list. A few runs on Haiku 4.5 check it before the text is final. If it doesn't help, the sentence changes and the maintainer sees the result.

## Risks / Trade-offs

- [The figures for Claude Code and the settings of other agents can change] → The entry gives one example and links to Claude Code's settings, and leaves out what changes fastest.
- [Codex and VS Code were only read in their sources, not run] → The entry names no figures for them, and the only Codex detail is a setting read in its source.
- [The runs behind the symptom are few and used invented skills] → The page reports the mechanism, which the debug log and the listing show directly, not rates.
