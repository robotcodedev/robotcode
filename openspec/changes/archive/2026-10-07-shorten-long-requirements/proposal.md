# Proposal: shorten-long-requirements

## Why

Since OpenSpec 1.14.1, a requirement description longer than 500 characters is a warning, and `openspec validate --strict` fails on it (Fission-AI/OpenSpec#1976, #2020). Our specs were written before agents knew the limit: 68 requirements in 20 main specs exceed it, and 85 ADDED requirements in 43 open changes would add more when they are archived. `--strict` should pass, so that it can be used as a check.

## What Changes

- **Main specs.** 63 requirements in 20 specs are shortened as OpenSpec's specs instruction describes. The description under MODIFIED keeps one behavior, and every existing scenario stays. Each behavior taken out becomes its own ADDED requirement with its own scenario. The sentences are moved, not rewritten, wherever they fit under 500 characters.
- **No behavior changes.** Every statement of the current text is kept with the same meaning. No code, test or documentation changes.
- **Left to the open changes.** Five requirements are rewritten by open changes, and those changes shorten them themselves:
  - `The page and its outline`, `Filter while typing` and `Sidebar with the outline of a library page` (`documentation-outline-tree`);
  - `Home page` (`home-feature-tour-examples`, `migrate-docs-to-starlight`);
  - `Rebot console options` (`migrate-docs-to-starlight`).

  Otherwise archiving them would bring the long text back.
- **Open changes.** The long ADDED and MODIFIED requirements of the open changes are shortened in their own planning artifacts, so that every open change passes `openspec validate <change> --strict` and leaves no long requirement behind when it is archived. Where one open change modifies a requirement another open change adds, both are split alike.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

Requirements are shortened and split in these specs, with no change in behavior:

- `deprecation-diagnostics`
- `documentation-cli`
- `documentation-site`
- `documentation-viewer-sidebar`
- `intellij-syntax-highlighting`
- `keyword-documentation-rendering`
- `library-documentation-extraction`
- `library-documentation-markdown`
- `library-imports`
- `repl-input-errors`
- `repl-session-status`
- `repl-variable-listing`
- `robot-toml-option-coverage`
- `semantic-highlighting`
- `semantic-model-inspection`
- `semantic-model-sidecar-consumers`
- `test-metadata-selection`
- `test-metadata`
- `vscode-documentation-viewer`
- `vscode-markdown-robot-highlighting`

## Impact

- **Specs:** 20 main specs after archive; the planning artifacts of the open changes.
- **Code, tests, docs, users:** none.
