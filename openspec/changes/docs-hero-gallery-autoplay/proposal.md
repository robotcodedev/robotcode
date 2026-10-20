# Proposal

## Why

The gallery next to the title of the home page changes its picture only when a reader clicks, swipes or uses the arrow keys of the enlarged view, so most visitors see a single picture of the RobotCode artwork, and during a season a single poster. Moving on by itself shows more of them without asking anything of the reader.

## What Changes

- The gallery of the home page moves on to the next picture every eight seconds with a short fade, in and outside a season.
- It waits while the pointer or the keyboard focus is on it, while the enlarged view is open and while the tab is hidden; after a change by hand the new picture gets the full eight seconds.
- With reduced motion it does not move on by itself.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `documentation-site`: a new requirement for the gallery of the home page moving on by itself.

## Impact

- `docs/src/components/Hero.astro`: the gallery element and its styles.
- The pictures, the enlarged view and the season pictures stay as they are.
