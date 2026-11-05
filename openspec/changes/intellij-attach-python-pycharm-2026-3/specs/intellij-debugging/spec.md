## ADDED Requirements

### Requirement: Python debugging in every supported PyCharm version

Debug with "Attach Python" SHALL behave the same in every PyCharm version in the plugin's range, also in versions whose Python debug runner starts runs differently from the minimum version. The plugin SHALL not override API of PyCharm's Python debug runner that a version in its range declares final.

#### Scenario: Both sessions in PyCharm 2026.3

- **WHEN** in PyCharm 2026.3 "Attach Python" is on, a Robot Framework line breakpoint is set on the call of a library keyword and a Python line breakpoint in that keyword, and the test is started with Debug
- **THEN** the run stops at the Robot Framework breakpoint in the tab "Orders" and, after Resume, at the Python breakpoint in the tab "Python Orders", and after another Resume the run ends and the test passes

#### Scenario: Rerun from the Python tab in PyCharm 2026.3

- **WHEN** in PyCharm 2026.3 the run with "Attach Python" has ended and the user reruns it from the tab "Python Orders"
- **THEN** a new run starts with a Robot Framework session in the tab "Orders" and a Python session in the tab "Python Orders", and no further tabs open

#### Scenario: Plugin verification of the released versions

- **WHEN** `verifyPlugin` checks the plugin against the released PyCharm versions from `pluginSinceBuild` to `pluginUntilBuild`
- **THEN** it reports no compatibility problem for any of them
