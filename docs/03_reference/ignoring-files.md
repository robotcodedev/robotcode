# Excluding Files with `.robotignore`

When RobotCode looks at a project — discovering suites, running static analysis, or providing diagnostics and completion in the editor — it walks the source tree to find the `.robot` and `.resource` files it should care about. On a small project that is harmless, but real projects are rarely just Robot Framework. The same tree usually holds build output and dependencies (`dist/`, `build/`, `target/`, `node_modules/`, and the like), configuration folders, archived suites, vendored libraries, or the source of whatever application you are testing — none of which RobotCode needs to read. Walking and analysing them anyway costs time and memory for no benefit. A **`.robotignore`** file tells RobotCode which paths to skip.

By default RobotCode honours your `.gitignore`. But Robot Framework's own built-in exclusion (applied when it collects suites to run) only skips dotted, underscored, and `CVS/` names — far too little for a modern repository, where the directories that actually slow things down (`node_modules`, virtual environments, build output, large test-data folders) are none of those. A `.robotignore` fills that gap. Just as importantly, it lets you decide what RobotCode skips *independently* of what you keep out of version control — the two are rarely the same question, as explained [below](#robotignore-and-gitignore).

::: tip Works everywhere, no setup
`.robotignore` is honoured by the language server in the editor as well as by the `robotcode discover` and `robotcode analyze` commands — the same ignore rules are applied wherever RobotCode walks your files. There is nothing to install or enable — drop the file in and it takes effect.
:::

## Quick start

1. Create a file named `.robotignore` in your **project root** — the same directory you point Robot Framework at. This is where discovery and analysis begin, so a `.robotignore` here governs the whole project.

2. Add one pattern per line. The syntax is identical to `.gitignore`, so most of what you already know carries over:

   ```gitignore
   results/
   node_modules/
   **/generated/
   ```

3. Confirm the result. `robotcode discover files` prints exactly the set of files RobotCode loads *after* applying your ignore rules, so you can see at a glance whether a directory really dropped out:

   ```bash
   robotcode discover files
   ```

