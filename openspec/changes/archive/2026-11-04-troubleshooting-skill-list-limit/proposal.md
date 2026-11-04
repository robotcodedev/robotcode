# Proposal

## Why

Someone with other skills installed, one on a Robot Framework library and one on best practices for writing tests, reported that `robotcode` keeps getting in the way, but only on small models such as Claude Haiku 4.5. We reproduced it: the list of skills an agent chooses from has a limited size. In Claude Code, with a 200K context window, two more skills overflow it, and then the skills used least keep only their name. The Troubleshooting page of the AI agents guide doesn't mention this, so a reader who sees it has no explanation and nothing to try.

The maintainer decided on 2026-11-04 to add it to that page, described for all agents, with Claude Code only as an example.

## What Changes

- **A new entry on the Troubleshooting page:** when the agent loads `robotcode` although another skill fits better, or skips it although it fits. It says why this happens and what helps.
- **The page's `description`:** it lists the symptoms of the page, so it names this one too.

Not part of this change:

- The skill and its `description` stay as they are, by the maintainer's decision. The evals don't change either.
- No other page of the guide changes, so nothing is explained twice.
- The page gives no advice on which model to use: our view on that isn't measured.
- The page doesn't show our run results or the room that Claude Code's own skills take up, which changes with each version.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-agents-guide`: the requirement "Troubleshooting AI agents" lists the new symptom and says what the page tells a reader about it.

## Impact

- `docs/src/content/docs/guides/ai-agents/troubleshooting.md`
- No code, no settings, no generated reference pages.
