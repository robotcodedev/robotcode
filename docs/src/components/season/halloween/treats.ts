// The tips that clicked creatures leave as treats. Every tip must be true for the RobotCode release the site
// documents: check each one against reference/cli.md and the robot.toml reference before it goes in.
export const TIPS = [
  "`robotcode discover tests` lists every test of your project without running it.",
  "`robotcode results summary --failed` shows the counts of a finished run and the tests that failed.",
  "`robotcode analyze code` checks the whole project for missing keywords and variables, ready for CI.",
  "`robotcode repl` runs Robot Framework keywords one at a time, right in your terminal.",
  '`robotcode doc keyword BuiltIn "Should Be*"` shows keyword documentation in the terminal.',
  "`robotcode -p ci robot` runs your tests with the `ci` profile from `robot.toml`.",
  "Profiles whose names start with `_` stay out of the profile lists.",
  "A profile can build on other profiles with `inherits` in `robot.toml`.",
];
