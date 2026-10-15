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
