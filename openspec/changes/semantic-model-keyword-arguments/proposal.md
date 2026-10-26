# Proposal: semantic-model-keyword-arguments

## Why

Inlay hints, signature help and the named-argument tokens each decide on their own which argument goes to which parameter, and they disagree with Robot Framework and with each other. For example, they treat the name of a positional-only parameter as named and count a list expansion as one argument. They also ignore where Robot Framework passes arguments to another keyword: template data rows, the inner keywords of Run Keyword variants and `Import Library`. After `semantic-model-cleanup` the semantic-model path is the only one, so these gaps can be closed there without double work.

## What Changes

- **One mapping of arguments to parameters**, following Robot Framework's own resolver of the installed version and used by inlay hints, signature help and the semantic tokens:
  - the name of a positional-only parameter does not make an argument named;
  - no argument of a keyword registered as a run keyword counts as named;
  - only a dictionary expansion `&{…}`, also with item access, makes the following arguments named; from a list expansion `@{…}` on, the positions are unknown;
  - a name written with variables counts with their values when these are known before the run.
- **Inlay hint labels**: a positional-only parameter shows its name without `=` (`⟨a⟩1`); of the arguments of a variable-length parameter only the first gets a hint, without `=` (`⟨*messages⟩a    b    c`). Reserved words before Robot Framework 7.0 get no hints.
- **Signature help after a name**: a tab after a keyword or import name counts like two spaces.
- **Template data rows** get the parameter hints, the signature help and the named-argument tokens of the template keyword. A template name that resolves only with the values of its first data row is rendered like a keyword.
- **Keywords that run keywords**: the inner calls get the hints and the signature of the inner keyword. Every keyword that runs keywords is rendered like the BuiltIn Run Keyword variants, also keyword-typed ones (Robot Framework 7.4 and newer) and registered ones. A keyword name taken from a variable, in a setup, teardown or inner call, gets a `variable` token.
- **`Import Library`** gets the parameter hints and the signature of the imported library's `__init__`, like a Library import.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `inlay-hints`: hint labels, named arguments, reserved words and Run Keyword variants change; list expansions, template data rows and `Import Library` are added.
- `signature-help`: the start after a name, named arguments, positional slots, Run Keyword variants, Library imports and where signature help is offered change; template data rows and `Import Library` are added.
- `semantic-highlighting`: keywords in settings, named arguments and Run Keyword variants change.

## Impact

- **Prerequisite (hard gate)**: `semantic-model-cleanup` is archived, and with it `semantic-model-feature-tests`, which creates `inlay-hints` and `signature-help` and the rules test modules this change extends. Until then the specs this change modifies exist only in that change, so `openspec archive` would refuse the deltas.
- **Code**: the semantic analyzer (a shared argument mapping, template data rows, `Import Library`, keyword names from variables), `inlay_hint.py`, `signature_help.py` and the model renderer in `semantic_tokens.py`.
- **Cache**: the model gains the init documentation of `Import Library` calls; a new RobotCode version empties the namespace cache as for every release.
- **Tests**: the rules modules of `semantic-model-feature-tests` (`test_inlay_hint_rules.py`, `test_signature_help_rules.py`, `test_semantic_tokens_rules.py`) get the new and changed scenarios, and the mapping gets unit tests.
- **Docs**: none; the user guides describe inlay hints and signature help in general terms.
- **Related changes**: `semantic-model-tokens-and-code-actions` and `semantic-model-token-rendering` also change `semantic-highlighting`, in other requirements. `variables-import-signature` changes the parameters of `Variables` imports, which the mapping then reads like any other.
- Not breaking.
