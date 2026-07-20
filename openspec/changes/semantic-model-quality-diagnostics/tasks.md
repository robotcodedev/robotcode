# Tasks: semantic-model-quality-diagnostics

## 1. Preparation

- [ ] 1.1 Confirm the SemanticModel is available as the analysis path — soft sequencing, no hard prerequisite; recommended after `semantic-model-switchover` (can also run flag-gated earlier)
- [ ] 1.2 Add the shared body-traversal helper over `DefinitionBlock.body` / statement subclasses (reused by workspace-refactorings); decide diagnostics-part vs. new extended-analysis module by reusing existing diagnostic-enable config
- [ ] 1.3 Create dedicated `.robot` fixtures for each check category

## 2. Extended dead-code diagnostics (one commit per check)

- [ ] 2.1 Unused loop variable / unused `EXCEPT AS` variable (definition in `local_variables`, no matching body reference via `find_variable`)
- [ ] 2.2 Empty control-flow block (`body` is only the closing `END`)
- [ ] 2.3 Unreachable code after `RETURN`/`BREAK`/`CONTINUE` within a block
- [ ] 2.4 Shadowed `VAR` (redefined before read)
- [ ] 2.5 Each check independently configurable (enable + severity), off unless enabled; conservative rules to avoid false positives on dynamic patterns

## 3. Complexity metrics

- [ ] 3.1 Cyclomatic complexity + nesting depth per `DefinitionBlock` using the design doc formulas
- [ ] 3.2 Surface as a code lens ("Complexity: N"); optional threshold diagnostic behind a setting

## 4. Enhanced argument validation

- [ ] 4.1 Too-many-positional / unknown named / missing required from `arguments_spec` vs. ARGUMENT / NAMED_ARGUMENT tokens
- [ ] 4.2 Gate on cases the analyzer does not already report; test the overlap to avoid double-reporting

## 5. Wrap-up

- [ ] 5.1 `hatch run test:test` green (all RF versions); `hatch run lint:all`
- [ ] 5.2 Update the Diagnostics/Linting entry in the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped checks; document the new diagnostics/lens and their settings
