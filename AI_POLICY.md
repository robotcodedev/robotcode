# AI and Automated Contribution Policy

AI tools and automated coding agents are welcome in RobotCode contributions — they can be genuinely useful development aids.

Whether a change was written, discovered, or produced by an autonomous agent does not matter. What matters is that a human then takes over, fully understands the change, and remains accountable for it — through review, testing, and any follow-up. Agent-assisted work followed by genuine human ownership is welcome.

This policy applies to AI-assisted or automated contributions and project interactions, including pull requests, issues, discussions, comments, code review replies, documentation changes, generated files, and any other content submitted to the RobotCode project.

This policy exists to protect the maintainers' time — time that would otherwise go into fixing real bugs and building new features, and that ultimately keeps RobotCode sustainable. It complements, and does not replace, the [Contribution Guide](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Human responsibility

The human submitter is responsible for everything they submit, regardless of which tools were used to create it.

Before submitting AI-assisted or automated content, you must ensure that:

- you fully understand the content and can explain it during review or discussion
- you have manually reviewed all AI-generated or tool-generated output
- code changes have been tested locally using the documented project workflow
- documentation or issue reports have been checked for accuracy and relevance
- the submission is focused and does not include unrelated refactoring, generated noise, or unnecessary boilerplate
- generated files are accompanied by the exact command or workflow used to regenerate them
- you are prepared to address maintainer feedback yourself

Do not submit code, tests, documentation, issue reports, comments, or review feedback that you do not understand.

## Disclosure

If AI tools or automated agents were used to create a pull request or other substantial contribution, disclose that in the contribution.

Place the disclosure where reviewers will see it: the pull request description, the issue body, or the comment itself. A short note is enough, for example:

> AI/tooling disclosure: This contribution was prepared with assistance from `<tool name>`. I reviewed the result manually, understand the changes, verified them locally, and confirm that I have the right to submit this contribution under the project license.

See [Licensing, provenance, and right to submit](#licensing-provenance-and-right-to-submit) for what this confirmation entails.

Optionally, a machine-readable trailer in commits is welcome, for example:

> `AI-Assisted-By: <tool name>`

For small grammar fixes, formatting help, or ordinary editor completions, disclosure is not required.

Disclosure does not replace review, testing, or responsibility for the contribution.

## Licensing, provenance, and right to submit

AI-assisted or automated contributions must be suitable for contribution under the RobotCode project license.

By submitting AI-assisted or automated content, you confirm that you have the right to submit the contribution under the project license and that your use of AI tools or automated agents does not impose terms that conflict with the project license.

See the [Legal Notice in CONTRIBUTING.md](CONTRIBUTING.md#legal-notice) for the project-wide right-to-submit statement and the recommended DCO sign-off.

Treat AI-generated or tool-generated output as untrusted input. Do not submit generated content if you cannot reasonably assess its origin, if it appears to contain copied third-party code, or if its licensing status is unclear or incompatible with this project.

If generated output includes or is based on pre-existing third-party material, disclose that material and its license or attribution where required.

AI tools and automated agents are not a substitute for a human contributor. The human submitter remains the contributor of record and must be able to explain the review, judgment, testing, and verification that make the contribution suitable for this project.

## Issues, discussions, comments, and pull request descriptions

AI may be used to help draft written communication, but the final message must be reviewed and edited by the human submitter.

Do not paste unreviewed AI-generated text into issues, discussions, pull request descriptions, review replies, or comments. Be concise and use your own understanding. Explain what changed, why it changed, how it was tested, or what problem you are reporting.

Reports, comments, or discussions that appear to be generated without real understanding, reproduction, or project context may be rejected, and maintainers may ask the contributor to resubmit with proper context.

## Pull requests and code changes

AI-assisted or automated pull requests must meet the same standards as any other contribution.

Before opening a pull request, make sure that:

- the change follows the [Contribution Guide](CONTRIBUTING.md)
- the documented test, lint, and code-generation workflows were used where applicable
- the change is focused on one issue or purpose
- generated files are explained and reproducible (for example, `docs/public/schemas/robot.toml.json` is regenerated via `scripts/create_robot_toml_json_schema.py`, and `docs/03_reference/cli.md` via `scripts/create_cmdline_doc.py` — never edit such generated files by hand)
- tests cover the relevant behavior, not only the narrow shape of the submitted patch, and no tests are written solely to make the diff pass
- the pull request does not shift validation, cleanup, integration, or design work onto maintainers

Small fixes are welcome when they are correct, focused, verified, and maintainable.

## Low-context automated submissions

Low-context, fully automated, shallow, or exploratory submissions may be rejected.

This includes, but is not limited to, submissions that:

- appear to be generated from a superficial scan of issues or code
- ignore the contribution guide
- do not include meaningful verification
- include broad unrelated changes or mechanical refactoring
- add unnecessary abstraction, boilerplate, comments, or tests
- misunderstand the project architecture or user-facing behavior
- require maintainers to do the necessary investigation, integration, or validation work

Automation is not a substitute for project understanding.

## Enforcement

Maintainers have final discretion when applying this policy.

Submissions that violate this policy may be rejected. Where reasonable, maintainers may instead request changes with a pointer to this policy before declining a contribution.

For pull requests, this may mean requesting changes, closing the pull request without review, or closing it without further review. For issues, discussions, comments, or other project interactions, this may mean declining the request, closing the issue, or asking the contributor to resubmit with proper context, verification, or disclosure.

If you believe a decision was made in error, you are welcome to follow up on the same pull request, issue, or discussion to clarify context. Respectful disagreement is fine; repeating the same low-context submission is not.

This policy is not intended to discourage responsible contributors. It is intended to keep RobotCode maintainable and to make clear that contributors are responsible for understanding, verifying, testing, and cleaning up automated output before submitting it.