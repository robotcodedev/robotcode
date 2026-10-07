# Design: shorten-long-requirements

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-07 with OpenSpec 1.14.1.

- **What is measured.** `extractRequirementBody` (`dist/core/parsers/requirement-text.js`):
  - Counted: the text between `### Requirement:` and the next heading, with every line trimmed, blank lines and fenced code skipped, and the lines joined with `\n`. Markdown markup counts as written.
  - Not counted: the heading and the scenarios.
  - More than 500 characters is a warning (`MAX_REQUIREMENT_TEXT_LENGTH`), and `--strict` fails on it.
  - In a change, only ADDED requirements are measured, MODIFIED ones are not. Archive validates without `--strict`.
- **OpenSpec's guidance** (specs instruction): split an existing long requirement only on request, in a change made for that purpose. Under MODIFIED, keep its header and every scenario and cut the description to one behavior without changing its meaning. Add each behavior taken out as its own ADDED requirement with its own scenarios. Every requirement needs `SHALL` or `MUST` and at least one scenario.
- **Inventory:** 68 long requirements in 20 main specs. In the open changes, 85 long ADDED and 11 long MODIFIED requirements, in 45 changes. Of the MODIFIED ones:
  - 6 replace requirements of main specs (design D3);
  - 4 replace requirements that another open change adds: `Home page demos` (`migrate-docs-to-starlight` → `home-feature-tour-examples`), `A separate result for each problem` (`intellij-environment-check` → `intellij-wsl-language-server`), `Runs use the configuration's interpreter and environment` (`intellij-run-configuration-target` → `intellij-wsl-runs`) and `Problems are reported before a run` (`intellij-python-interpreter` → `intellij-wsl-runs`);
  - 1, in `library-index`, replaces `Only explicitly named targets are documented`, which no main spec and no open change defines.

## Goals / Non-Goals

**Goals:**
- After this change and the open changes are archived, `openspec validate --specs --strict` passes.
- Not one statement of the specs changes its meaning.

**Non-Goals:**
- No rewording beyond what the split needs, no new behavior, no code changes.
- The titles of the main specs stay as they are.
- No new limit or check in this repository. The specs instruction already gives agents the limit for new requirements.

## Decisions

### D1: Move sentences, do not rewrite them

Each long description is split along its sentences, list items and paragraphs into groups of one behavior with at most 500 characters. The first group stays the description under MODIFIED; every further group becomes an ADDED requirement. Sentences are moved as they are. Only these changes are allowed:
- a pronoun or a short reference that loses its context, such as "they", "both", "the button" or "these flags", is replaced by what it refers to;
- a list item that becomes a sentence of its own gets a subject and its own punctuation;
- a reference to "the next requirement" names the requirement, because ADDED requirements are appended to the end of the main spec;
- a long list, such as the 34 variables of `.vars --user`, is divided between requirements, and the requirement that held it names the requirements that now list it.

### D2: Scenarios

- The scenarios of a MODIFIED requirement stay exactly as they are; a script copies them from the main spec.
- Each ADDED requirement gets one new scenario that states its sentences for a concrete case. It uses examples the spec already uses, such as `Collections`, `common.resource`, `ArgLib` or `Issue: 4409`, and claims nothing that the sentences do not say.

### D3: Requirements left to open changes

Five requirements are replaced by open changes through MODIFIED:
- `The page and its outline`, `Filter while typing` and `Sidebar with the outline of a library page` (`documentation-outline-tree`);
- `Home page` (`home-feature-tour-examples`, `migrate-docs-to-starlight`);
- `Rebot console options` (`migrate-docs-to-starlight`).

This change does not touch them. If it did, the later archive of those changes would replace the shortened text with their long text, or bring back behaviors that this change had moved into other requirements. The three changes shorten them in their own MODIFIED blocks, as in D1, with ADDED requirements in the same change.

### D4: Open changes are shortened in their own artifacts

The long ADDED and MODIFIED requirements of the open changes are plans that are not implemented yet. They are split in place, as in D1 and D2, without a change of their own. Unlike a MODIFIED requirement, an ADDED one has no archived version to keep, so its existing scenarios move with the behavior they test, and a new scenario is written only for a part left without one. Each open change SHALL then pass `openspec validate <change> --strict`.

Where an open change modifies a requirement that another open change adds, both SHALL be split alike: the requirements the ADDED one is split into get the same names in the MODIFIED change. There, each part that the MODIFIED change touches is a MODIFIED requirement of its own, and the other parts stay untouched. Otherwise archiving the later change would bring back the long text, or the behaviors the split moved into other requirements.

`library-index` modifies a requirement that does not exist, which its archive would reject anyway; it is shortened like the others, and the missing requirement stays a problem of that change.

### D5: How it is checked

- A script assembles the delta specs from the new descriptions and the copied scenarios. It reports:
  - every description over 500 characters or without `SHALL`/`MUST`;
  - every name collision;
  - every sentence of the old text that does not appear verbatim in the new one.

  Each reported sentence is checked by hand against D1.
- The change is archived in a copy of `openspec/`, and `openspec validate --specs --strict` runs there. Only the five requirements of D3 may still fail until their changes are archived.

## Risks / Trade-offs

- [A moved sentence changes its meaning in its new place] → The sentence check lists every sentence that is not verbatim, and each one is reviewed. Pronouns are replaced, never left without their reference.
- [New scenarios duplicate existing ones] → Accepted. OpenSpec requires a scenario per requirement, and the existing scenarios must stay with the MODIFIED requirement.
- [OpenSpec warns about more than 10 deltas in one change] → Accepted, as a single cleanup change was chosen; the warning does not block validation or archive.
- [An open change is re-planned later] → Its specs instruction then keeps new requirements under the limit anyway.

## Migration Plan

Nothing to migrate. Rollback is a revert of the archive commit.
