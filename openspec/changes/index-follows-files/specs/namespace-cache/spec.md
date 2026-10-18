# Spec Delta

## ADDED Requirements

### Requirement: The cache keeps no entries of deleted files

The analysis cache SHALL NOT keep the entries of a Robot Framework file after the file was deleted. The language server SHALL remove them when it notices the deletion. `robotcode analyze code` SHALL remove, after its run, the entries of files that no longer exist, also of files outside the paths it analyzed, and SHALL keep the entries of files that still exist.

#### Scenario: File deleted while the language server runs

- **WHEN** a suite is deleted while the language server runs, and the server notices the deletion
- **THEN** `robotcode analyze cache list` lists no entry of that suite

#### Scenario: File deleted between two runs of the analyzer

- **WHEN** a suite is deleted after a run of `robotcode analyze code`, and `robotcode analyze code` runs again
- **THEN** after that run `robotcode analyze cache list` lists no entry of the deleted suite

#### Scenario: Analyzer run on some of the paths

- **WHEN** `robotcode analyze code` runs on `tests/area_a` only
- **THEN** the entries of existing files in `tests/area_b` stay in the cache

### Requirement: The cache keeps no analysis with failed imports

The analysis cache SHALL NOT store the analysis of a file with an import that failed, so that a file created after that analysis is found when the file is analyzed again.

#### Scenario: Resource file created between two sessions

- **WHEN** a suite imports `later.resource`, which does not exist yet, and `later.resource` is created before the language server starts again
- **THEN** after the restart the suite no longer reports the missing resource file
