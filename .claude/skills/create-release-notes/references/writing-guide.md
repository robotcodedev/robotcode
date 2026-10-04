# Writing a RobotCode Release Post

A release post is an announcement. The changelog records every change; the post curates. In Michael Lynch's words, release notes "should be exhaustive while release announcements should curate the changes to include only the most impactful ones". A list of commits with headings is release notes, not an announcement.

The post is about the highlights. The documentation describes each feature in detail, so the post says in a sentence or two what a change gives the user and links the documentation for the rest. It does not describe again what the documentation already explains.

News is written as an inverted pyramid: the most important facts come first, and the details follow in decreasing order of importance. Readers can stop at any point and still have the story. Many readers of a release post only read the first paragraph, so that paragraph has to carry the news on its own.

## Anatomy of a Post

```markdown
---
title: What's New in vX.Y.Z
date: YYYY-MM-DD
---

# What's New in RobotCode vX.Y.Z

<lede: one sentence> <product sentence>

Highlights of this release:

- [<Feature>](#<anchor>): <what the reader can do, in one sentence>
- …

## Breaking Changes
## <headline chapter, for example "Robot Framework X.Y Support">
### <big feature that needs the new version>
### Also on Robot Framework X.Y
## <big editor feature>
## PyCharm and IntelliJ IDEA
## Editor and CLI Polish
## <power-user chapter: command line, REPL>
## Bug Fixes
## Under the Hood

---

## Thank You
```

Not every post has every chapter. A patch release is mostly Bug Fixes, with a short lede and no highlights list.

## The Opening

### The lede

The first sentence states RobotCode's own news: the version and the two or three changes that matter most to users. It is at most about 40 words. If there is more, end with "along with many smaller enhancements and bug fixes".

- Start with **RobotCode** and the version. Don't start with background, a date, a slogan or another project's release.
- Name what RobotCode does ("adds support for Robot Framework 7.5"), not what Robot Framework added.
- "Most important" means what most readers notice. Editor features usually rank above command-line tools.

The lede of v2.8.0:

> **RobotCode** v2.8.0 adds support for Robot Framework 7.5, a Documentation Viewer for VS Code and test selection by metadata, along with many smaller enhancements and bug fixes.

Openings the maintainer rejected for v2.8.0, and why:

- "Robot Framework 7.5 was released in September, and **RobotCode** v2.8.0 brings support for it …": it opens with someone else's news. The news is RobotCode's.
- "Robot Framework 7.5 is here, and **RobotCode** v2.8.0 is ready for it. Libraries can now document their keywords in Markdown …": it describes Robot Framework's features, not RobotCode's.
- "With **RobotCode** v2.8.0, the documentation of your keywords is always one step away. The new `robotcode doc` command …": it is a slogan, and it leads with a tool only power users need.
- "**RobotCode** v2.8.0 supports Robot Framework 7.5 and understands what it adds: …", followed by nearly every change of the release in four long sentences: a feature dump with no priority.

Other projects use the same structure: their own news first, then a short list of highlights. Copy the structure; the tone is set under Wording.

- Robot Framework 7.5: "Robot Framework 7.5 is a new feature release with major enhancements to the library documentation tool Libdoc, support for test/task metadata, enhanced console logging configuration and several other enhancements and bug fixes."
- Django: one sentence that announces the release, then "A few highlights are:" and three bullets.
- VS Code: a "Release highlights" block with one theme sentence and bullets of the form "Feature: one benefit sentence".

The Robot Framework ecosystem (Robot Framework, SeleniumLibrary, the Browser library, Robocop) opens matter-of-factly; none of its recent release posts says "excited" or "proud". RobotCode uses the same tone.

### The product sentence

Right after the lede comes one sentence for readers who don't know RobotCode. Base it on the README, without superlatives:

> **RobotCode** brings Robot Framework support to VS Code, PyCharm, IntelliJ IDEA and the command line.

### The highlights list

After "Highlights of this release:" come three to five bullets. Each has the form `[Feature](#anchor): what the reader can do`, in one sentence, and links to its chapter. Choose the bullets by user impact: features in the editor before tools for power users. Breaking changes are not highlights; they have their own chapter right below.

## Changes Users See

A commit body says how the code changed. The post says what changes for the user, and the two are not always the same. Before you announce something, check that users see a difference: in the code and, for the VS Code extension, in what VS Code itself already does. The commit that added the Documentation Viewer said that log and report files "now open beside the editor in VS Code's integrated browser". The extension had switched from the Simple Browser to the integrated browser, but on desktop VS Code's Simple Browser already forwards to the integrated browser, so users saw no difference worth announcing. The line was cut.

## Ordering

- Weigh the audience: VS Code users first, then PyCharm and IntelliJ users, then command-line power users.
- Use tiers. Headline features get a chapter or subsection with an explanation and, if useful, an example. Secondary changes get one bullet. The long tail stays in the changelog. Not every change needs a highlight.
- Space signals importance: a long section reads as an important feature. Don't spend a paragraph on a deprecation or a cosmetic fix.
- Inside each list, what most readers notice comes first. Rarely used features and deprecations come last; cosmetic changes are left out.
- Group by topic. An item belongs with the feature it concerns. For example, the new `${TEST_METADATA}` variable goes with test metadata, not into a general list.

