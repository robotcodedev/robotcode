## MODIFIED Requirements

### Requirement: The run terminal is the run's input and output

On every platform that VS Code runs on, the run SHALL have the terminal as its standard input and output, as in a shell: Robot Framework's console colors and progress line SHALL work, and every Ctrl+C in the terminal SHALL reach the run and not close the terminal.

#### Scenario: Console of the run is a terminal

- **WHEN** a test in the run checks whether its standard output is a terminal
- **THEN** it is

#### Scenario: Ctrl+C during a run

- **WHEN** the user presses Ctrl+C in the run terminal while a test runs
- **THEN** Robot Framework stops the run as on Ctrl+C in a shell, and the terminal stays open with the run's output

#### Scenario: Run on Windows

- **WHEN** a test runs in a run terminal on Windows
- **THEN** the terminal shows the line before the run and the run's output, and the run's standard input and output are a terminal

#### Scenario: Ctrl+C a second time

- **WHEN** Robot Framework is stopping a run after a first Ctrl+C, for example in a teardown, and the user presses Ctrl+C again
- **THEN** Robot Framework ends the run at once, as in a shell, and the terminal stays open with the run's output
