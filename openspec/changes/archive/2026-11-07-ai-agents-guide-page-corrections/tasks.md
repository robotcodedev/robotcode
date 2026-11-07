# Tasks

## 1. Pages of the guide

- [x] 1.1 How the Skill Works: delete "How it works" and "See also", new intro, the debugger row of the table and the reason for the debugger over the REPL, tasks without `--rpa`, "When robotcode is missing" with the three meanings of `No such command`, "AI-agent detection" corrected and shortened, with all variables (F1, F6, F10, F11, F12, F18, F33, O1, O2, S1, W16, W21)
- [x] 1.2 Setting Up: prerequisites without the contradiction to VS Code, no "Open Plugins", the plugin's README for skill folders, "Updating the plugin", PyCharm with the agents named, no claim about Copilot Chat owning `chat.plugins.marketplaces`, no "alongside", tags from 2.6.0 on, `chat.plugins.enabled`, "Special cases" after "Checking that it works" (F3, F4, F7, F8, F13, F15, F16, F30, F31, F32, O7, R11, S3, W2, W13, W20, W21)
- [x] 1.3 Troubleshooting: one heading per symptom, the update commands, results before the debugger, the wrong-skill entry worded clearly (F1, F2, F10, F32, F34, R4, S4, W1, W15, W17, W21)
- [x] 1.4 Briefing the Agent: GitHub Copilot CLI, `chat.useAgentsMdFile` in local sessions, no "never repeat", clear references, heading of the example (F24, F25, F26, R10, W4, W9, W10, W11)
- [x] 1.5 Overview: the skill explained at its first use, no "Open Plugins", PyCharm in one clause, no "turn the plugin on", one link to the tutorial (D17, F3, F7, F29, S8, W12)

## 2. VS Code extension

- [x] 2.1 `chatPluginsManager.ts`: the error message of *Add/Remove Chat Plugins Marketplace* shows the error instead of naming GitHub Copilot Chat (F4)

## 3. Verification

- [x] 3.1 `npm run docs:build` passes without broken links, and every anchor that another page links is in the built pages
- [x] 3.2 `eslint` and `tsc` on the extension and `npm run compile` pass
- [x] 3.3 `openspec validate ai-agents-guide-page-corrections --strict` passes

## Workflow follow-up

- Archive the change, syncing the two modified requirements into `openspec/specs/ai-agents-guide/spec.md`.
- The layout of the plugin (F3) stays a task of its own in `robotframework-agent-plugins`.
