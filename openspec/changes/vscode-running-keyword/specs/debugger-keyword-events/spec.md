# Spec Delta

## Purpose

Defines the opt-in events with which the RobotCode debugger tells its client, such as the VS Code extension, when each keyword and control structure of a run starts and ends, what these events carry and what they leave out.

## ADDED Requirements

### Requirement: Keyword events only on request

The debugger SHALL send keyword start and end events only when `robotcode debug` runs with `--keyword-events`, or the launch request of the launcher carries `keywordEvents: true`. Without the option the client SHALL receive only the suite and test events it receives today.

#### Scenario: Default run

- **WHEN** a run is started without the option
- **THEN** the client receives `robotStarted` and `robotEnded` events for suites and tests only

#### Scenario: Run with the option

- **WHEN** a run is started with `--keyword-events` and a test calls `Log    hello`
- **THEN** the client receives a `robotStarted` and a `robotEnded` event of type `keyword` for the call, between the events of the test

#### Scenario: Launch attribute

- **WHEN** a client sends a launch request with `keywordEvents: true`
- **THEN** the launcher starts `robotcode debug` with `--keyword-events`

### Requirement: What a keyword event carries

Each keyword start event SHALL carry the item's type as Robot Framework reports it (keyword, setup, teardown or a control structure such as a loop or an iteration), its name, the source file and the line it was called from; each end event SHALL additionally carry the status and the elapsed time in milliseconds. The start and the end of the same execution SHALL carry the same id, and a nested execution of the same line SHALL get an id of its own.

#### Scenario: Keyword call

- **WHEN** a keyword in `shop.resource` calls `Sleep    1s` on line 12
- **THEN** the start event names `Sleep`, type `keyword`, the resource file and line 12, and the end event carries status `PASS` and an elapsed time of about 1000 milliseconds with the same id

#### Scenario: Loop

- **WHEN** a test runs a `FOR` loop with three iterations over `Log    ${item}`
- **THEN** the client receives events for the loop, for each iteration, which share the loop's line, and for each `Log` call

#### Scenario: Recursion

- **WHEN** a keyword calls itself before its first execution has ended
- **THEN** the inner execution's events carry a different id from the outer one

### Requirement: Keyword events are not synchronized

Keyword events SHALL be sent without the synchronization that suite and test events use, so the run never waits for the client to process a keyword event.

#### Scenario: No sync

- **WHEN** the client receives a keyword event
- **THEN** its body has `synced` set to false and the run goes on without a `robot/sync` request from the client

### Requirement: Keywords run for the client are not reported

Keywords that the debugger executes on the client's behalf, such as an expression evaluated in the Debug Console while the run is paused, SHALL NOT produce keyword events.

#### Scenario: Evaluate at a stop

- **WHEN** the run is paused and the client evaluates `Log    hi`
- **THEN** the client receives no keyword events for that `Log`, and the events of the paused keyword are unchanged
