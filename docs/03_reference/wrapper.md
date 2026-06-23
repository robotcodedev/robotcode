# Running Tests Through a Wrapper

You always run RobotCode the same way — `robotcode … run`, a `debug` session, the `repl` — and configure everything in `robot.toml`. The `wrapper` option doesn't change that: it tells RobotCode to run its actual command **through** a command of your choosing. The wrapper command goes first and the real `robotcode` command line is **appended** to it. That lets the wrapper prepare the **test environment** a run needs — start the services, servers, mocks or session the tests depend on, run the tests inside it, and tear it all down again — none of which is part of the tests themselves.

::: tip Only need environment variables?
Set them in `robot.toml` under `[env]` — they apply to every run, no wrapper required. Reach for a `wrapper` when something has to **run** around the tests, not just be exported.
:::

**Who this is for:**

- **Bring up the services a run depends on** — a database, a message broker, the application under test, a whole `docker compose` stack — and tear them down again when the run finishes.
- **Start mocks or stub servers** the tests talk to — a fake API, a WireMock instance, a local web server, …
- **Run UI tests inside a graphical session** — a virtual X server (`xvfb-run`) in CI, or a specific window manager / compositor.

## Quick start

```bash
# A ready-made tool, for a single run (the value is split like a shell command)
robotcode --wrapper "xvfb-run -a" run tests/

# Your own environment script, configured once in a profile
robotcode -p integration run tests/

# Ignore a configured wrapper for one run
robotcode -p integration --no-wrapper run tests/
```

The same `wrapper` applies whether you run from the command line or from an editor — the editor integrations run `robotcode` for you. It takes effect only for commands that **execute Robot Framework** — `run`, `robot`, `debug`, `repl`, `run-debug` and `repl-server`. Commands that don't run tests (the language server, `discover`, `libdoc`, …) are never wrapped.

## Configure it in `robot.toml`

```toml
# A ready-made tool — here a virtual X server for headless UI tests
[profiles.headless]
wrapper = ["xvfb-run", "-a"]

# Your own script — bring the test environment up, then tear it down again
[profiles.integration]
wrapper = ["./with-test-services.sh"]
```

```bash
robotcode -p integration run tests/
```

The profile's `env` is applied **before** the wrapper runs, so the wrapper can rely on it. Use `extend-wrapper` to append to an inherited `wrapper`. See the [`robot.toml` reference](config.md#wrapper).

## On the command line

`--wrapper` sets (or overrides) the wrapper for a single run; `--no-wrapper` disables a configured one:

```bash
robotcode --wrapper "xvfb-run -a" run tests/       # split like a shell command
robotcode -p integration --no-wrapper run tests/   # ignore the profile's wrapper
```

It can also be set via the `ROBOTCODE_WRAPPER` environment variable.

## In VS Code

As noted above, a `wrapper` in your selected profile already applies in the editor. If you want to **override** it for your editor alone — without touching `robot.toml` — set `robotcode.debug.launchWrapper`:

```json
"robotcode.debug.launchWrapper": ["./with-test-services.sh"]
```

This wraps tests you run or debug from the Test Explorer and takes precedence over the profile's `wrapper`. It is an **IDE-only override** — it has no effect on the command line.

## Writing your own wrapper script

A wrapper is just a command. RobotCode runs it with the arguments you configured first, and then appends the actual `robotcode` command line that has to run:

```
<your-wrapper>  [wrapper args you configured]   <robotcode command line, appended by RobotCode>
```

So inside the script, that appended command line is simply **`"$@"`** — the script sets up whatever the run needs, then executes `"$@"`. The environment is already prepared for you: the selected profile's `[env]` is set, and the working directory is the one you started `robotcode` from.

::: warning The wrapper contract
1. Run `"$@"` in the **foreground** and **propagate its exit code** — pass/fail, CI and the debugger depend on it.
2. Pass **stdin / stdout / stderr** through. Send your own diagnostics to **stderr** (`>&2`), never stdout — otherwise you corrupt the JSON-RPC protocol of `repl-server --stdio` and the debug launcher.
3. Do **not** detach or daemonize — it would break the debugpy `--tcp` attach and the interactive REPL.
4. **Tear down** whatever you start (use a `trap`, so it happens even on failure or Ctrl-C).
:::

The usual job is to **start something, run the tests, then stop it again** — a server, a mock, a database, a session. A `trap` guarantees teardown, `"$@"` runs in the foreground, and its exit code is forwarded:

```bash
#!/usr/bin/env bash
set -euo pipefail

log() { printf '%s\n' "$*" >&2; }   # diagnostics ALWAYS to stderr

service_pid=""
cleanup() {
    # stop whatever you started — kill a PID, `docker compose down`, …
    [ -n "$service_pid" ] && kill "$service_pid" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM           # runs on success, error and Ctrl-C

# --- bring the test environment up --------------------------------------
log "starting the test environment"
my-service &                         # a web server, a mock, docker compose, Xvfb, …
service_pid=$!
export SERVICE_URL="http://localhost:8080"   # hand the address to the tests

# wait until it is actually ready (poll, don't just sleep blindly)
for _ in $(seq 1 50); do
    is-ready && break
    kill -0 "$service_pid" 2>/dev/null || { log "service failed to start"; exit 1; }
    sleep 0.1
done

# --- run the appended robotcode command, forward its exit code ----------
set +e
"$@"
status=$?
set -e
exit "$status"                       # the trap tears the environment down
```

The same in PowerShell — configure it as `wrapper = ["pwsh", "-File", "./with-test-services.ps1"]`. The appended command arrives through a `ValueFromRemainingArguments` parameter, and `try`/`finally` replaces the `trap`:

```powershell
param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $Command)

$service = $null
try {
    [Console]::Error.WriteLine('starting the test environment')   # diagnostics to stderr
    $service = Start-Process my-service -PassThru                 # web server, mock, docker compose, …
    $env:SERVICE_URL = 'http://localhost:8080'                    # hand the address to the tests

    # wait until it is ready (poll, don't just sleep)
    for ($i = 0; $i -lt 50 -and -not (Test-Ready); $i++) {
        if ($service.HasExited) { throw 'service failed to start' }
        Start-Sleep -Milliseconds 100
    }

    & $Command[0] @($Command | Select-Object -Skip 1)             # run the appended robotcode command
    $code = $LASTEXITCODE
}
finally {
    if ($service -and -not $service.HasExited) { $service | Stop-Process -Force }
}
exit $code                                                        # forward the robotcode exit code
```

::: tip Simpler cases
- **Nothing to tear down?** If the wrapper only has to *enter* an environment that cleans up after itself (delegating to a tool like `xvfb-run` or `dbus-run-session`), skip the `trap` and just `exec "$@"` — the process is replaced, so stdio, signals and the exit code pass through on their own.
- **Only environment variables?** You don't need a wrapper at all — set them in `robot.toml` under `[env]`.
:::

::: tip Passing options to the wrapper
If the wrapper takes its own arguments, end the `wrapper` with `--` so the script can tell them apart from the command — RobotCode appends the `robotcode` command line right after it:

`wrapper = ["./with-test-services.sh", "--fast", "--"]`

In the script, consume your own options up to the `--`, `shift` past it, and whatever is left in `"$@"` is the `robotcode` command to run. (Or keep the script option-free and pass settings through the profile's `[env]`.)

A relative `wrapper` path is resolved against the directory you run `robotcode` from; use an absolute path otherwise.
:::
