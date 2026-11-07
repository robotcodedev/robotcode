# Spec Delta

## MODIFIED Requirements

### Requirement: Values that depend on the order are computed per group

With groups, `robotcode results compare` SHALL compute every value that depends on the order of the runs within each group: the failed count, flaky tests and failing since in `--show tests`, the growth in `--show elapsed`, the first run in `--show failures`, and new and gone in `--show messages`. `--last N` SHALL keep the last N runs of each group. The status of a test SHALL have a space between groups.

#### Scenario: Fails only on one platform
- **WHEN** a test passed in all five `linux` runs and failed in four of the five `windows` runs
- **THEN** its status is `PPPPP FFPFF`
- **AND** its failed count is shown per group as `0/5, 4/5`

#### Scenario: Last runs per group
- **WHEN** `--group-by-metadata Platform --last 2` compares five runs per platform
- **THEN** the last two runs of each platform are compared