## Chapter Patterns

### Breaking Changes

One bullet per change. A bold lead sentence says what changed; the rest says what happens and what to do. Order the bullets by the number of affected users.

> - **The VS Code extension needs VS Code 1.127 or newer.** Older VS Code versions keep the newest **RobotCode** release they can install.
> - **The IntelliJ plugin needs PyCharm or IntelliJ IDEA 2026.1 or newer.** Older IDE versions no longer receive plugin updates.
> - **`--tags` is now `--show-tags`.** … The old name is no longer accepted, so update any scripts that use it.

### Support for a New Robot Framework Version

The chapter is called "Robot Framework X.Y Support". It opens with what RobotCode does and one general pointer, without a link, to the Robot Framework documentation for what is new in Robot Framework itself. The pointer covers the whole chapter; don't repeat it in the subsections:

> **RobotCode** now supports Robot Framework 7.5. What is new in Robot Framework 7.5 itself is described in the Robot Framework documentation. Here is what changes in **RobotCode**.

- Only things that need the new version, or that matter mainly because of it, belong in this chapter. In v2.8.0 these were the keyword documentation, test metadata, Markdown resource files, the new `robot.toml` values and the `Tags:` deprecation. The rendering of Markdown documentation works on every version, but it stayed in the chapter because the standard libraries switched to Markdown in 7.5. Improvements that also apply to older versions go into other chapters.
- The big RobotCode features that the new version makes possible get subsections, the most visible first. For v2.8.0 these were argument descriptions in hover, signature help and completion, then test metadata.
- Explain the Robot Framework feature only as far as the reader needs to follow RobotCode's part: one sentence and, if it helps, a short example.
- Small items go into a final "Also on Robot Framework X.Y" list, ordered by impact, with deprecations last.
- If users must act, for example by installing a package, use an `IMPORTANT` callout next to the feature it concerns. Name an alternative if there is one: "If you don't want to install it, use the new Documentation Viewer or `robotcode doc` instead: both show the documentation without the `markdown` package."
- For a known upstream bug that users will run into, say what they will notice and link the upstream issue. Promise nothing beyond the issue's state: "Once a Robot Framework bugfix release includes it, the buttons will appear in the right place."
- Leave out upstream details that don't change what RobotCode users do. For v2.8.0, a note that older Robot Framework versions cannot read 7.5 result files with test metadata was removed.

### Editor Features and the IDE Chapter

A feature chapter says what the user can do now, how to open or use it (commands, menus, views), and links the guide for details.

- When a change shows up in several places, name the one most users know; it stands for the rest. "A click on a link in a **hover**" replaced a list of hovers, completion details, signature help and the tooltips of the Keywords view.
- When a new feature replaces an old one, say that the old one is deprecated in favour of the new one and keeps working, and nothing more about it. In v2.8.0, the fixes to *Open Documentation* were cut once it was deprecated.

The chapter for PyCharm and IntelliJ IDEA uses bullets with a bold lead sentence:

> - **Colors come from the active color scheme.** Variables, keyword calls, operators and numbers get colors from your scheme instead of plain text, …

### Power-User Tools

Keep changes to the command line, the REPL and `robotcode doc` short: what the tool does, one or two example commands, and a link to the reference. When the AI chat plugins start using a new command or behave differently, say so in one sentence where the feature is described.

### Editor and CLI Polish

One line per fix, saying what the user notices now. No error messages, internals or reasons:

> - On Windows, commands no longer fail when a given path is on a different drive than the working directory.

### Bug Fixes

Only fixes whose commit closes a GitHub issue, each in one or two sentences with the issue link. A change that only references an issue (`Refs #123`), or whose issue stays open, goes into its topical chapter with the link instead.

### Under the Hood

Experimental or internal work that users can opt into. One paragraph, last before the footer.

## Wording

- Describe what RobotCode does now. Use "no longer" only for bugs that users had in a released version. For support of something new, don't describe what would have gone wrong without it. "Several things that 7.5 changed would otherwise have caused lost information or false errors" was rejected for that reason.
- Stay non-technical. Leave out diagnostic codes, cache details and class or module names unless the reader acts on them. For v2.8.0, the library-loading section went from four bullets with error codes and cache details to one paragraph: "A library that hangs or exits while it loads no longer holds up the editor or `robotcode analyze code`. …"
- No hype: no "excited", "proud", "ultimate" or "powerful", and no exclamation marks. Address the reader as "you".
- A heading names what the user gets: "Richer Keyword Documentation", "More Robust Library Loading".
- Give a reason only if a commit, the code or the docs back it.
- Use an example only if it is real and shows the point. "Its heading, such as `Keyword Log`" was cut: readers take `Keyword Log` for a keyword, but the keyword is `Log`, and its documentation has no links. An example taken from the docs needs the same check. If no example fits, write the sentence without one.
- Write plain English, one idea per sentence where possible.
