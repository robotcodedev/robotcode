# Spec Delta

## REMOVED Requirements

### Requirement: Runs with a WSL interpreter are not supported yet

**Reason**: Run and Debug work with WSL interpreters now; the requirement "Runs inside the WSL distribution" of `intellij-run-configurations` describes them.
**Migration**: None. Runs with a WSL interpreter start inside the interpreter's distribution instead of ending with the "not supported yet" error.
