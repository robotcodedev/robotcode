# Working with large projects (tens of thousands of tests)

At scale, enumerating everything floods the terminal and the context window — and is almost never what the user actually wants. **Default to filtering or aggregating; only enumerate when explicitly asked, and even then on a narrowed scope.**

> **Note**: RobotCode auto-detects non-interactive use and disables paging/colors automatically — no extra flags needed.

## Contents

1. Filter at the source, not after the fact
2. Aggregate, don't enumerate
3. Stream to disk + use shell tools
4. Reach for JSON + `jq` for *projection*
5. `analyze code` on big repos
6. Handling huge result files

## 1. Filter at the source, not after the fact

Filter *before* the output is generated: the standard Robot Framework filters `-i` / `-e` / `-s` / `-t` are what bulk-narrow a huge run — combining a path argument with `-i <tag>` is usually enough to cut 100k tests down to a workable subset. (`-bl` / `-ebl` are RobotCode-added *exact-longname* selectors for when you already have a specific test's full name, not bulk filters.)

```bash
robotcode discover tests tests/acceptance/billing/ -i smoke -e wip
```

Don't pipe a huge enumeration through `grep` — that ingests it into your context first.

## 2. Aggregate, don't enumerate

If the user asks "how big is this project" / "what tags exist" / "is there a smoke suite", you don't need the test list. Reach for an aggregating `discover` command — **not** a `grep` over `.robot` sources. At scale the urge to scan files is strongest, but it is both slow and wrong: the effective tests/tags/suites are resolved at runtime (paths, config, profiles, variables, pre-run modifiers), and `discover` is the only thing that reflects that (see *Discovery* in [SKILL.md](../SKILL.md)).

```bash
# Counts only — last few lines of any discover command are a stats block
robotcode discover tests | tail -5
# Tag names only (the default; pass --tests to list the tests under each tag)
robotcode discover tags
# Suite-level inventory
robotcode discover suites
```

## 3. Stream to disk + use shell tools

Once an enumeration is too large to read inline, write it once and grep it many times — the data stays out of your context:

```bash
robotcode discover tests > /tmp/tests.txt
wc -l /tmp/tests.txt                          # count
grep -i 'billing'  /tmp/tests.txt | head -50  # sample matches
grep -c 'goto'     /tmp/tests.txt             # how many tests have "goto" in the longname
```

Read the file in slices (offset/limit), not the whole thing.

## 4. Reach for JSON + `jq` for *projection*

This is the one case where JSON beats text: pulling specific fields out of a huge tree without ingesting the rest.

```bash
# Just longnames, then count — never materializes the full payload in your context
robotcode --format json discover tests \
  | jq -r '..|.longname? // empty' | wc -l

# Tests grouped by source file
robotcode --format json discover tests \
  | jq -r '..|select(.type? == "test") | .source' | sort -u | head
```

## 5. `analyze code` on big repos

- Pass narrow `PATHS` or use `--filter '**/billing/**/*.robot'` instead of analyzing the whole tree
- Let the namespace cache warm on the first run — subsequent runs are much faster. If results look stale (after refactoring imports or upgrading libraries), `robotcode analyze cache clear`; to bypass the cache for one run, `--no-cache-namespaces`
- Inspect / manage the cache with `robotcode analyze cache info|list|path|clear`
- Use `--severity error` to focus on errors first (filter, don't `grep` — see [analyze.md](analyze.md)); leave warnings/infos for a follow-up pass. Add `--code <CODE>` to zoom in on one diagnostic type

## 6. Handling huge result files

Robot Framework's `output.xml` for 100k tests can be gigabytes. Don't load it whole — `robotcode results` is the right tool (full reference: [results.md](results.md)); combine it with bounded queries:

- `robotcode results summary --failed -i <tag>` — totals plus only failures in a narrow scope; never materializes all 100k tests in your context
- `robotcode results show --failed --top 50` — capped failure listing
- `robotcode results log -bl "<full longname>"` — drill into one specific test's tree rather than the whole report (exact-match, no glob ambiguity)
- Add `-o PATH` (file or directory) to any of the above when the file isn't in the auto-discovered location — typical for CI artefacts downloaded locally, runs from a colleague, or older runs you've archived
- Write JSON output (`--output results.json`, RF 7.0+) instead of XML — smaller file, faster parse, same `robotcode results` interface
- For truly gigantic XML and bounded-memory custom analysis, fall back to `xml.etree.ElementTree.iterparse(..., events=("end",))` with `el.clear()` after each `test` element

Regardless of which path: lead with the headline counts and offer to drill into a specific suite or tag — don't try to summarize 100k results in one response.
