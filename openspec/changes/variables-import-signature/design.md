# Design: variables-import-signature

## Context

See proposal.md for the problem. Verified facts:

- **Robot Framework**, from its sources and from running a suite with `Variables    typedvars.py    env=prod    port=8` (`get_variables(env="dev", port: int = 1)`) and a class-based `classget.py` with a `get_variables(self, env="dev")` method:

  | | RF 5.0, 6.1 | RF 7.0, 7.5 |
  |---|---|---|
  | call | `get_variables(*args)` (`robot/variables/filesetter.py`) | `PythonArgumentParser("variable file").parse(get_variables)` resolves the arguments |
  | `env=prod` | the string `env=prod` as the first argument (observed on 6.1) | `env` by name, `prod` (observed on 7.0 and 7.5) |
  | `port=8` for `port: int` | the string `port=8` | the integer `8` (observed) |
  | a file without `get_variables` given arguments | no such check in the source | 7.5: "Static variable files do not accept arguments." |
  | a variable file class | created without arguments (`instantiate_with_args=()`) | the same |

  YAML variable files accept no arguments on any of these versions, nor do JSON variable files, which RF supports from 6.1 on.
- **`PythonArgumentParser("variable file").parse(f)`** exists on RF 5.0, 6.1, 7.0 and 7.5 and returns the same `ArgumentSpec` for `typedvars.get_variables` and for the bound method `classget().get_variables` on all four (observed; `self` is not part of the bound method).
- **RobotCode.** `get_variables_doc` ([library_doc.py:3288](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)) builds the initializer only before RF 7.0:
  - from `get_variables` through a subclass of RF's `_PythonHandler` ([library_doc.py:3372](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py));
  - for files without it, from `getattr(libcode, "__init__")` through `_PythonInitHandler` ([library_doc.py:3418](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)).
  
  Both branches are `TODO`s from RF 7.0 on. Running `get_variables_doc` directly gives these initializers: on RF 6.1 an empty one for a static `vars.py` and for `classvars.py` (a class with `__init__(self, x="1")`), `env` for `needsarg.py` with `get_variables(env)`, none for a YAML file; on RF 7.5 none at all.
- **Consumers** of the initializer, unchanged by this change:
  - signature help: the legacy path [signature_help.py:778](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/signature_help.py), with the fallback without arguments at line 804, and the model path through `ImportStatement.init_keyword_doc`;
  - the argument completion of `Variables` imports ([completion.py:2185](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py));
  - the parameter inlay hints ([inlay_hint.py:164](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/inlay_hint.py)).

  The named-argument completion offers a `name=` item for every parameter except `*args`, `**kwargs` and the markers, positional-only parameters included ([completion.py:2604](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)). For a keyword `def show(a, /, b="x")`, RF 5.0 and 7.5 pass `Show    a=1` to `a` as the value `a=1` (observed).

  `test_variables_import_has_no_links` is skipped from RF 7.0 on, with the reason that variable files have no signature help there ([test_signature_help_documentation_links.py:195](../../../tests/robotcode/language_server/robotframework/parts/test_signature_help_documentation_links.py)).

## Goals / Non-Goals

**Goals:**
- `Variables` imports get signature help, named-argument completion and parameter inlay hints on every supported Robot Framework version, from `get_variables` or `getVariables`.
- What RobotCode offers matches what Robot Framework accepts on that version.

**Non-Goals:**
- Diagnostics for arguments that Robot Framework passes differently than they look, such as `name=value` before RF 7.0 or arguments for a static file (Open Questions).
- The completion details of variable files (`variables-completion-details`).
- Changes to the consumers of the initializer, apart from D5.

## Decisions

### D1: One way to read the signature, the way Robot Framework 7 does

`get_variables_doc` reads `get_variables`, or else `getVariables`, with `PythonArgumentParser("variable file").parse(...)` on every supported version. It builds the initializer `KeywordDoc` from the resulting `ArgumentSpec` with the converters the RF < 7.0 branch uses today (`ArgumentInfo.from_robot`, `ArgumentSpec.from_robot_argument_spec`), with the docstring of the function as its documentation, `is_initializer=True` and the name of the variable file. This replaces `VarHandler`, `InitVarHandler` and both `TODO`s.

