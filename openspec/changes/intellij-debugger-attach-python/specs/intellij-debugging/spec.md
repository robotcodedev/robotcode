# Spec Delta

## ADDED Requirements

### Requirement: Debugging the Python code of libraries
When a Robot Framework run configuration is started with Debug and its effective "Attach Python" is on, the plugin SHALL run the robot process under PyCharm's own Python debugger, with the configuration's interpreter, interpreter options, working directory and environment, so that Python breakpoints in the code of libraries and keywords stop the run. This SHALL work in every setting of PyCharm's Python debugger mode and SHALL need nothing installed in the interpreter.

#### Scenario: Python breakpoint in a library keyword
- **WHEN** "Attach Python" is on, a Python line breakpoint is set in a library keyword that a test calls, and the test is started with Debug
- **THEN** the run stops at the Python breakpoint, and PyCharm's Python debugger shows the Python frames and variables of the stop

#### Scenario: Robot Framework and Python breakpoints in one run
- **WHEN** "Attach Python" is on, a Robot Framework line breakpoint is set on the call of a library keyword and a Python line breakpoint in that keyword, and the test is started with Debug
- **THEN** the run stops first at the Robot Framework breakpoint and, after Resume, at the Python breakpoint, and after another Resume the run ends and the test passes

#### Scenario: Either Python debugger mode
- **WHEN** PyCharm's Python debugger mode is set to "debugpy" or to "pydevd" and a test with a Python breakpoint in a library keyword is started with Debug and "Attach Python" on
- **THEN** the run stops at the Python breakpoint in both modes

#### Scenario: Breakpoint in the initialization of a library
- **WHEN** "Attach Python" is on and a Python line breakpoint is set in the `__init__` of a library class that a suite imports
- **THEN** the run stops at that breakpoint when Robot Framework imports the library

#### Scenario: Attach Python off
- **WHEN** "Attach Python" is off and a test with a Python breakpoint in a library keyword is started with Debug
- **THEN** only the Robot Framework debug session starts, and the run does not stop at the Python breakpoint

### Requirement: Python exception breakpoints in runs with Python debugging
In a Debug run with "Attach Python" on, PyCharm's Python exception breakpoints SHALL stop at Python exceptions in the code of libraries and keywords as they do in PyCharm's own Python debug sessions.

#### Scenario: Exception raised in a library keyword
- **WHEN** "Attach Python" is on, a Python exception breakpoint for `ValueError` that suspends on raise is enabled, and a test calls a library keyword that raises `ValueError`
- **THEN** the run stops at the line that raises the exception, and PyCharm's Python debugger shows the exception

### Requirement: Two debug sessions for a run with Python debugging
A Debug run with "Attach Python" on SHALL show two sessions in the Debug tool window: the Robot Framework session in a tab named after the run configuration, with the test tree, the output and every tab it has without the option, and a session of PyCharm's Python debugger in a tab named "Python <name of the run configuration>", with PyCharm's Python debug console. Robot Framework breakpoints SHALL stop in the first session, Python breakpoints in the second.

#### Scenario: Tabs of the run
- **WHEN** the run configuration "Orders" with "Attach Python" on is started with Debug
- **THEN** the Debug tool window shows a tab "Orders" with the test tree, the output, "Terminal", "Debug Console" and "Robot Debug Console", and no Python debug console, and a tab "Python Orders" with PyCharm's Python debugger and its Python debug console

#### Scenario: Python prompt at a Python stop
- **WHEN** the run is paused at a Python breakpoint in a library keyword with the parameter `price` and the user enters `price` at the prompt of the Python debug console in the tab "Python Orders"
- **THEN** the console shows the value of `price` in the paused frame

#### Scenario: The tab of a stop comes to the front
- **WHEN** the run stops at a Python breakpoint while the tab "Orders" is shown
- **THEN** the tab "Python Orders" comes to the front and shows the frames and variables of the stop

### Requirement: The sessions of a run with Python debugging end together
The Python session of a Debug run with "Attach Python" on SHALL be in effect before Robot Framework imports the first library, and SHALL end when the run ends, together with the Robot Framework session.

#### Scenario: Run ends
- **WHEN** a Debug run with "Attach Python" on runs to its end
- **THEN** both sessions show as terminated

#### Scenario: Process ends unexpectedly
- **WHEN** the robot process of a Debug run with "Attach Python" on ends while the run is in progress, for example because it is killed outside the IDE
- **THEN** both sessions end

### Requirement: Stop ends a run with Python debugging gracefully
Stop in either session of a Debug run with "Attach Python" on SHALL end the run gracefully, as Stop ends a Robot Framework run without the option: the running test fails, the remaining tests are not run, teardowns run, and the output files are written. This SHALL also hold while the run is paused at a Python breakpoint, and both sessions SHALL end.

#### Scenario: Stop in the Python session while paused in Python code
- **WHEN** the run is paused at a Python breakpoint and the user presses Stop once in the tab of the Python session
- **THEN** the run ends without a further Stop, the stopped test fails, `output.xml`, `log.html` and `report.html` are written, and both sessions show as terminated

#### Scenario: Stop in the Robot Framework session while paused in Python code
- **WHEN** the run is paused at a Python breakpoint and the user presses Stop once in the tab of the Robot Framework session
- **THEN** the run ends without a further Stop, the stopped test fails, the output files are written, and both sessions show as terminated

#### Scenario: Stop at a Robot Framework breakpoint
- **WHEN** the run is paused at a Robot Framework breakpoint and the user presses Stop once in either tab
- **THEN** the run ends gracefully as without "Attach Python", and both sessions show as terminated

### Requirement: Rerun of a run with Python debugging
Rerun from either tab of a Debug run with "Attach Python" SHALL end the run gracefully if it still runs and start it again with both sessions, shown in the same two tabs.

#### Scenario: Rerun from the Python tab
- **WHEN** the run has ended and the user reruns it from the tab "Python Orders"
- **THEN** a new run starts with a Robot Framework session in the tab "Orders" and a Python session in the tab "Python Orders", and no further tabs open

#### Scenario: Rerun while paused in Python code
- **WHEN** the run is paused at a Python breakpoint and the user reruns it from the tab "Orders"
- **THEN** the paused run ends gracefully and the new run starts with both sessions
