# Tasks: test-explorer-file-events

All checks in VS Code run as a deterministic script in the isolated VS Code harness. The script reads the tree without expanding items, because expanding an item starts a discovery itself. It counts discoveries of a workspace folder by the `discover … all` command lines in the output channel RobotCode; the lines of a per-file discovery (`discover … tests -I …`) do not count.

## 1. One watcher for files and folders

- [ ] 1.1 In `vscode-client/extension/testcontrollermanager.ts`, replace the watcher for `**/*.{<fileExtensions>}` with one watcher for `**` and classify its events as D2 describes. Check created directories with the walk of D3, after settling its open question on matching `files.watcherExclude`, and send every match to `refreshUri` (D4). Verify that `npm run compile` and `npm run lint` pass.
- [ ] 1.2 Verify the requirement "Robot Framework files followed on disk" in the harness: a suite file created outside VS Code appears and a deleted one disappears. Also verify that an unsaved edit of an open suite file still updates the tree, as before.
- [ ] 1.3 Verify the requirements "Deleted folders leave the tree" and "New folders join the tree" in the harness, each way three times:
  - Deleted with `rm -rf`, with `workspace.fs.delete` and in VS Code's Explorer.
  - Renamed and moved away.
  - The parent folder of the test paths deleted, with `paths = ["src/tests"]` in `robot.toml` and `src` deleted.
  - Created together with its files, copied in with `cp -r` and moved in with `mv`.
  - Run the same script against a build of the previous state, where the folder cases fail.
- [ ] 1.4 Verify the requirement "Many folder changes lead to one discovery" in the harness: three suite folders deleted with one `rm -rf` lead to exactly one discovery of the workspace folder, and none of them remains in the tree.
- [ ] 1.5 In `docs/src/content/docs/guides/vscode/test-explorer.mdx`, extend the sentence on when the tree updates to folders that are created, copied, renamed, moved or deleted, also outside VS Code, for example through `git`. Verify that `npm run docs:build` has no link errors.

## 2. Suite files of other extensions

- [ ] 2.1 Verify the requirement "Deleted suite files leave the tree whatever their extension" in the harness. Use a minimal custom parser for `.custom` files that the demo project's `robot.toml` configures with `parsers`. The tree shows its suite; deleting the file outside VS Code removes the suite, and renaming it shows the suite under its new name only. If the tree does not show suites of a custom parser at all, stop and report, because the requirement assumes it does.

## 3. Unrelated paths

- [ ] 3.1 Verify the requirement "Other files start no discovery" in the harness. Each of these cases may start no discovery:
  - A test run writes into `results`.
  - A script writes files below the analysis cache.
  - A folder with only a text file is created.
  - A package without Robot Framework files is installed into a new virtual environment inside the workspace folder. Also check that the window stays responsive meanwhile.

## 4. Configuration watcher

- [ ] 4.1 Remove the duplicate `robocop.toml` from the pattern of the configuration watcher in `vscode-client/extension/languageclientsmanger.ts` and leave the watcher otherwise as it is (D6). Verify that `npm run compile` and `npm run lint` pass.

## 5. Integration

- [ ] 5.1 Run the whole harness script once more on the final build: every scenario of the spec `vscode-test-explorer`. Verify that `npm run compile` and `npm run lint` pass and that `openspec validate test-explorer-file-events --strict` reports the change as valid.
