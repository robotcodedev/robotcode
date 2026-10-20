# Spec Delta

## MODIFIED Requirements

### Requirement: Showing and refreshing a kept page

Showing a target SHALL show its kept page at once, if there is one; while RobotCode has not found the Python environment of the viewer's folder usable, that SHALL be the page that the history entry showed last. It SHALL generate the page again in the background once per session, and update the view when the result differs. The refresh button SHALL generate it again; when the environment is not usable, it SHALL first check the environment again. When a generation fails, the viewer SHALL show the error, above the kept page if there is one.

#### Scenario: Refresh button
- **WHEN** the user chooses the refresh button of a viewer that shows `Collections`
- **THEN** the page of `Collections` is generated again

#### Scenario: Restart before the environment is known
- **WHEN** a viewer showed `Collections`, VS Code is restarted, and the Python side selects the folder's environment only some seconds after the viewer is restored
- **THEN** the viewer shows the page of `Collections` at once and no error, and generates it again in that environment once RobotCode has checked it

#### Scenario: Refresh while the environment has a problem
- **WHEN** a viewer shows the error that the selected Python environment of its folder has no Robot Framework, Robot Framework has just been installed into that environment, and the user chooses the refresh button
- **THEN** RobotCode checks the environment again, and the viewer shows the page

### Requirement: Targets whose documentation cannot be generated

When the documentation of an entered target cannot be generated, the viewer SHALL show the error. If no page of that target was kept before, it SHALL also show a way to retry. The field SHALL keep the entered text, and back SHALL return to the previous page. A Python environment that cannot run Robot Framework, and a folder for which RobotCode is switched off, SHALL NOT count as such an error (requirement "A viewer says that it waits").

#### Scenario: Import arguments that fail
- **WHEN** a library `StrictLib` raises for the unknown mode `bogus`, no page of `StrictLib::bogus` was kept before, and the user enters `StrictLib::bogus`
- **THEN** the viewer shows the error and a way to retry, and the field keeps `StrictLib::bogus`

## ADDED Requirements

### Requirement: Generation waits for a usable Python environment

A viewer SHALL generate a page only when RobotCode's check finds the Python environment of its workspace folder usable, the check that the language server waits for too, and SHALL generate with the interpreter of that check. When the environment becomes usable, a viewer that waits for it SHALL load its page by itself.

#### Scenario: Robot Framework installed later
- **WHEN** a viewer waits because the selected Python environment of its folder has no Robot Framework, and the user installs Robot Framework into that environment in a terminal
- **THEN** within a few seconds the viewer shows its page, without any action in the viewer

#### Scenario: Interpreter selected later
- **WHEN** a viewer waits because no Python interpreter is selected for its folder, and the user selects an environment with Robot Framework
- **THEN** the viewer shows its page, generated with that environment

### Requirement: A viewer says that it waits

While the Python environment of a viewer's folder cannot run Robot Framework, the viewer SHALL say above the page it shows, if there is one, that it waits for that environment, with its progress bar running. When the problem has lasted 30 seconds, the viewer SHALL show it as an error that names the problem, without a way to retry. When RobotCode is switched off for the folder, the viewer SHALL show that as an error at once.

#### Scenario: Problem that solves itself at startup
- **WHEN** at startup RobotCode's first check finds the global interpreter without Robot Framework, and the Python side selects the folder's `.venv` with Robot Framework some seconds later
- **THEN** the viewer shows its progress bar and that it waits for the Python environment, and no error, and then its page, generated with `.venv`

#### Scenario: Problem that lasts
- **WHEN** a viewer waits for the environment of its folder, and that environment still has no Robot Framework 30 seconds after RobotCode found that
- **THEN** the viewer shows the error that the selected Python environment has no Robot Framework, with no way to retry
- **AND** it shows its page by itself once Robot Framework is installed into that environment

#### Scenario: Environment without Robot Framework
- **WHEN** the selected Python environment of the folder has had no Robot Framework for more than 30 seconds, and the user enters `Collections` in a viewer
- **THEN** the viewer shows the error that this environment has no Robot Framework at once, with no way to retry, and no generation runs

#### Scenario: Switched-off folder
- **WHEN** `robotcode.disableExtension` is `true` in the folder of a viewer, and the viewer shows `Collections`
- **THEN** the viewer shows the error that RobotCode is switched off for the folder, and shows the page once the setting is removed

### Requirement: A viewer follows the environment of its folder

When the Python environment of a viewer's workspace folder becomes usable with another interpreter than the one its page was generated with, the viewer SHALL load the page again, as it does when the page is shown: the kept page for that interpreter at once, if there is one, then a generation once per session.

#### Scenario: Another environment selected
- **WHEN** a viewer shows `Collections` generated with the folder's `.venv`, and the user selects another environment with Robot Framework for the folder
- **THEN** the viewer shows `Collections` generated with that environment, without any action in the viewer

#### Scenario: Wrong interpreter at startup
- **WHEN** at startup RobotCode's first check finds the global interpreter usable, a viewer shows `Collections` generated with it, and the Python side then selects the folder's `.venv`
- **THEN** the viewer shows `Collections` generated with `.venv`
