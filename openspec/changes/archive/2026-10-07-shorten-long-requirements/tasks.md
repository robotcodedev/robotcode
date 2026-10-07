# Tasks: shorten-long-requirements

## 1. Main specs

- [x] 1.1 Review the delta specs against design D1 and D2: every sentence that the assembly script reports as not verbatim keeps its meaning, and every new scenario claims only what its requirement says. Verify that the scenarios of each MODIFIED requirement are identical to the main spec, and that archiving the change in a copy of `openspec/` leaves only the five requirements of design D3 failing `openspec validate --specs --strict`.

## 2. Open changes

- [x] 2.1 Shorten the long ADDED requirements of the open changes in their own delta specs, as design D4 describes. Verify that each changed open change passes `openspec validate <change> --strict`.
- [x] 2.2 Shorten the 11 long MODIFIED requirements of the open changes in their delta specs, as design D3 and D4 describe, and split the four chains of design D4 alike in both changes. Verify with the length measurement of design D5, because `openspec validate` does not measure MODIFIED requirements.

## 3. Verification

- [x] 3.1 In a copy of `openspec/`, archive this change and then the open changes from 2.2 in their order. Verify that `openspec validate --specs --strict` passes for every main spec they touch, and that `openspec validate --changes --strict` passes for every open change.

## Workflow follow-up

- Archive the change after review.
