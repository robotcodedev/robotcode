# Tasks

## 1. The page

- [ ] 1.1 Check the labels that the page names in the sources: **Switch to Pre-Release Version** and **Switch to Release Version** in microsoft/vscode at tag `1.127.0`, and **Manage Plugin Repositories...** in JetBrains/intellij-community on the branch of build 261. Note the files and the labels found here, and use the labels found if they differ from design.md.
- [ ] 1.2 Check the pip way in a scratch virtual environment: `pip install "robotcode[runner,analyze]==<newest dev version>"` installs that version of `robotcode` and of its `robotcode-*` packages, and a release of Robot Framework. Note the versions here.
- [ ] 1.3 Write `docs/src/content/docs/getting-started/dev-builds.md` with the content of design.md: frontmatter with `title`, `description` and `sidebar` (label "Dev Builds", order 40), an intro and one section each for VS Code, PyCharm and the Python packages, and a short section on reporting problems. Verify that `npm run docs:build` passes and that the Getting Started overview lists the page.

## 2. README

- [ ] 2.1 Add a line to "Get Involved" in `README.md` that links `https://robotcode.io/getting-started/dev-builds/`, for example "Try the dev builds and report what you find". Verify that the path matches the built page (`docs/dist/getting-started/dev-builds/index.html`).

## 3. Verification

- [ ] 3.1 After the maintainer pushes and the site is deployed, open https://robotcode.io/getting-started/dev-builds/ and follow the link from the README on GitHub.

## Workflow follow-up

- Archive the change after 3.1.
