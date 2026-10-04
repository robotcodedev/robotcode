# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach, checked on 2026-10-03 against the code on main, PyCharm 2026.1 (PY-261.22158.340, javap and decompiled classes from the Gradle cache) and LSP4IJ 0.21.0 (decompiled jar of the sandbox):

**Builds on planned changes.** `intellij-language-server-connection` and `intellij-environment-check` are planned, not implemented. This design relies on their planned designs:
- the connection: the provider builds its command line only in `start()`, listens on `127.0.0.1`, waits for the connection with a liveness check and a 60-second limit, gives the server two seconds after the exit notification before it ends the process, and forwards stdout from LSP4IJ's pipe to the log handlers;
- the environment check: a project service holds one state per interpreter, identified by kind, SDK name and home path; it classifies the SDK before it probes, with the WSL kind planned before the generic remote kind; one probe process runs a snippet that prints the Python and Robot Framework versions as one JSON line, with a 30-second limit; `buildRobotCodeCommandLine` reads the state and throws `CantRunException`; bundled paths come from the plugin descriptor; the run path waits for a missing result.
- The planned profile and extra-argument changes move the robotcode arguments into one pure function, which `buildRobotCodeCommandLine` prefixes with `<python> -u -X utf8 <bundled robotcode>`. This change replaces only that prefix.

**Plugin code on main:**
- Every robotcode process is a local `GeneralCommandLine(sdk.homePath, "-u", "-X", "utf8", <bundled robotcode>, …)` with the project folder as working directory (`RobotCodeHelpers.kt`, `buildRobotCodeCommandLine`). The check requires `sdk.homePath` to exist as a local regular file.
- `RobotCodeLanguageServer` starts `language-server --socket <port>` and reads the socket's streams.
- Discovery sends the open documents keyed by `VirtualFile.uri`, which is `Paths.get(file.path).toUri()` (`RobotCodeTestManager.kt`), and matches discovered items by scheme and path of their `uri` (`DataItems.kt`, `isSameUri`). Run markers build their state URL from the item's `source` path (`RobotCodeRunLineMarkerContributor.kt`).

