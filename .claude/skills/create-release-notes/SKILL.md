---
name: create-release-notes
description: "Write or update RobotCode's user-facing release announcement: the \"What's New in vX.Y.Z\" news post under docs/news/, built from the commits since the last stable release. Use this whenever the user asks for release notes, a release announcement, a news post or a What's New article for RobotCode, or wants an existing draft post updated with newly committed changes, even if docs/news is not mentioned. Produces only the Markdown post; no changelog, build, version bump or commit."
argument-hint: "[optional release date or focus area]"
---

# Create Release Notes

Write the news post that announces the next RobotCode release, or update its draft when more commits land before the release.

The post is an announcement, not a changelog. `CHANGELOG.md` lists every change. The post picks what matters to users, says it in their terms and puts the most important things first. The documentation explains the details; the post links to it instead of repeating them. Most of the work is choosing, ordering and cutting, not summarizing every commit.

## Scope

This skill only writes the news post. Do not:

- run a docs build or preview, including `npm --prefix docs run build`;
- create, update or regenerate `CHANGELOG.md`;
- edit version files;
- edit `docs/news/index.md` or `docs/news/posts.data.ts`; the VitePress content loader finds new posts on its own;
- commit, tag or push.

The rest of the release workflow is automatic or handled by the user.

## Who Reads the Post

- Most readers use RobotCode in VS Code. After an update, the extension's "What's New?" notification opens https://robotcode.io/news/, so they read the post on the website.
- A smaller group uses the plugin for PyCharm and IntelliJ IDEA.
- Command-line tools such as `discover`, `results`, `robotcode doc` and the REPL are used by fewer, more experienced users.

Readers want to know three things: what will I notice, what can I do now, and do I have to do anything? The answers decide what goes into the post and in which order.

## Sources

- `references/writing-guide.md` for structure and tone. Use the existing posts in `docs/news/*.md` only for the format: frontmatter, file naming and footer. Posts before v2.8.0 predate the guide, so don't copy their openings (slogans, long feature paragraphs) or their technical explanations. Ignore April Fools posts: `docs/news/2026-04-01-whats-new-v2.5.0.md` and any post with `aprilFools` in its frontmatter.
- The next version: `hatch run build:cz bump --get-next`.
- The newest stable release tag in `vX.Y.Z` form. Ignore `alpha`, `beta` and `dev` tags unless the user asks for prerelease notes.
- The commits from that tag to `HEAD`, with subjects, bodies and changed files.
- For changes planned with OpenSpec, the archived `proposal.md` under `openspec/changes/archive/`. It says in prose what changes for users.
- The documentation changed in the range. It shows how a feature is documented and which pages and anchors to link.
- The "What is RobotCode?" section of `README.md`, for the one-sentence product description.

## Procedure

1. **Determine the release metadata.**
    - Run `hatch run build:cz bump --get-next` and normalize the result to `vX.Y.Z` for the filename, title and heading.
    - Find the newest stable tag, for example `v2.7.0`.
    - Date the post today unless the user gave a release date.

2. **Check the state.** Run `git status --short -- docs/news` and keep unrelated changes. An untracked or modified `docs/news/*-whats-new-v*.md` for a version newer than the last stable tag is the current draft. Its version can differ from the one in step 1, because a later commit can change the next version. If there is a draft and the user asks to update it, follow step 9 and then steps 10 and 11. If there is a draft and the request is unclear, ask before you overwrite or merge it.

3. **Collect the changes.**
    - Read the full log, not only the subjects: `git log --format='%h %s%n%b' <tag>..HEAD`.
    - Inspect important commits with `git show --stat` and targeted reads of code, tests and docs.
    - Count explicit issue references: `Fixes #123`, `Closes #123`, `Resolves #123`, `Refs #123`, `GH-123` and issue URLs. A trailing `(#123)` from a squash merge may be a pull request; use it only when the context confirms an issue.
    - Check every issue you plan to link with `gh issue view <number> --json state,title`. Check upstream issues and pull requests the same way before you say anything about when a fix arrives.

4. **Choose what goes in.**
    - Include what users notice or must act on: new features, fixes of released behavior, breaking changes, new minimum versions, required installation steps.
    - Check that users actually see a difference. A commit body says how the code changed, which is not always what users notice; see "Changes Users See" in the writing guide.
    - Leave out internal refactors, CI and tooling, work on the documentation site itself (build, theme, preview), OpenSpec planning, dependency bumps and synced vendored files. Also leave out fixes for features added after the last tag; those bugs never reached users. A correction of the documentation that closes an issue is a fix and goes into Bug Fixes.
    - Leave out cosmetic changes that don't change how anything works, such as new translations of section headers. A fix of visibly wrong output, such as empty lines when output is paged, is not cosmetic; it gets a line in Editor and CLI Polish. If you think a cosmetic change matters to users, ask.
    - Give a deprecation of a rarely used feature one sentence, last in its list, never a section of its own.
    - Mention each change once. A new minimum IDE version goes into Breaking Changes and not again in the chapter for that IDE.
    - If you are unsure whether something matters or whether it is breaking, ask (see Decision Points).

5. **Order everything by user impact.** At every level (chapters, subsections, list items), put first what most readers notice or must act on. A list never starts with its least important item. A typical chapter order:
    1. Breaking Changes, if there are any
    2. the headline chapters, such as support for a new Robot Framework version or a big editor feature
    3. other improvements that most editor users notice
    4. the chapter for PyCharm and IntelliJ IDEA
    5. Editor and CLI Polish, with one-line fixes
    6. command-line and REPL changes for power users
    7. Bug Fixes
    8. Under the Hood, for experimental features that users can opt into