If a path you expected to disappear is still listed — or one you need has gone missing — tweak the pattern and run the command again. You are editing a plain text file, so there is no cache to clear: the next time you run the command, it walks with the new rules. (In the editor, saving a `.robotignore` reloads the language server automatically — see [Reloading](#reloading).)

## Syntax

`.robotignore` uses the exact same pattern language as `.gitignore`. If you have written a `.gitignore` before, there is nothing new to learn here:

```gitignore
# a comment starts with '#'

# match a directory anywhere in the tree (trailing slash = directories only)
results/
node_modules/
coverage/

# match by name at any depth (no slash)
*.bak
*.tmp

# anchor to this directory only (leading slash)
/legacy/

# match nested paths with '**'
**/generated/
tests/**/snapshots/

# exclude a folder's contents but keep one file
# (use '/*', not 'fixtures/' — '!' can't re-include inside a fully excluded folder)
fixtures/*
!fixtures/shared.resource
```

A few rules are worth keeping in mind. Patterns are matched relative to the directory the `.robotignore` lives in, not the current working directory. Order matters: a later rule overrides an earlier one, and a leading `!` re-includes a path that an earlier rule excluded. A trailing slash restricts a pattern to directories, and a leading slash anchors it to the file's own directory instead of matching at any depth. All of this is identical to Git.

### Pattern reference

| Pattern | Matches |
| --- | --- |
| `results/` | a directory named `results` anywhere in the tree, and everything inside it |
| `*.bak` | any file ending in `.bak`, at any depth |
| `/build/` | `build/` only in the same directory as the `.robotignore` |
| `**/generated/` | a `generated/` directory at any depth |
| `tests/**/data/` | a `data/` directory anywhere below `tests/` |
| `!keep.resource` | re-include a path excluded by an earlier rule |

::: warning You can't re-include inside a fully excluded folder
This is a standard Git behaviour, not a RobotCode quirk, but it trips everyone up at least once: once a whole directory is excluded (`legacy/`), a later `!legacy/common/` has no effect, because RobotCode never descends into an excluded directory in the first place — so there is nothing for the negation to re-include. Exclude the directory's *contents* instead, which leaves the directory itself walkable so the negation can apply:

```gitignore
legacy/*
!legacy/common/
```
:::

## What's ignored by default

Even with no `.robotignore` at all, RobotCode never walks into `.git/`, `.svn/`, `CVS/`, or any file or directory whose name starts with a dot — `.venv/`, `.cache/`, `.tox/`, and so on (on Windows, items with the hidden attribute or a leading `$` are skipped too). These are skipped in every context (discovery, analysis, and the editor), so listing them in a `.robotignore` is redundant and you can leave them out.

Underscore-prefixed names are a partial exception, and the distinction is worth understanding so you are not surprised. Robot Framework's own *suite collector* ignores names that begin with `.` or `_`, which is why a `_drafts/` folder never turns into a runnable suite. That rule, however, only applies when Robot Framework is collecting suites to **run**. RobotCode's static side — the language server, `robotcode analyze`, and `robotcode discover files` — still walks `_`-prefixed files and analyses them. This is deliberate: a `_keywords.resource` that other files import should absolutely get completion and diagnostics in the editor. The consequence is simply that if you want a `_`-named folder kept out of analysis *as well*, you do have to list it in `.robotignore` — the underscore convention alone won't hide it from the editor.

## `.robotignore` and `.gitignore`

RobotCode uses **one or the other — never both merged**:

- If a `.robotignore` is present at the project root, RobotCode uses `.robotignore` files throughout the project and **ignores every `.gitignore`**.
- If there is no `.robotignore` anywhere, RobotCode falls back to your `.gitignore` files.

The moment you add a `.robotignore`, you opt out of `.gitignore` for RobotCode entirely. That can feel surprising at first, but it is deliberate, and the reason is that the two files answer different questions. `.gitignore` describes what should not be committed to version control; that is rarely the same set as what RobotCode should skip. A build artifact may be git-ignored yet still worth nothing to analyse; a large folder of vendored test data may be committed on purpose yet pointless to walk. Trying to merge two rule sets with different intentions tends to produce confusing, hard-to-predict results. So once you reach for a `.robotignore`, RobotCode treats it as the single source of truth for "what RobotCode looks at" and leaves your Git configuration untouched — and unconsulted.

In practice this means a `.robotignore` is a small, self-contained file you can reason about on its own, without having to mentally diff it against everything in your `.gitignore`.

::: tip Define it at the project root
Discovery and analysis always start at the project root, so that is where a `.robotignore` belongs. Placed there, it puts the whole project into "`.robotignore` mode"; placed only deep in a subtree, it may never be reached if a `.gitignore` higher up has already taken over. When in doubt, keep one `.robotignore` at the root.
:::

## Nested `.robotignore` files

You are not limited to a single file. You can drop additional `.robotignore` files into subdirectories, and they cascade exactly like Git: a `.robotignore` applies to its own directory and everything beneath it, and a deeper file *adds to* the rules inherited from above. A deeper file can also re-include, with `!`, something a parent excluded — as long as the parent excluded its contents rather than the whole directory (see the warning above). Throughout this cascade you stay in `.robotignore` mode: `.gitignore` files are ignored at every level, not just at the root.

This is useful when a particular subtree needs extra exclusions that don't make sense for the rest of the project — for example a legacy area with its own generated junk:

```text
my-project/
├── .robotignore          # project-wide excludes
├── tests/
│   └── …
└── legacy/
    └── .robotignore      # extra excludes that only apply under legacy/
```

## A realistic example

To see how the pieces fit together, here is a `.robotignore` you might find at the root of a mixed project — a Robot Framework test suite living alongside a web front-end, some build tooling, and an archive of old suites:

```gitignore
# build output and dependencies
dist/
build/
target/
node_modules/

# Robot Framework run artifacts
results/
output.xml
log.html
report.html

# generated and vendored code
**/generated/
third_party/

# scratch files and backups
*.bak
**/tmp/

# a large archive of legacy suites we don't want analysed…
legacy/*
# …except for the shared resources the active suites still import
!legacy/common/
```

Read top to bottom, this keeps RobotCode focused on the suites and resources you actually work with: the front-end's dependencies and the project's build output are gone, run artifacts from previous executions don't get re-parsed, and the bulky legacy archive is excluded — except for the shared resource files the live suites still import, which the final `!legacy/common/` rule keeps visible.

## Where it applies

A `.robotignore` is honoured everywhere RobotCode walks the file system — the same ignore rules apply on the command line and in the editor alike:

- **Test and suite discovery** — [`robotcode discover`](./discovering-tests.md) and the editor's Test Explorer. Excluded directories don't appear in the discovered tree, which keeps both the CLI output and the Test Explorer focused on real suites.
- **Static code analysis** — [`robotcode analyze`](./analyzing-code.md). Excluded files are never analysed by `robotcode analyze`, so they produce no diagnostics in a lint run.
- **The language server** — diagnostics, completion, and namespace resolution in the editor. Excluded files are never loaded, so they don't contribute keywords or variables and don't slow the editor down.

## Verifying what's ignored

When a pattern doesn't behave the way you expect, don't guess — ask RobotCode. The quickest way to see what your rules actually do is [`robotcode discover files`](./discovering-tests.md#files-—-source-files-robot-would-parse), which lists every `.robot` and `.resource` file RobotCode would load *after* applying `.robotignore`:

```bash
# every file RobotCode currently considers
robotcode discover files

# narrow it down to one area while you tune patterns
robotcode discover files ./tests
```

If an excluded directory still appears in the list, your pattern isn't matching it — check the anchoring (`/foo` vs `foo`) and the trailing slash. If a file you need has vanished, an earlier rule is too broad, and you may need a `!` re-include to bring it back (remembering the fully-excluded-folder caveat above). Iterating against this command is far faster than restarting the editor to see what changed.

## Performance on large projects

This is where `.robotignore` earns its keep. For every `.robot` and `.resource` file it loads, the language server builds a namespace and resolves that file's imports — and on a large workspace that work, repeated across thousands of files, is often the dominant cost. One of the most effective things you can do about it is reduce how many files there are to analyse in the first place.

Excluding directories you never actually work in — generated code, vendored libraries, build output, or a large archive of legacy suites — removes them from analysis entirely: no namespace is built and no imports are resolved for them. On big projects this can reduce both analysis time and the language server's memory use, and because a `.robotignore` is trivial to add and easy to verify with `robotcode discover files`, it is usually the first thing to try — before reaching for finer-grained analysis settings such as `robotcode.analysis.diagnosticMode`, which controls whether diagnostics are reported only on the files you have open or across the whole workspace.

## Reloading

A `.robotignore` is read while RobotCode walks the workspace, so a change to it has to be applied project-wide. Editing a `.robotignore` (or a `.gitignore`) therefore restarts the language server, which re-walks the tree with the new rules and rebuilds its view of the project. You don't need to do anything beyond saving the file.

## See also

- [`robotcode discover files`](./discovering-tests.md#files-—-source-files-robot-would-parse) — verify exactly which files survive your ignore rules.
- [Analyzing Code](./analyzing-code.md) — the static analysis that honours `.robotignore`.
- [Diagnostics Modifiers](./diagnostics-modifiers.md) — suppress individual diagnostics instead of whole files, when excluding a file is too coarse a tool.
