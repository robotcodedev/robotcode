---
title: Checking Before a Push
description: "Step 6 of the tutorial: ask an AI agent to check a Robot Framework project before a push, also with the CI profile, decide what gets fixed, and have an intended finding marked as such."
sidebar:
  label: 6. Checking Before a Push
  order: 150.46
---

Before you push, you want to know what is wrong with what you have. A test run doesn't tell you all of it, because it only reaches the keywords a test calls. So ask the agent for a check, and then decide what gets fixed, what stays, and what is intended.

To follow along, use the [example project](/guides/ai-agents/working-with-the-agent/#following-along).

## Ask for a check

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Check the project for problems before I push.

</div>

<div class="rc-session-calls">

- [`robotcode analyze code`](/guides/cli/analyzing-code/)
- [`robotcode analyze code --collect-unused`](/guides/cli/analyzing-code/)

</div>

<div class="rc-session-answer">

**Agent:** The static analysis found one error, and it will break at runtime if `Checkout` is ever called.

- **Error:** `resources/orders.resource:31:5` has `KeywordNotFound: No keyword with name 'Submit Ordr' found`. It's a typo in the `Checkout` keyword. The fix is to change `Submit Ordr` to `Submit Order`, which is defined at line 23 of the same file.

I also ran the opt-in unused-keyword check. It gave two warnings, and the error above is the likely cause of both:
- `Submit Order` and `Checkout` are not used anywhere.
- `Submit Order` looks unused because the typo stops `Checkout` from referencing it.
- `Checkout` isn't called by any test or other keyword. If it's meant to be a shared resource keyword, you can ignore the warning.

I haven't changed anything. … I only ran static analysis, not the tests themselves. Want me to fix the typo and run the tests?

</div>

</div>

"Check the project" leaves it to the agent what that means. So look for what it checked and what it left out: this agent checked the code and didn't run the tests, and another may run them too, or read every file. If you want the tests to run as well, say so.

The typo is what a test run can't show you, because no test calls `Checkout`.

## Check it the way CI does

The check depends on the configuration, so ask for the one that counts:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Check it with the profile our CI uses too.

</div>

<div class="rc-session-calls">

- [`robotcode profiles list`](/reference/cli/#profiles)
- [`robotcode -p ci analyze code`](/guides/cli/analyzing-code/)

</div>

<div class="rc-session-answer">

**Agent:** I checked with the `ci` profile, which is the one `.github/workflows/tests.yml` runs (`uv run robotcode -p ci robot`). The result is the same as before: one error, no warnings.

- **Error:** `resources/orders.resource:31:5` has `KeywordNotFound: No keyword with name 'Submit Ordr' found`. This is the same typo as before. It should be `Submit Order`.

The `ci` profile only changes `BASE_URL`, to `https://staging.shop.example`. It doesn't change which files or keywords get analyzed, so the profile makes no difference to the analysis.

…

</div>

</div>

Here, it makes no difference. With a profile that sets other variables or another Python path, a keyword or an import can resolve differently, and then the same check finds something else. Notice that you didn't have to name the profile. The agent looked up which one CI uses.

## Ask what nothing uses

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Are there keywords or variables that nothing uses?

</div>

<div class="rc-session-answer">

**Agent:** Yes, I ran `robotcode analyze code --collect-unused` on the whole project earlier. It found two unused keywords and no unused variables.

- **`Submit Order`** (`resources/orders.resource:23`) looks unused only because of the typo. `Checkout` calls `Submit Ordr`, so the reference doesn't resolve. Fixing the typo should clear this warning.
- **`Checkout`** (`resources/orders.resource:28`) really is unused. No test or keyword calls it. Either a test is missing, it's dead code, or it's meant as a shared keyword. …

…

</div>

</div>

[`robotcode analyze code`](/guides/cli/analyzing-code/) is the command behind the check. An unused keyword is a question for you, not necessarily a mistake, and only you know the answer.

## Decide what gets fixed

Say what you want changed, and say what you don't:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Fix the typo in `Checkout`. Leave everything else as it is.

</div>

<div class="rc-session-calls">

- [`robotcode analyze code --collect-unused`](/guides/cli/analyzing-code/)

</div>

<div class="rc-session-answer">

**Agent:** I fixed the typo in `Checkout` at `resources/orders.resource:31`. It now calls `Submit Order`, and I changed nothing else.

I re-ran the analysis with `--collect-unused`. The error is gone and `Submit Order` no longer shows as unused, as expected. One warning is left: `Checkout` isn't called anywhere. I left that alone, as you asked.

I haven't run the tests.

</div>

</div>

## Mark what is intended

If a finding is intended, say why, and have it marked. Otherwise every later check reports it again, and you stop reading the reports:

<div class="rc-session">

<div class="rc-session-prompt">

**You:** `Checkout` is for the next sprint, so nothing uses it yet, and that's intended. Mark it so that the check doesn't report it again, and run the check again.

</div>

<div class="rc-session-calls">

- [`robotcode analyze code --collect-unused`](/guides/cli/analyzing-code/)

</div>

<div class="rc-session-answer">

**Agent:** I marked `Checkout` as intentionally unused. The check now reports 0 errors, 0 warnings, 0 infos and 0 hints across all 8 files.

I added `# robotcode: ignore[KeywordNotUsed]` to the end of the `Checkout` line in `resources/orders.resource`. That is the narrowest scope: it covers only this keyword and only this one diagnostic. Everything else in the file is still checked.

…

</div>

</div>

Look at where the comment went, because that decides what it covers. At the end of a line, it covers that line. At the start of a line, it covers the rest of the file, and that can be more than you asked for. [Diagnostics Modifiers](/reference/diagnostics-modifiers/#scope-of-a-modifier) has the details.

## See how it checked

<div class="rc-session">

<div class="rc-session-prompt">

**You:** Which `robotcode` commands did you use for the check? I want to run them myself.

</div>

<div class="rc-session-answer">

**Agent:** Run these from the project root …

```bash wrap
# Static check of the whole project, no tests run
robotcode analyze code

# Same check with the CI profile (the one in .github/workflows/tests.yml)
robotcode -p ci analyze code

# Also report unused keywords and variables (off by default)
robotcode analyze code --collect-unused
```

The last command is the one that now ends with `Errors: 0, Warnings: 0`. Run it on the whole project, not on single paths. With paths, only references inside the selection count, so keywords used elsewhere would show up as unused.

I also used `robotcode profiles list` to find the `ci` profile. I didn't run the tests. CI would run them with `robotcode -p ci robot`.

…

</div>

</div>

Run them. [Analyzing Code](/guides/cli/analyzing-code/) shows what else `robotcode analyze code` finds and how to use it in CI, and [`robotcode profiles list`](/reference/cli/#profiles) and [`robotcode robot`](/reference/cli/#robot) are in the reference. Your agent may name other commands, such as [`robotcode config show`](/reference/cli/#config).

## In your own project

- Say what the check should cover, or look at what the agent covered.
- Ask for the check with the profile your CI uses.
- Decide what gets fixed, and say what stays as it is.
- Have what is intended marked in the file, and look at where the mark went.
- Ask for the commands, and run them yourself.
