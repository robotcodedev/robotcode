# Spec Delta

## ADDED Requirements

### Requirement: ESLint runs in the code-quality checks

The code-quality checks of the CI SHALL run ESLint with the command that the pre-commit hook runs (`npm run lint`). An ESLint error SHALL fail the code-quality checks. The ESLint step SHALL also run when an earlier step of the code-quality checks has failed, so that one run reports the findings of all of them.

#### Scenario: An ESLint error in a pull request

- **WHEN** a pull request adds TypeScript code that breaks an ESLint rule, such as an unused variable or a formatting difference that Prettier reports
- **THEN** the code-quality checks fail, and the log of the ESLint step names the file, the line and the rule

#### Scenario: A Python style error and an ESLint error

- **WHEN** a pull request breaks both the Python style check and an ESLint rule
- **THEN** the code-quality checks fail, and the run reports both findings
