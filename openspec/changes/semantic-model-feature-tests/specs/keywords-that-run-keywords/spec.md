# Spec: keywords-that-run-keywords

## Purpose

Some keywords run other keywords: an argument names the keyword to run, and the analysis looks it up like a keyword call. The rules say which arguments the analysis takes as keyword names. They hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: BuiltIn keywords that run no keyword

Robot Framework registers some BuiltIn keywords only so that it passes their arguments unresolved. The analysis SHALL treat them as keywords that run no keyword and SHALL NOT look up any of their arguments as a keyword. Among them are `Log Many`, `Comment`, `Create Dictionary`, `Set Variable If`, `Pass Execution If`, `Return From Keyword`, `Return From Keyword If`, the keywords that set, get or check variables by name, and `Import Library`, `Import Resource` and `Import Variables`.

#### Scenario: Log Many and Comment
- **WHEN** a test contains `Log Many    hello    world` and `Comment    some text`
- **THEN** the analysis reports no `KeywordNotFound` for them

#### Scenario: Variable name in escaped form
- **WHEN** a test contains `Set Test Variable    \${y}    2` and `Variable Should Not Exist    \${z}`
- **THEN** the analysis reports no `KeywordNotFound` for them

#### Scenario: Dictionary and conditional value
- **WHEN** a test contains `${d}=    Create Dictionary    a=1` and `${w}=    Set Variable If    ${TRUE}    a    b`
- **THEN** the analysis reports no `KeywordNotFound` for them

#### Scenario: Import at run time
- **WHEN** a test contains `Import Library    Collections`
- **THEN** the analysis reports no `KeywordNotFound` for it

#### Scenario: Keyword that runs a keyword
- **WHEN** a test contains `Run Keyword    Unknown Inner`
- **THEN** the analysis reports `KeywordNotFound` for `Unknown Inner`
