# Tasks

## 1. Children and paging

- [ ] 1.1 Add a pure function that plans the children requests of a value or scope from the debugger's counts: named children once plus `indexed` pages of 100 for values with indexed children, no filter for values without them and for scopes. Verify with JUnit tests: a list of 3 items, a list of 300 items (named children, items 0–99, 200 remaining), a dictionary, a scope.
- [ ] 1.2 Use the plan in `RobotCodeNamedValue.computeChildren`, offering further pages through `tooManyChildren(remaining, Runnable)`; set `supportsVariablePaging = true` in the `initialize` request; remove the unused variables cache. Verify with harness check Q51 in task 4.2.
- [ ] 1.3 Let `RobotCodeStackFrame.computeChildren` show the Local variables inline and add the other scopes as groups that request their variables in `RobotCodeValueGroup.computeChildren`; show nothing and log nothing for a frame without scopes. Verify with harness checks Q51 and Q53.
- [ ] 1.4 Shorten type strings of the form `<class '…'>` to the part after the last dot. Verify with a JUnit test for `str`, `list`, `robot.utils.dotdict.DotDict` and a string in another form.

## 2. Set Value

- [ ] 2.1 Return a modifier from `RobotCodeNamedValue.getModifier()` only for direct children of the Local scope of the innermost frame; it sends `setVariable` with the scope reference, the name and the expression text, calls `valueModified()` on success and `errorOccurred` with the debugger's message otherwise, and offers the current value as the initial editor text. Verify with JUnit tests that the request is built from the scope reference, name and text, and that no modifier exists for a Suite or Global variable, an item of a list, or a Local variable of an outer frame; and with the Set Value harness checks.

## 3. Frames

- [ ] 3.1 Render the frame name followed by `file:line` in grey, render `subtle` frames in grey, pass the DAP column minus one to the source position, and create the frames once per suspend context. Verify with a JUnit test against a recording `ColoredTextContainer` for a frame with and without a source, and with the frame harness check.
- [ ] 3.2 Override `getEqualityObject()` with the frame name, the source path and the distance from the bottom of the stack. Verify with JUnit tests: the same frame in two stack responses with different lines is equal; two frames of one stack entry at different depths are not.

## 4. Verification

- [ ] 4.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 4.2 Check the behaviour in the headless PyCharm harness with `vars.robot`:
  - Q51: `@{items}` expands to `a`, `b` and `c` with the type `list`; a list with 300 items shows 100 items and an entry that loads the next 100; a dictionary expands into its entries;
  - Set Value of `${x}` to `'changed'` shows the new value and the following `Log    ${x}` logs `changed`; the bare word `changed` shows the debugger's error message; a Suite group variable offers no Set Value;
  - paused inside a user keyword, the frames show the keyword, test and suite names with file and line, and a directory suite is dimmed;
  - Q53: the Suite and Global groups and a nested dictionary stay expanded after Step Over in the same test;
  - `idea.log` gets no new SEVERE entries from RobotCode.
