# Proposal: variables-import-signature

## Why

Robot Framework passes the arguments of a `Variables` import to `get_variables` (or `getVariables`) of the variable file. RobotCode reads the signature of that function into an initializer. Signature help, the named-argument completion and the parameter inlay hints of the import come from it. From Robot Framework 7.0 on, `get_variables_doc` builds no initializer: both branches are `TODO`s ([library_doc.py:3363](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py), [library_doc.py:3414](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)). A `get_variables(env)` has the initializer `env` on RF 6.1 and none on RF 7.5 (observed). Since RF 7.0, a `Variables` import therefore has no signature help and no `env=` items, although RF 7.0 and later accept named arguments for variable files and convert their types.

Before RF 7.0, the initializer does not match what Robot Framework does either:
- RobotCode offers `env=` items, but RF 5.0 and 6.1 call `get_variables(*args)`, so `env=prod` arrives as the string `env=prod` (observed on RF 6.1).
- A file without `get_variables` gets an initializer built from `__init__`, an empty one in the cases observed. Robot Framework passes such a file no arguments: it creates a variable file class without arguments (`instantiate_with_args=()` in RF 5.0, 6.1 and 7.5), and RF 7.5 rejects arguments for it with "Static variable files do not accept arguments."

## What Changes

- The initializer of a variable file comes from its `get_variables` or `getVariables` on every supported Robot Framework version. RobotCode reads it the way Robot Framework 7.0 and later read it to resolve the import arguments. Signature help, named-argument completion and parameter inlay hints of `Variables` imports work again on RF 7.0 and later.
- From RF 7.0 on, the parameters accept names and positions and carry their types, as RF 7.0+ resolves `env=prod` by name and converts `port=8` for `port: int` to `8` (observed on RF 7.0 and 7.5).
- Before RF 7.0, the parameters are positional only and carry no types. Signature help shows them, but no `name=` items are offered.
- The named-argument completion offers no `name=` items for positional-only parameters. Today it offers them, also for keywords such as `def show(a, /, b="x")`, although Robot Framework passes `a=1` to `a` as the value `a=1` (observed on RF 5.0 and 7.5). The point above depends on this.
- A variable file without `get_variables` or `getVariables` has no initializer on any version. That covers a static module, a class (also one whose `__init__` takes parameters), and YAML and JSON files.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `library-documentation-extraction`: what RobotCode extracts as the initializer of a variable file, the same on every supported Robot Framework version and matching how Robot Framework passes the import arguments.
- `keyword-documentation-rendering`: named-argument completion items exist only for parameters that accept a name.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: the initializer in `get_variables_doc`. One implementation replaces the RF < 7.0 handlers (`VarHandler`, `InitVarHandler`) and the two RF 7.0 `TODO`s.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`: the named-argument items leave out positional-only parameters ([completion.py:2604](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)).
- Otherwise no code change is needed in the consumers: signature help (legacy path [signature_help.py:778](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/signature_help.py), and the model path through `init_keyword_doc`), the argument completion of `Variables` imports ([completion.py:2185](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)) and the inlay hints ([inlay_hint.py:164](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/inlay_hint.py)) already use the initializer.
- Tests:
  - a new test module for the initializer per Robot Framework version;
  - signature help and argument completion of a `Variables` import, with the RF ≥ 7.0 skip in `test_signature_help_documentation_links.py` removed;
  - regression outputs that contain `Variables` imports may change and are reviewed.
- Related, planned separately as `variables-completion-details`: the completion details of variable files.