Alternative considered: keep the `_PythonHandler` branch for RF < 7.0 and write a second branch for RF 7.0 and later. That is two ways to read one signature, and `_PythonHandler` does not exist in RF 7.

### D2: Argument kinds per Robot Framework version

From RF 7.0 on, the parameters are taken as parsed: positional-or-named, named-only, `*args`, `**kwargs`, with types. Before RF 7.0, Robot Framework calls `get_variables(*args)` with the arguments as they are:
- every positional-or-named parameter becomes positional-only;
- `*args` stays;
- named-only parameters and `**kwargs` are left out, because nothing can reach them;
- types are left out, because nothing converts the arguments.

To keep the `name=` items away before RF 7.0, the named-argument completion has to leave positional-only parameters out (D5). Signature help and inlay hints show the parameters.

### D3: No initializer without get_variables

A file without `get_variables` or `getVariables` gets no initializer: a static module, a class, YAML and JSON. Robot Framework passes such a file no arguments, and it creates a class without arguments, so `__init__` describes nothing the import can pass.

### D4: The function is read from the object the variables come from

For a class-based variable file, Robot Framework calls `get_variables` on an instance created without arguments. RobotCode reads the signature from the object it already uses to read the variables, so for a class it is the bound method, without `self`.

### D5: Named-argument items leave out positional-only parameters

The named-argument completion adds positional-only parameters to the kinds it leaves out ([completion.py:2604](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)). This is right for every caller, because Robot Framework passes `name=value` to a positional-only parameter as a value (Context). It covers keywords, library imports and `Variables` imports, and before RF 7.0 it removes the `name=` items of variable files (D2).

Alternative considered: a special case that offers no named items for `Variables` imports before RF 7.0. That keeps the wrong items for keywords with positional-only parameters.

### D6: Tests

- A new module `tests/robotcode/robot/diagnostics/test_variables_doc_initializer.py` writes `typedvars.py`, `classget.py`, `classvars.py`, a static `vars.py` and a `settings.yaml` to `tmp_path`, calls `get_variables_doc`, and asserts the initializer per `RF_VERSION`: names, kinds and types (D2), no `self` (D4), none for the files of D3.
- The language server tests:
  - the skip in `test_signature_help_documentation_links.py` is removed and the test checks the parameter;
  - a signature help test for `typedvars.py` runs on both analysis paths;
  - `test_completion_argument_docs.py` asserts `env=` and `port=` from RF 7.0 on and none before, and for a keyword `def show(a, /, b="x")` the item `b=` without `a=` (D5).
- Regression outputs that contain `Variables` imports may change, on RF 7.0 and later because the initializer comes back, and on earlier versions because the empty initializers go away. Each changed output is reviewed before the outputs are reset.

## Risks / Trade-offs

- [Signature help, inlay hints and argument completion of `Variables` imports change on every version] → intended. The regression outputs are reviewed one by one (D6).
- [Before RF 7.0, `name=` items for `Variables` imports go away] → they put `name=value` as a string into the first parameter, which is not what they suggest.
- [Keywords and library imports with positional-only parameters lose the `name=` items of those parameters] → Robot Framework passes `name=value` to them as a value, so the items were wrong (D5).
- [Reading the signature fails, for example on an annotation that cannot be evaluated] → the file gets no initializer, and its variables are not affected.

## Migration Plan

No data or setting changes. The disk cache stores the documentation of variable files, so cached entries keep their old initializer until the cache is renewed. The cache stores the RobotCode version and is emptied when it differs ([data_cache.py:377](../../../packages/robot/src/robotcode/robot/diagnostics/data_cache.py)), so a release renews it. Rollback is reverting the change.

## Open Questions

- Should RobotCode report a `name=value` argument of a `Variables` import before RF 7.0, which Robot Framework passes to the first parameter as a string?
- Should arguments for a variable file without `get_variables` be reported on Robot Framework versions before 7.5? RF 7.5 rejects them; RF 5.0 and 6.1 have no such check in their source.
