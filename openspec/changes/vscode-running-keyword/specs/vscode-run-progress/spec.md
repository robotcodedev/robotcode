# Spec Delta

## Purpose

Defines how the VS Code extension shows the progress of a Robot Framework run in the editor: the highlighted lines of the keywords that are executing and the durations of the executed steps, and when it removes them.

## ADDED Requirements

### Requirement: Two settings, both off by default

The execution view in the editor SHALL be controlled by two settings, both off by default: `robotcode.run.highlightRunningKeyword` for the highlighted lines and `robotcode.run.showStepDurations` for the durations. While both are off, the extension SHALL NOT request keyword events from the debugger and SHALL show neither; while one of them is on, it SHALL request them. Runs started outside VS Code SHALL never show highlights or durations.

#### Scenario: Default

- **WHEN** a test is run from the Test Explorer with both settings at their default
- **THEN** the editor shows no highlighted lines and no durations, and the launch request carries no `keywordEvents`

#### Scenario: Only the durations on

- **WHEN** `robotcode.run.showStepDurations` is on, `robotcode.run.highlightRunningKeyword` is off, and a test is run from the Test Explorer or the editor, or debugged
- **THEN** the launch request carries `keywordEvents: true`, the editor shows durations as keywords end, and no line is highlighted

#### Scenario: Run in the terminal

- **WHEN** both settings are on and the user runs `robotcode robot` in the integrated terminal
- **THEN** the editor shows no highlights and no durations for that run

### Requirement: Running lines are highlighted

While `robotcode.run.highlightRunningKeyword` is on and a run or debug session started from VS Code executes, the extension SHALL highlight, in every visible editor of the file, the line of each test and keyword that has started and not ended, from the running test down to the innermost keyword, and SHALL remove each highlight when its item ends, the run ends or the setting is turned off.

#### Scenario: Nested keywords

- **WHEN** the test `Order Coffee` calls `Create Order`, which calls `Sleep    2s`, and the run is in the sleep
- **THEN** the line of `Order Coffee`, the line that calls `Create Order` in the test, and the line of `Sleep` in the resource file are highlighted in their editors
- **AND** when `Create Order` returns, only the line of `Order Coffee` stays highlighted until the test ends

#### Scenario: Editor opened during the run

- **WHEN** the user opens the resource file while `Sleep` runs
- **THEN** the editor shows the highlight of the `Sleep` line at once

#### Scenario: Run stopped

- **WHEN** the user stops the run while keywords are executing
- **THEN** all highlights disappear

#### Scenario: Highlight turned off

- **WHEN** the user turns `robotcode.run.highlightRunningKeyword` off during a run
- **THEN** the highlights disappear from all editors and no new ones appear while the run goes on

### Requirement: Durations are shown at the end of the line

While `robotcode.run.showStepDurations` is on, the extension SHALL show the elapsed time of each keyword that ends at the end of the line it was called from, in the editors of that file, in the format the Test Explorer uses for durations. A line executed several times in the same run SHALL show how often it ran and the total time.

#### Scenario: Single call

- **WHEN** `Sleep    1s` on line 12 of the resource file ends
- **THEN** line 12 shows a duration of about one second at its end

#### Scenario: Loop body

- **WHEN** a `FOR` loop runs `Log    ${item}` three times
- **THEN** the line of `Log` shows that it ran three times and the total of the three durations

### Requirement: Durations are cleared

Durations SHALL stay after the run ends and SHALL be removed from a file when a new run starts in the same workspace folder, when the document is edited, or when `robotcode.run.showStepDurations` is turned off.

#### Scenario: Next run

- **WHEN** a run has ended with durations shown and the user starts another run in the same workspace folder
- **THEN** the durations of the previous run disappear when the new run starts

#### Scenario: Edit

- **WHEN** the user edits the resource file after the run
- **THEN** the durations of that file disappear

#### Scenario: Durations turned off

- **WHEN** the user turns `robotcode.run.showStepDurations` off after a run
- **THEN** the durations disappear from all editors

### Requirement: The editor stays responsive

Updates of highlights and durations SHALL be batched; a run that produces thousands of keyword events per second SHALL NOT make the editor unresponsive, and the run SHALL NOT wait for the editor.

#### Scenario: Tight loop

- **WHEN** a test runs a `FOR` loop with ten thousand iterations of `No Operation` with both settings on
- **THEN** the editor stays usable during the run and the run takes no longer than it does with both settings off, apart from the time the debugger needs to send the events
