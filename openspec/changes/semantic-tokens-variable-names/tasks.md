# Tasks: semantic-tokens-variable-names

## 1. Decomposition

- [ ] 1.1 Give `build_variable_sub_tokens()` the site (declaration, keyword name, usage) and split type hints, patterns and extended names as design D2 describes. Verify with new cases in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/test_variable_tokenizer.py`:
  - `${count: int}` as declaration, keyword name and usage;
  - `${a: b: int}`, `@{items: int}` and `&{map: str=int}` as declarations;
  - `${n:\d+}` and `${n: int:\d+}` in a keyword name and as a usage;
  - `${OBJ.attr}` with and without a resolving full name;
  - all type-hint cases on Robot Framework 7.2 and 7.3 or later.

## 2. Analyzer

- [ ] 2.1 Pass the site to the decomposition at every call site of the analyzer, and pass whether the full name resolves (design D2). Verify with `dump-model`: `${x: int}` in a `Log` argument has no `VARIABLE_TYPE_HINT`, and `${x: int}=` has one with Robot Framework 7.3 or later.
- [ ] 2.2 Attach variable sub-tokens to declarations in `*** Variables ***` (design D3). Verify with model tests: `${SCALAR}`, `@{LIST}`, `&{DICT}`, `${X} =` and `${TYPED: int}` each contain a `VARIABLE_BASE` leaf for the name.
- [ ] 2.3 Attach variable sub-tokens to keyword-call assignments, including several targets, item assignments and the assignment mark. Verify with model tests for `${result}=`, `${a}    ${b}=`, `${DICT}[key]=`, `${DICT}[${k}]=` and `${r: int}=`.
- [ ] 2.4 Build `[Arguments]` declarations as `PARAMETER` tokens with variable sub-tokens. Verify with model tests for `${a}`, `${b}=default`, `${c}=${DEFAULT}`, `@{rest}`, `&{named}` and `${count: int}`.
- [ ] 2.5 Build the options of `EXCEPT` and `WHILE` as `OPTION` tokens with name, operator and value sub-tokens, like `VAR` options (design D7). Verify with model tests for `type=glob`, `limit=3` and `on_limit=pass`.
- [ ] 2.6 Run `tests/robotcode/robot/diagnostics/test_semantic_analyzer/test_analyzer_snapshot.py`. Review the diff: only the sub-tokens and token kinds from 2.1–2.5 may differ. Then reset the outputs with `hatch run test:test-reset <path>`.
- [ ] 2.7 Run the tests of the other model consumers (references, rename, hover, inlay hints, inline values). Check every difference against the risk in design.md before accepting it.

## 3. Model renderer

- [ ] 3.1 Remove `VARIABLE`, `VARIABLE_NOT_FOUND` and `VARIABLE_NAME` from `_ATOMIC_KINDS`, and render variable parts as design D4 describes:
  - `VARIABLE_BASE` with the type and modifiers of its enclosing token, so it is `parameter` inside `PARAMETER`;
  - `VARIABLE_TYPE_HINT` as `type`;
  - nothing for all other parts.

  Verify with unit tests in `tests/robotcode/language_server/robotframework/parts/test_semantic_tokens_unit.py`, covering every scenario of the spec `semantic-highlighting`.

## 4. Legacy path

- [ ] 4.1 Replace the whole-variable token at every variable site of the legacy path with the name and type-hint leaves of `build_variable_sub_tokens()`, called with the site from design D5. Embedded values keep the `embedded` modifier. Verify that the unit tests from 3.1 pass with the flag off as well.
- [ ] 4.2 Send `[Arguments]` declarations as one `parameter` token over the name, without the `operator` token for `=` (design D6). Verify with the scenario "Arguments with and without default values".
- [ ] 4.3 Send the options of `EXCEPT` and `WHILE` as one `controlFlow` token (design D7). Verify with the scenarios "WHILE options" and "EXCEPT option".
- [ ] 4.4 Run `tests/robotcode/language_server/robotframework/parts/test_semantic_tokens_flag_parity.py` on every Robot Framework version. Verify that every file passes, and that `_XFAIL_FILES` has no new entry.

## 5. Documentation

- [ ] 5.1 Update the semantic-token section of `dev-docs/semantic-model.md`: variables render their name and type hint instead of atomically, and the options of `EXCEPT` and `WHILE` render like `VAR` options. Verify that `grep -n "render atomically" dev-docs/semantic-model.md` no longer finds the variable family.

## 6. Verification

- [ ] 6.1 Run `tests/robotcode/language_server/robotframework/parts/test_semantic_tokens.py`. Review the diff against the list of expected changes in design.md (Risks), and look at every other difference. Then reset the outputs with `hatch run test:test-reset <path>`.
- [ ] 6.2 Run `hatch run test:test` and `hatch run lint:all`, and verify that both pass.
- [ ] 6.3 Check by hand, in the isolated VS Code harness and in IntelliJ (`runIde`), with a file covering the spec scenarios. Verify:
  - variable braces keep their grammar look after semantic tokens arrive, including the `*** Variables ***` line of #655 in IntelliJ;
  - the Python inside `${{ }}` keeps its grammar colours;
  - type hints and `[Arguments]` names show the colours of `type` and `parameter`;
  - embedded argument values in calls still get the embedded look on their name.
