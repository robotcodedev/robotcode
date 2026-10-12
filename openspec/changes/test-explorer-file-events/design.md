# Design

## Context

See proposal.md for the motivation. The current state in `vscode-client/extension/testcontrollermanager.ts`:

- **One watcher:** `createFileSystemWatcher("**/*.{<fileExtensions>}")` passes create, change and delete events to `refreshUri`.
- **`refreshUri(uri)`:** ignores other schemes, existing files without a known extension and files open in an editor (their editor content counts, via `refreshDocument`). An existing path with a test item gets `refresh(item)`. Everything else, including every deleted path, gets a discovery of its workspace folder, debounced per folder (`refreshWorkspaceChangeTimer`, `DEBOUNCE_MS` = 1 s).
- **Discovery result:** `robotTestItems` holds the discovery result of each workspace folder. It is the source of truth for the tree; per-file discoveries keep it current, and `robotItemIndex` indexes it by id. Every item carries `uri` for VS Code (navigation and the mapping to documents), `source`, the path Robot Framework reports, and `relSource`, that path relative to the workspace folder with `/`, because discovery runs there (`cwd: folder.uri.fsPath` in `pythonmanger.ts`). A folder suite's `source` is the folder: `robotcode discover all` reports the suite "Broken" of `tests/broken/` with that folder.
- **`testItemByUri`:** maps the URIs of the container items in the VS Code tree to these items, to find the suite of a document. It is derived, holds only what the tree shows, and cannot tell the workspace item from the root suite, which share the folder's URI (#624, comment at `findWorkspaceRobotItem`).
- **Extensions:** `languageClientsManager.fileExtensions` is `robot` and `resource` plus what other extensions contribute through `contributes.robotCode.fileExtensions`. The planned change `markdown-suites` adds `robot.md` and `robot.rst` there.
- **VS Code's folding, measured in the isolated harness (three times each):** `rm -rf` and `workspace.fs.delete` of a folder give one delete event for the folder. A folder created together with its files, moved in or copied in gives one create event for the folder. Files created some time after their folder, files deleted one by one, and files written through `workspace.fs` give one event per file.

## Goals / Non-Goals

**Goals:**

- Folder events and deletions of suite files of any extension reach the existing refresh path.
- Events of unrelated paths start nothing.

**Non-Goals:**

- The known sync problems: the per-file discovery without `-N`, stale snapshots of parent items, and that `refreshItem` rediscovers a file only when it is open, so a change made outside VS Code to a closed file does not update the tree.
- New files with an extension that is not in `fileExtensions`; the next discovery finds them, as today.
- The language server's watched files (`documents.py` also registers `**/*.{robot,resource}`) and IntelliJ's file handling; neither is checked for folder operations.

## Decisions

### D1: One watcher for `**` replaces the extension watcher

The Test Explorer watches `**` with create, change and delete events, and drops the watcher for `**/*.{<fileExtensions>}`.

VS Code reports a folded folder event only to watchers whose pattern matches the folder's path, and the API documentation recommends watching `**` for this. A string pattern uses the watching that VS Code does for the workspace folders anyway; it starts no further recursive watcher, and `files.watcherExclude` applies to it like to every workspace watcher.

Alternatives:

- **A second `**` watcher next to the old one:** two places that decide the same thing; one watcher with one classification is simpler.
- **A pattern listing the suite folders known from the last discovery:** has to be rebuilt after every discovery, needs glob characters in folder names escaped, and cannot see new folders. Rejected by the maintainer.
- **`workspace.onDidDeleteFiles`, `onDidCreateFiles`, `onDidRenameFiles`:** report only operations made in VS Code (Explorer, `applyEdit`), not those of a terminal, `git`, an agent or `workspace.fs`.

### D2: Classification in the handler, cheapest test first

1. **The path ends with an extension from `fileExtensions`** (lower-case comparison, like `refreshUri` does today): `refreshUri(uri)` for create, change and delete. Robot Framework files behave exactly as before.
2. **Delete of another path:** `refreshUri(uri)` only when a suite in the discovery result of the workspace folder has the deleted path as its `relSource`, or lies below it. The deleted path is made relative to the workspace folder with `/`; on Windows and macOS the comparison ignores case, as VS Code's own glob matching does there. This catches a folder suite, a suite file of another extension, and a folder above the test paths that is no suite itself, such as `src` with `paths = ["src/tests"]`. Relative paths keep URI encoding and the casing of Windows drive letters out of the comparison; `testItemByUri` is not used for it, see Context.
3. **Create of another path:** a `stat`; when it is a directory that contains a file with an extension from `fileExtensions`, `refreshUri(uri)`.
4. **Change of another path:** ignored. A folder's change event carries nothing the file events do not, and a changed suite file of another extension belongs to the known sync problems.

### D3: Directories checked by a walk

Whether a created directory contains a Robot Framework file is checked by walking it asynchronously with Node's `fs`. The walk stops at the first file with an extension from `fileExtensions`, does not follow symbolic links, and skips the paths that `files.watcherExclude` excludes, so it looks at what the watcher would report.

`workspace.findFiles` was rejected for this check: it runs the search service per call, and installing packages into a virtual environment inside the workspace creates hundreds of directories one after the other.

### D4: The existing debounce coalesces

Every match of D2 goes through `refreshUri`. For a deleted path and for a new directory without a test item, `refreshUri` schedules the debounced discovery of the workspace folder. So a branch switch or one `rm -rf` of several folders leads to one discovery after a second without further events, which the spec requires.

### D5: `fileExtensions` stays the only list of extensions

The handler adds no list of its own. Extensions that other extensions contribute, and those that `markdown-suites` adds, apply to the watcher without further changes.

### D6: The configuration watcher stays separate

The watcher in `languageclientsmanger.ts` for `pyproject.toml`, `robot.toml`, `.robot.toml`, `robocop.toml`, `.gitignore` and `.robotignore`, which restarts the language server of the folder, keeps its own string pattern. Merging it into the `**` watcher would save nothing at runtime, because VS Code serves both string patterns from the watching of the workspace folders, and it would couple the Test Explorer to the language client manager. Only the duplicate `robocop.toml` leaves its pattern.

Its other limits stay as they are, decided by the maintainer: configuration files outside the workspace folders, such as a project root above the folder or the user's `robot.toml`, are not reported, and a nested configuration file restarts the server. Robocop reads the configuration file closest to a source, so nested files can matter.

## Risks / Trade-offs

- [A discovery after a package install into a virtual environment inside the workspace, when its packages ship `.robot` or `.resource` files] → Happens today already through the file events of those files; at most one discovery per quiet second, as with any other change.
- [Path casing: on Windows and macOS a path in `robot.toml` can differ in case from the disk, so a suite's `relSource` and the deleted path differ in case] → On these platforms the comparison ignores case (D2).
- [A rename shows the suite under its new name only after the discovery] → The old entry disappears in the same discovery; there is no state with both names.

## Open Questions

- How the walk of D3 matches the patterns of `files.watcherExclude`: Node's `path.matchesGlob` needs no new dependency. Whether it is stable in the Node version of VS Code's extension host is checked before the implementation; otherwise a glob library is added at its newest version.