6. **Write the chapters.** Read `references/writing-guide.md` before you draft or restructure a post. It explains how each part of the post works: the chapter patterns (breaking changes, support for a new Robot Framework version, editor chapters, polish lists, bug fixes), the wording, and how much space an item gets. It also contains openings that worked and openings the maintainer rejected.

7. **Write the opening last.** When the chapters stand, write the lede, the product sentence and the highlights list from them, as the writing guide describes. Writing them last keeps them consistent with the final order.

8. **End with the standard footer.**

    ```markdown
    ---

    ## Thank You

    Thanks to everyone who reported issues, contributed ideas, and tested pre-release builds. Your feedback drives every release.

    For the full list of changes, see the [Changelog](https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md).

    - [Report issues](https://github.com/robotcodedev/robotcode/issues)
    - [Discussions & Q&A](https://github.com/robotcodedev/robotcode/discussions)
    - [Sponsor RobotCode](https://opencollective.com/robotcode)
    ```

9. **Update an existing draft.** When the user says that new commits have landed:
    - Read `references/writing-guide.md` (Ordering, Chapter Patterns, Wording) before you add anything.
    - If the next version from step 1 differs from the draft's version, rename the file and update `title:` and the H1.
    - Find the commits the post does not cover yet. If the conversation names the commit where the previous pass stopped, start there. Otherwise read the whole range from the tag again and skip what the post already covers. Read the bodies too: `git log --format='%h %ad %s%n%b' --date=short <commit-or-tag>..HEAD`.
    - Check new issue links as in step 3. Add only what passes step 4, each item at its place in the existing order. Keep the existing structure unless the user asks to change it.
    - Update the lede and the highlights list if a new item belongs there.
    - If the post's `date:` is not today, rename the file to today's date and update `date:`, unless the user gave a release date.
    - Report what you added and what you left out, with a short reason for each omission.

10. **Validate the post, and only the post.**
    - The filename date, `date:`, `title:`, the H1 and the version match.
    - Every statement is backed by a commit, the code or the docs. Don't add a "because" that you cannot back.
    - Every linked issue exists. Bug Fixes lists only issues that the commit closes.
    - Every in-page link matches a heading, and every linked docs page and anchor exists (see Post Format).
    - Each list starts with its most important item, and nothing appears twice.
    - `git diff --check -- <post>` passes, and nothing outside the post changed.

11. **Report back.** Give the post path, the version and the tag used. In one line each, give the main structure decisions and the changes you left out. List the checks you ran. Say that no docs build, changelog update, commit, tag or push happened.

## Post Format

- File: `docs/news/YYYY-MM-DD-whats-new-vX.Y.Z.md`.
- Frontmatter:

    ```markdown
    ---
    title: What's New in vX.Y.Z
    date: YYYY-MM-DD
    ---
    ```

- Heading: `# What's New in RobotCode vX.Y.Z`.
- Write in English. Write the product name in prose as `**RobotCode**`.
- Link documentation pages relatively (`../03_reference/repl.md#exit-code-and-session-status`). Link issues as `([#123](https://github.com/robotcodedev/robotcode/issues/123))`.
- In-page anchors follow VitePress: the heading in lowercase, with spaces and punctuation turned into `-` and repeats collapsed. `Robot Framework 7.5 Support` becomes `#robot-framework-7-5-support`, and `In VS Code: the Documentation Viewer` becomes `#in-vs-code-the-documentation-viewer`. Leading and trailing `-` are dropped, and a slug that starts with a digit gets a `_` prefix.
- Use code blocks only for commands and configuration that users can run. One to three lines are usually enough.
- Put something the reader must do into a callout. Use GitHub's alert syntax, with the marker alone on its line and a bold first sentence as the title:

    ```markdown
    > [!IMPORTANT]
    > **Libdoc HTML needs the `markdown` package.** Because the standard libraries are now documented in Markdown, …
    ```

    This renders as a callout both on the website and on GitHub. VitePress `:::` containers, and a title written after the marker, render only on the website. VS Code's built-in Markdown preview renders none of these forms as a callout; there the GitHub form shows as a plain quote.

## Decision Points

- If `hatch run build:cz bump --get-next` fails or returns no version, stop and report the blocker.
- If there are no relevant commits since the last stable tag, don't create a post without the user's confirmation.
- If a stable tag after the last post has no post of its own, ask whether this post should cover it too. The v2.6.2 post, for example, also covers v2.6.1.
- Ask the user one question at a time, with a recommended option, in these cases:
    - A change might break existing setups and is not one of the clear cases. Clear cases are removed or renamed options, removed features, and new minimum versions of VS Code, the JetBrains IDEs or Python. Put those in Breaking Changes without asking.
    - You are unsure whether a small change deserves a line.
    - The impact of a change stays unclear after you read the code, tests and docs.
- If an upstream fix has no release or milestone yet, don't name a version or a date. Describe the condition instead: "Once a Robot Framework bugfix release includes the fix, …".

## Quality Criteria

- The first sentence states RobotCode's news: the version and the two or three changes that matter most to users.
- Chapters, subsections and list items are ordered by user impact.
- The post describes what RobotCode does. Robot Framework's own features are explained only as far as the reader needs them to understand RobotCode's part.
- The text is factual, concise and neutral, with no hype and no "would otherwise have failed" framing.
- Every Bug Fixes entry links an issue that the commit closes.
- The Markdown is valid for VitePress, with YAML frontmatter. Exactly one post is created or changed.
- No docs build, changelog update, version edit, commit, tag or push happened.

## Example Prompts

- "Create release notes for the next RobotCode version."
- "Write the What's New post for the upcoming release."
- "There are new commits, check what we can add to the news post."
- "Update the release post, focusing on the runner changes."
