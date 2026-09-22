---
name: create-release-notes
description: "Use when creating RobotCode docs/news what's-new posts, release announcements, or user-facing news in the form of Markdown posts under docs/news/ from commits since the last version. Produces only a human-friendly Markdown news post, using existing non-April-Fools posts as templates and hatch run build:cz bump --get-next for the next version."
argument-hint: "[optional release date or focus area]"
---

# Create Release Notes

Create a new RobotCode news post from the commits since the last released version.

The output is only a polished, user-facing Markdown post in `docs/news/`.

## When to Use

- The user asks for RobotCode release notes, news, a release announcement, or a "What's New" post.
- The user wants commits since the previous version summarized for RobotCode users.
- The requested output is a new Markdown post under `docs/news/`.

## Scope

This skill only creates the news post.

Do not perform these actions:

- Do not run a docs build or preview, including `npm --prefix docs run build`.
- Do not create, update, or regenerate `CHANGELOG.md`.
- Do not edit version files.
- Do not edit `docs/news/index.md` or `docs/news/posts.data.ts`.
- Do not commit, tag, or push changes.

The rest of the release workflow is automatic or handled by the user.

## Inputs and Sources

Use these sources every time:

1. Existing release posts in `docs/news/*.md` as writing and structure templates.
2. Exclude April Fools posts from style and factual examples, especially `docs/news/2026-04-01-whats-new-v2.5.0.md` and any post marked with `aprilFools` frontmatter.
3. The next version from:

    ```bash
    hatch run build:cz bump --get-next
    ```

4. The latest stable release tag, normally in `vX.Y.Z` form.
5. Relevant commits from the latest stable release tag to `HEAD`.

The VitePress content loader already discovers new `docs/news/*.md` posts.

## Procedure

1. Check the current state.
    - Inspect `git status --short -- docs/news` before editing.
    - Preserve unrelated user changes.

2. Determine release metadata.
    - Run `hatch run build:cz bump --get-next` and treat the output as the next version number.
    - Normalize it to `vX.Y.Z` for titles, headings, links, and filenames.
    - Determine the newest stable release tag. Prefer an exact stable tag such as `v2.5.1`; ignore prerelease tags like `alpha`, `beta`, or `dev` unless the user asks for prerelease notes.
    - Use today's date unless the user supplied a release date.

3. Collect commits since the last version.
    - Start with an ordered log from the last stable tag to `HEAD`.
    - Include commit subjects, bodies, issue references, changed files, and any nearby docs or tests that explain user impact.
    - To decide whether a commit mentions a GitHub issue, inspect both the subject and body with `git log --format='%H%n%s%n%b'` or `git show --format=medium <hash>`.
    - Count explicit issue references such as `Closes #123`, `Fixes #123`, `Resolves #123`, `Refs #123`, `GH-123`, or `https://github.com/robotcodedev/robotcode/issues/123`.
    - Do not assume a trailing squash-merge reference like `(#123)` is an issue; it may be the pull request number. Use it as an issue link only when the commit body or inspected context confirms it refers to an issue.
    - Inspect important commits with `git show --stat` or targeted file reads instead of relying only on commit subjects.

4. Classify the changes by user impact.
    - Prioritize `feat`, `fix`, `perf`, and breaking changes.
    - In a `Bug Fixes` section, list only bug fixes that have a linked GitHub issue. Fold issue-less fixes into topical sections only when they are important user-visible context; otherwise omit them.
    - Include documentation or test commits only when they describe user-visible behavior, examples, confidence, or migration notes.
    - Group related commits into coherent release-note sections.
    - Omit purely internal churn, dependency updates, and mechanical cleanup unless the user should know about them.

5. Draft the post.
    - Create `docs/news/YYYY-MM-DD-whats-new-vX.Y.Z.md`.
    - If that file already exists, read it and ask before overwriting or merging.
    - Use this frontmatter shape:

      ```markdown
      ---
      title: What's New in vX.Y.Z
      date: YYYY-MM-DD
      ---
      ```

    - Use this heading shape:

      ```markdown
      # What's New in RobotCode vX.Y.Z
      ```

    - Write in English.
    - Use a short opening paragraph that frames the release around the most important user benefit.
    - For minor releases, prefer a small set of substantial sections plus optional `Bug Fixes` and `Under the Hood` sections.
    - For patch releases, keep it concise and focus on the fixes.
    - Include `Breaking Changes` when needed.
    - Link issues as `([#123](https://github.com/robotcodedev/robotcode/issues/123))` when known.
    - Use `**RobotCode**` for the product name in prose, matching existing posts.
    - Include code blocks only for user-facing commands or configuration that users can actually run.

6. End with the standard footer.

    ```markdown
    ---

    ## Thank You

    Thanks to everyone who reported issues, contributed ideas, and tested pre-release builds. Your feedback drives every release.

    For the full list of changes, see the [Changelog](https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md).

    - [Report issues](https://github.com/robotcodedev/robotcode/issues)
    - [Discussions & Q&A](https://github.com/robotcodedev/robotcode/discussions)
    - [Sponsor RobotCode](https://opencollective.com/robotcode)
    ```

7. Validate only the generated news file.
    - Check that the filename, frontmatter title, H1, and version all match.
    - Check that every described feature or fix is supported by commits or inspected code.
    - Run `git diff --check -- docs/news/YYYY-MM-DD-whats-new-vX.Y.Z.md`.
    - Review the diff for accidental edits outside the new news post.

8. Report back.
    - Mention the created news file path, next version, last tag used, and validation performed.
    - State clearly that no docs build, changelog update, commit, tag, or push was performed.

## Decision Points

- If `hatch run build:cz bump --get-next` fails or returns no version, stop and report the blocker.
- If there are no relevant commits since the last stable tag, do not create a news post without user confirmation.
- If the commit range contains many unrelated internal commits, summarize by user-visible outcome rather than listing everything.
- If a change is ambiguous, inspect the code and tests first; ask the user only when the impact still cannot be determined.
- If the release includes breaking changes, put them in a dedicated section near the top.

## Quality Criteria

- The post is factual, specific, and grounded in the commit range.
- The writing is polished and helpful for RobotCode users, not only maintainers.
- The post follows the real `docs/news` style and avoids the April Fools tone entirely.
- The post explains why the changes matter, not just what files changed.
- If a `Bug Fixes` section exists, every listed fix links to a GitHub issue.
- The final Markdown is valid VitePress-compatible Markdown with YAML frontmatter.
- Exactly one new `docs/news/*.md` post is created unless the user asks otherwise.
- No docs build, changelog update, version edit, commit, tag, or push is performed.

## Example Prompts

- "Create release notes for the next RobotCode version."
- "Generate a docs/news post from commits since the last release."
- "Write the What's New article for the upcoming release, focusing on runner changes."
