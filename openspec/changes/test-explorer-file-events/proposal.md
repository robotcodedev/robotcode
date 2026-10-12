# Proposal

## Why

The Test Explorer in VS Code does not follow folders. It listens to `**/*.{robot,resource}`, and VS Code reports an operation on a whole folder as one event for the folder, without events for the files in it (`createFileSystemWatcher`: "file events from deleting a folder may not include events for the contained files"). A folder of suites that is deleted, renamed or moved away keeps its suites in the tree, and a folder of suites that appears at once, through `git checkout`, `cp -r`, `mv` or an agent, does not show up. Only **Refresh Tests** or another discovery of the workspace folder repairs the tree. Measured in the isolated VS Code harness, three times for each way.

## What Changes

- **Folders followed:** when a folder is deleted, renamed or moved away, the tree drops the suites in it, also when the folder lies above the test paths that `robot.toml` names. A folder with Robot Framework files that is created, copied or moved in shows its suites. This also holds when it happens outside VS Code, in a terminal, through `git` or by an agent. Many such operations at once lead to one discovery of the workspace folder.
- **Suite files by their place in the tree:** a file that the tree shows as a suite and that is deleted, renamed or moved away disappears from the tree whatever its extension, so this also holds for suites read by custom parsers (`parsers` and `extend-parsers` in `robot.toml`). A new file counts as a Robot Framework file by the extensions RobotCode already knows (`fileExtensions`), as today.
- **Other files stay quiet:** creating, changing or deleting other files, for example under `results/` or in the analysis cache, starts no discovery.
- **Docs:** the guide page Test Explorer says that the tree also follows folders, including changes made outside VS Code.

Not in this change: the known sync problems of the Test Explorer (the per-file discovery without `-N`, stale snapshots of parent items, and that a change made outside VS Code to a file that is not open does not rediscover it), and whether the language server misses folder operations the same way; it also registers `**/*.{robot,resource}`, which is not checked.

## Capabilities

### New Capabilities

- `vscode-test-explorer`: how the VS Code Test Explorer shows the discovered suites, tests and tasks and keeps them current with the files on disk.

### Modified Capabilities

None.

## Impact

- **VS Code extension:** `vscode-client/extension/testcontrollermanager.ts`. One file system watcher for `**` replaces the watcher for `**/*.{robot,resource}`. Its handler decides by the paths of the suites in the discovery result and by `languageClientsManager.fileExtensions`, and it reuses the debounced workspace discovery of `refreshUri`.
- **Configuration watcher:** `vscode-client/extension/languageclientsmanger.ts` keeps its own watcher for the configuration files that restart the language server; only the duplicate `robocop.toml` in its pattern goes (design, D6).
- **Tests:** the extension has no unit tests; a deterministic script in the isolated VS Code harness checks every way of creating, renaming, moving and deleting.
- **Docs:** `docs/src/content/docs/guides/vscode/test-explorer.mdx`.
- **IntelliJ:** not affected, it has its own file handling.