**PyCharm 2026.1:**
- A WSL interpreter is a target-based SDK. Its additional data implements `TargetBasedSdkAdditionalData`, whose target configuration is a `WslTargetEnvironmentConfiguration` (type id `wsl`, which is also how PyCharm's own statistics recognize WSL interpreters), and `RemoteSdkPropertiesPaths`, whose `getInterpreterPath()` is the interpreter's path inside the distribution. `getDistribution()` returns a `WSLDistribution` for the stored id even when that distribution is no longer installed; `WslDistributionManager.getInstalledDistributions()` lists the installed ones (it runs `wsl.exe`, so it must not run on the EDT). None of these carries an `ApiStatus` annotation.
- `WSLDistribution` (no class-level annotation): `patchCommandLine(T, Project, WSLCommandLineOptions)`, `getWslPath(Path)`, `getWindowsPath(String)`, `getMntRoot()` and `getMsId()` are unannotated; `getUNCRootPath()` is `@Experimental`; the variant `patchCommandLine(T, Project, String, boolean)` is deprecated and `@Internal`. `WslPath.parseWindowsUncPath` keeps the prefix a path uses, `\\wsl.localhost\` or `\\wsl$\`; the platform's own default prefix is `\\wsl.localhost\` on Windows 11 and `\\wsl$\` before.
- `patchCommandLine` runs the command through the IDE's WSL agent (IJent) when it is available, and otherwise rewrites it to `wsl.exe --distribution <id> …`. The default options run the command in the user's login shell. With `setExecuteCommandInShell(false)`, both modes run the command directly (`--exec`, or a direct spawn) and take the working directory from the command line's directory: `wsl.exe` translates the Windows working directory, the agent converts it with `getWslPath`. In that mode the agent passes the `ProcessBuilder`'s environment to the process as it is.
- `WslTargetEnvironment` and its request are deprecated in favour of `EelTargetEnvironment` (`@Internal`); the configuration class is not.

**LSP4IJ 0.21.0:**
- `LSPClientFeatures` (`@Experimental`, already used by the plugin's factory) has `setFileUriSupport(FileUriSupport)`. Its built-in conversion maps a file below `\\wsl.localhost\<distro>\` or `\\wsl$\<distro>\` to a `file://wsl.localhost/<distro>/…` URI and back (`WslUriConverter`); it never produces paths of the distribution.
- Several code paths ignore a client's `FileUriSupport` and use the built-in conversion: `LSPIJUtils.applyWorkspaceEdit`, used for rename, for the edits of code actions and for `workspace/applyEdit`; the code-action request of intention actions (`LSPIntentionAction`); navigation links in tooltips; the reopen after a file rename. For an edit in `changes` form whose URI does not resolve, `applyWorkspaceEdit` creates the file.
- `initialize` carries `processId`, the IDE's own process id, set before LSP4IJ calls the client features' `initializeParams` hook. `rootPath` is the IDE's path; the server uses `rootUri`.
- For a stdio server, `OSProcessStreamConnectionProvider` decodes stdout with the command line's charset and writes it UTF-8 encoded into a pipe, which `getInputStream()` returns.

**Server:**
- Every file URI passes through `robotcode.core.uri.Uri`: incoming URIs as `Uri(uri).normalized()`, which converts to a path and back; outgoing ones from `Uri.from_path` (40 call sites in 13 files of the language server, the robot diagnostics, the analyzer and `discover`; `as_uri()` appears only in `uri.py` itself and in the results renderer of `robotcode results`). Rename and code actions answer with `documentChanges` that carry the document's own URI.
- `discover` writes item `uri`s with `Uri.from_path`, `source` as a plain path, and reads the open documents from stdin keyed by `Uri(k).normalized()`.
- The parent-process watcher starts only if `pid_exists(processId)` is true at `initialize`.
- In stdio mode the protocol goes to `sys.__stdout__.buffer`. Library and variable-file loading capture Python-level output (`_std_capture`); nothing else protects stdout. The read loop polls `peek(1)` and keeps polling at the end of input, so the process does not end when its input closes.
- Internal options are hidden global options of the root command (`--default-path`, `--launcher-script`). The bundled libraries are installed with `pip --implementation py`, so they are pure Python.

**The community fix (#433 report):** it converts in `uri.py`, switched on by environment variables: incoming UNC URIs to Linux paths when `WSL_DISTRO_NAME` or a JetBrains flag is set, incoming drive URIs to `/mnt/<drive>`, and `from_path` to UNC URIs when the flag is set. A Kotlin `FileUriSupport` maps the Linux URIs that still came back to WSL files. It also contains unrelated changes: a semantic model flag, nested variables, cache metadata and CLI aliases.

## Goals / Non-Goals

**Goals:**

- One mapping between the IDE's and the distribution's view of files, computed by the plugin and applied the same way by the plugin and the server.
- No change for local interpreters, VS Code and the command line.
- The WSL interpreter joins the planned environment state as one more kind: same results model, consumers and triggers.
- Only non-internal platform API.

**Non-Goals:**

- Run and Debug inside WSL; Docker, SSH and other targets.
- Copying robotcode into the distribution, or using a robotcode installed there.
- Translating absolute paths that users type into settings.
- Working around LSP4IJ's own WSL conversion beyond what the server's URIs can do.

## Decisions

### Recognizing a WSL interpreter

A small function returns, for an SDK, the WSL distribution and the interpreter path when the SDK's additional data is a `TargetBasedSdkAdditionalData` with a `WslTargetEnvironmentConfiguration` and implements `RemoteSdkPropertiesPaths`, and `null` otherwise. The environment state classifies this WSL kind before the generic remote kind. The interpreter's identity stays kind, SDK name and home path.

Alternatives:
- `PyTargetAwareAdditionalData` from the Python plugin: the same data, but a class of a PythonCore module, while the platform interfaces suffice.
- The type id `wsl` alone: it does not give the distribution.

### Starting processes inside the distribution

One function builds the WSL form of a command line for the interpreter and its arguments: `<interpreter path> <arguments>`, with the project folder's IDE path as working directory, no parent environment and UTF-8, handed to `WSLDistribution.patchCommandLine` with `setExecuteCommandInShell(false)`. The result is still a `GeneralCommandLine`, so LSP4IJ's provider and `CapturingProcessHandler` start it unchanged. `buildRobotCodeCommandLine` calls it, for the WSL kind, with `-u -X utf8 <bundled robotcode, distribution path> <mapping options> <robotcode arguments>`, so every robotcode process (language server, both discovery calls, and the profile list where it exists) gets the WSL form; the environment probe calls it with its snippet, because it runs before the state allows the builder. Process creation through the agent blocks; all callers already run on background threads.

- No shell: the default login shell reads the user's startup files, and anything they print would end up in the server's protocol stream.
- No parent environment: the agent passes the `ProcessBuilder`'s environment unchanged, so the IDE's Windows `PATH` and other variables would reach the Linux process.

Alternatives:
- PyCharm's target API (`TargetEnvironmentRequest`, `@Experimental`): an asynchronous environment preparation that yields a `Process`, which LSP4IJ's provider cannot take, for processes that need no upload and no port.
- A hand-built `wsl.exe` command: duplicates the platform and skips the agent.

### The bundled robotcode through the drive mount

The tool path inside the distribution is `distribution.getWslPath(<bundled robotcode>)`, by default `/mnt/c/…/robotcode4ij/data/bundled/tool/robotcode`. The probe tells whether the folder is visible inside the distribution, so a distribution without the Windows drive mount gets a clear result instead of a failing server.

Alternatives:
- Copying the tool into the distribution, per plugin version: faster imports, but a copy that must be versioned, refreshed and cleaned up, which nobody asked for. If the start over the mount proves too slow (task 4.3), a follow-up can add it.
- A robotcode installed in the WSL environment: the version would drift from the plugin's.

### Standard input and output for a server in WSL

For the WSL kind, the provider starts `language-server --stdio`, opens no `ServerSocket`, and lets LSP4IJ's base class provide the streams. It does not forward the stdout pipe to the log, because that pipe now carries the protocol. The socket path of local interpreters stays as the connection change plans it.

Alternatives:
- The server connects back to the plugin's socket: in WSL 2's default NAT mode, `127.0.0.1` inside the distribution is not the Windows loopback, and listening on the virtual network adapter would undo the loopback-only listener and needs a firewall rule.
- The server listens inside the distribution and the plugin connects through WSL's localhost forwarding: the port must be chosen up front without knowing whether it is free inside WSL, it depends on `localhostForwarding`, and any local process can connect first.

### A stdio mode that keeps stdout clean and ends with its input

In `jsonrpc2/server.py`, `start_stdio` writes the protocol to a duplicate of file descriptor 1 and points file descriptor 1 at stderr, so that `print`, native writes and child processes, such as the library-loading workers, end up on stderr, which LSP4IJ shows in the server's log. The read loop ends when a read returns no data, which on the blocking standard input means the end of input; the server then shuts down the way it does after the exit notification. Both apply to every stdio client.

Alternatives:
- Redirecting only `sys.stdout`: native writes and inherited descriptors of child processes still reach the protocol.
- Keeping the parent-process watch as the only end: the IDE's process id means nothing inside the distribution (next decision).

### No IDE process id for a server in WSL

The factory's client features override `initializeParams` and set `processId` to `null` when the server was started for the WSL kind. Otherwise the server's `pid_exists` check runs against an unrelated Linux process with the same number, and could end the server when that process ends.

### URIs are translated by the server, from a table the plugin passes

The plugin passes the mapping as one hidden global option per root, `--path-mapping <client URI root>=<local path root>`, to the language server and to `discover`. `robotcode.core.uri` keeps the table for the process:
- an incoming `file:` URI whose scheme, host and first path segment (drive letter or distribution) match a client root, ignoring case, becomes the local root plus the unquoted rest;
- `Uri.from_path` turns a path below a local root into the client root plus the quoted rest; the longest root wins;
- with an empty table, nothing changes.

The plugin builds the roots in exactly the form the IDE's own URIs have:
- the distribution as the project shows it, for example `file://wsl.localhost/Ubuntu/=/`;
- each Windows drive root that exists, for example `file:///C:/=/mnt/c/`, with the distribution's mount root.

The plugin installs no `FileUriSupport`.

Why the server, compared with the community fix:
- LSP4IJ applies rename and code-action edits and builds the intention requests with its built-in conversion, which bypasses a `FileUriSupport`. A mapping only in the plugin therefore breaks rename and quick fixes, or creates files for `changes` edits. The built-in conversion does understand `file://wsl.localhost/<distro>/…`, so a server that speaks the IDE's URIs works with every LSP4IJ code path, and a second mapping layer in the plugin could only disagree with it.
- The server already funnels every URI through `Uri`, so one mapping covers the language server and `discover`.
- An explicit table instead of environment heuristics: `WSL_DISTRO_NAME` is set in every WSL process, so the fix's conversion also runs where nobody asked for it, for example under VS Code Remote - WSL.
- Both directions for drive files: the fix sent `/mnt/c/…` back as `file://wsl.localhost/<distro>/mnt/c/…`, which the IDE opens as a second copy of the file.
- Exact client forms: `\\wsl$\` and `\\wsl.localhost\` are different roots in the IDE's file system, and `isSameUri` compares paths case-sensitively, so the server must write the drive letter and the prefix as the IDE does.
- The fix's unrelated changes are not part of this change.

Alternatives:
- Plugin only, with a `FileUriSupport`: incomplete, see above.
- Rewriting every message in the plugin's own stream: parsing and re-serializing every message, and guessing which strings are URIs.

### The plugin maps its own paths with the same table

A pure Kotlin mapper over strings holds the roots and converts paths in both directions with the same longest-root rule. It gives the tool path inside the distribution (for the builder) and the IDE path of each discovered item's `source`, which the run markers use for their state URL. The open documents that discovery receives keep their IDE URIs; the server translates them. Because the mapper does not call Windows-only API, its unit tests run on Linux.

### The environment check for the WSL kind

Before it runs the interpreter, the state service checks that the distribution is among the installed ones and that the project folder's IDE path converts to a path of that distribution (`getWslPath` returns `null` for an unreachable path and throws for a path of another distribution). Then it runs the planned probe snippet through the WSL command-line function, with the bundled folder's distribution path as an argument, and the snippet reports one more field: whether that folder exists. The results and their texts are those of the spec; time limit, logging and retry are the planned ones.

### Runs stay refused for the WSL kind

The run path refuses a WSL interpreter with `CantRunException` and the "not supported yet" text before it builds a command line, so the WSL form of the builder never starts a run. The planned run-configuration base refuses remote interpreters itself; whichever of the two run paths exists gets the refusal.

### The environment results as a modified requirement

The spec modifies the requirement "A separate result for each problem" as `intellij-environment-check` plans it, so that both are consistent after archiving. The block is copied from that plan as of 2026-10-03.

## Risks / Trade-offs

- [`LSPClientFeatures` is `@Experimental`] → The plugin already depends on it; the change adds one override. `verifyPlugin` against 261 and the newer configured versions reports changes.
- [PyCharm moves WSL interpreters to another configuration class, as the deprecation of `WslTargetEnvironment` in favour of an internal Eel environment suggests] → Recognition lives in one function with a test; an SDK it does not recognize falls back to the "remote, not supported yet" result, not to a broken server.
- [The agent and `wsl.exe` modes differ: the environment of a process started without shell, and the translation of the working directory in `wsl.exe` mode] → The manual check covers the environment (task 4.3) and the working directory through the markers; if the translation fails, the builder sets the platform's working-directory option with a non-login shell instead.
- [Slow start, because Python reads the bundled robotcode over the drive mount] → Measured in task 4.3; copying the tool is the fallback.
- [A cache location in the IDE's system directory is written over the drive mount] → It works through the drive root of the table; the "Project folder" location keeps the cache inside WSL.
- [LSP4IJ's built-in WSL conversion uses `URI.create`, which fails for paths with characters that must be encoded, such as spaces] → Outside RobotCode; task 4.3 checks a project path with a space, and the maintainer decides whether to report it to LSP4IJ.
- [A cold WSL start takes longer than the probe's 30 seconds] → The planned check reports a timeout and checks again on the next trigger; task 4.3 records the time after `wsl --shutdown`.
- [Absolute paths typed into settings, such as a Python path entry, reach the server unchanged] → In a WSL project they must be distribution paths or relative paths.
- [The copied requirement block drifts from `intellij-environment-check`] → Copy it again if that plan changes before this change is archived.
- [Long command lines, one mapping option per drive] → Only existing drive roots, usually a handful.

## Migration Plan

None. Nothing that is stored changes, and the server's new option is only passed by the plugin.

## Open Questions

- Can the maintainer's PyCharm be switched to `wsl.exe` launching for the manual check, for example through a registry key? If not, the check runs in the agent mode only; the approach stays the same.
