# Spec Delta: keyword-documentation-rendering

## ADDED Requirements

### Requirement: Named-argument items only for parameters that accept a name

The named-argument completion SHALL offer a `name=` item only for a parameter that Robot Framework accepts by name: a positional-or-named or a named-only parameter. It SHALL NOT offer one for a positional-only parameter, because Robot Framework passes `name=value` to such a parameter as the value `name=value`. It SHALL NOT offer one for `*args` or `**kwargs`, as before. This applies to keywords, library imports and `Variables` imports alike.

#### Scenario: Keyword with a positional-only parameter
- **WHEN** a library keyword is defined as `def show(a, /, b="x")` and the named-argument completion is requested in the arguments of a call of `Show`
- **THEN** `b=` is offered and `a=` is not

#### Scenario: Variables import before Robot Framework 7
- **WHEN** `typedvars.py` defines `def get_variables(env="dev", port: int = 1)`, Robot Framework 6.1 is used, and the completion is requested in the arguments of `Variables    typedvars.py    `
- **THEN** no `env=` or `port=` items are offered
