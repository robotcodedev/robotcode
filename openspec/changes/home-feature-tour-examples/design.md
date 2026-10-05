# Design: home-feature-tour-examples

## Context

See proposal.md. The feature tour is `docs/src/components/home/FeatureTour.astro`, played by `<rc-demo>` (`demo-player.ts`). A feature's panel is one of three kinds:

- `video`: Code intelligence.
- `terminal`: configuration, CLI and REPL, with steps that appear one by one through CSS animations. The animations restart when the demo gets the class `is-playing` and the panel is active (`home.css`).
- `series`: Run, debug & test explorer with two video slides, and Multi-IDE with 14 screenshots. Slides are switched by the player, one dot each, each for its `data-slide-seconds`, and the window title shows the slide's `data-title`.

All recordings and screenshots are 2072×1182 (a 1036×591 window at scale 2). Every video is in the page with `preload="metadata"`.

The recordings come from the isolated VS Code harness in `playground/robotcode-demo/vscode/` (git-ignored, README there):

- Playwright drives `/usr/share/code/code` on its own X display, with its own profile, stub Python extensions and RobotCode from the checkout.
- `ffmpeg` grabs the display without the mouse pointer, so `rec.js` draws its own pointer and a ring on each click.
- Scenes 1–4 make the four existing recordings: code intelligence, test explorer, debugging and the Documentation Viewer. Scene 4 was made for the v2.8.0 news, which does not use it yet.
- Some scenes call commands through the extension API instead of pressing keys: scene 1 opens completion and signature help with `executeCommand`.

The terminal sessions are abridged output of `capture.sh`, which runs `robotcode` from the project's environment. `robotcode-demo` has Robocop and the Browser library installed. Its `robot.toml` has the profiles `dev` and `ci`.

## Goals / Non-Goals

**Goals:**
- Every feature except Multi-IDE becomes a series of examples, in the order the spec lists them.
- The player and the markup stay the ones in place: a series gains terminal slides, and no new panel kind is added.
- Loading the home page costs no more requests than today, however many recordings the tour holds.

**Non-Goals:**
- New PyCharm or Neovim pictures.
- Changing the Multi-IDE series or the agent conversations.
- Re-cutting the content of the existing recordings.

## Decisions

### D1: Every feature is a series; terminal sessions become slides

A slide is a screenshot, a recording or a terminal session (`{ terminal: TerminalStep[] }`) and plays for this long:

- a screenshot: the series' `seconds`
- a recording: its length
- a terminal session: `steps × STEP_DELAY + HOLD`, the time a terminal panel stays today

The kinds `video` and `terminal` stop being used by a panel. Code intelligence becomes a series whose first slide is its existing recording. The old kinds are removed rather than kept unused.

Alternative: separate panels per example, one feature card each. Rejected, because it multiplies the cards and loses the grouping by feature that the dots already give (`is-group-start` is unused here, since the labels differ).

### D2: Steps of a terminal slide replay whenever the slide is shown

The step animation is tied to `.is-playing .is-active`. For a slide it must restart when the slide becomes current. The player toggles `is-playing` on the current slide, reflowing it the same way `#show` already reflows the demo. The CSS animates `.rc-step` inside a playing current slide.

- The pause, hover and hidden states keep holding the steps as today.
- Under reduced motion a terminal slide shows all its steps, as terminal panels do now.
- The window keeps one size for all slides, because the slides share one grid cell. A terminal slide has the window's terminal background, as terminal panels had, so that it stays readable in the light theme. Only screenshots and recordings get the dark background.
- A terminal session is kept no taller than a recording, about 14 lines at the home page's width, so the window does not grow.
- The dots that select an example are 24 px buttons, the minimum target size Lighthouse checks. The first feature now has dots, so they are visible and checked on load.

### D3: Recordings load when their slide is shown

With some twenty recordings on the page, `preload="metadata"` would add a request for each on load. Videos in a slide therefore get `preload="none"`, and the player's existing `play()` on show starts the download. Only the first slide of the first feature keeps `preload="metadata"`, so that the tour starts without a blank frame.

Alternative: a poster image per video. Rejected for now. It means 20 more images, and a recording paints its first frame quickly once requested.

### D4: Screencast mode shows the shortcuts, not the clicks

The harness turns on VS Code's screencast mode (`workbench.action.toggleScreencastMode`) before recording (`playground/robotcode-demo/vscode/screencast.js`). It uses these settings, tried on test frames on 2026-10-05 with VS Code 1.140 and viewed at the size the home page shows recordings (608 px wide):

- `screencastMode.keyboardOptions` shows only the keys, without command names, typed text or cursor moves: `showKeys: false`, `showKeybindings: true`, `showCommands: false`. The settings `onlyKeyboardShortcuts` and `keyboardShortcutsFormat` no longer exist in this version.
- `screencastMode.fontSize: 28` and `screencastMode.verticalOffset: 8` put a small key label just above the status bar. At the default size of 56, the overlay covered about a third of the editor.
- `screencastMode.mouseIndicatorColor` is fully transparent, because `rec.js` already draws the pointer and the click ring.

VS Code shows every key that is bound to a command, so Enter, Escape, End and Tab would appear too. `screencast.js` therefore hides the overlay after a key that has no Ctrl, Alt or Meta and is not a function key. On the test frames, F12, Shift+F12 and Ctrl+Shift+Space appeared, while Escape, End, Enter and typed text did not. Playwright's key presses reach the overlay.

Scenes press a shortcut wherever the overlay should show it, rather than calling the command through the API. Scene 1 presses Ctrl+Space and Ctrl+Shift+Space. The new scenes press F12, Shift+F12 and so on. Actions done with the mouse stay mouse actions; for example, the debugging scene keeps clicking the toolbar.

Alternative: keep recording without screencast mode and add captions afterwards. Rejected: captions need a video editing step per recording, while the overlay comes from VS Code itself.

### D5: The existing recordings are recorded again with the same scenes

Scenes 1–4 run again with screencast mode, and the only change is D4's switch from API calls to key presses. The new MP4s replace the old files under the same names, and the Documentation Viewer recording is added as `vscode-documentation-viewer.mp4`.

If a re-recording differs from the old one in more than the overlay, the old file stays and the difference is reported. That covers a changed hover, a moved test or a scene that no longer reproduces.

### D6: New VS Code scenes

Each new scene is a scene file of its own in `playground/robotcode-demo/vscode/` (`scene5.js` to `scene14.js`), lasts 8–15 s and starts from `ctx.resetTo` in `scene5.js`. That helper closes the editors, removes breakpoints and test results, and sets the inlay hints. It also clicks once into the editor, because the context menu of a run icon leaves a hover behind that keeps other hovers away. The examples per feature are the ones the spec lists. Where a scene ended up different from the plan, the reason is given below.

- **Go to Definition**: F12 on `Create Order` in a test opens the keyword in `orders.resource`, and F12 on `Place Order` there opens `place_order` in `libraries/ShopLibrary.py`.
- **Find References**: Shift+F12 on `Open Shop As` opens the peek view, which steps into `cart.robot` and `login.robot`. Its tree also shows the call passed to `Run Keyword And Expect Error`. The preview of that call is not selected, because the narrow preview cuts the line off.
- **Diagnostics**: a new test with a misspelt keyword call gets RobotCode's error and Robocop's warnings (missing documentation, unused variable). Ctrl+Shift+M opens the Problems panel with both sources, and correcting the call removes the error. No quick fix is applied: Robocop's findings have none, and the only one for the error, Create Keyword, is in the first recording.
- **Keywords view**: Ctrl+Shift+E shows the view, a resource is expanded, and its inline Insert action puts a keyword into a test. Signature help then shows the argument, and a value is typed.
- **Stopping at a failure**: Debug Test on `Login Works` without a breakpoint stops at `Should Be Equal` in `shop.resource`, because "Uncaught Failed Keywords" is the default exception filter. The exception widget and the inline values show the two greetings.
- **Debug Console**: at a breakpoint in `Order Coffee`, Ctrl+Shift+Y opens the Debug Console. There `${order}` and `Order Status    ${order}` are evaluated.
- **Log after a run**: with `robotcode.run.openOutputAfterRun: "log"`, Run Test opens the log beside the editor in VS Code's browser. Scrolling in it is left out, because the browser's content does not receive Playwright's input.
- **`robot.toml` schema**: Ctrl+Space offers the values of `console`, and a hover over `output-dir` shows its documentation. Even Better TOML in the harness is mapped to the checkout's `docs/public/schemas/robot.toml.json`, and its status bar entry, which shows the schema's path, is hidden.
- **Profile in VS Code**: the command palette's Select Configuration Profiles picks `ci`, and Debug Test then stops at a breakpoint in `Open Shop As`. There the inline value shows the profile's `BASE_URL`. A plain run was not used, because its output shows no logged values. The status bar's language status was not used either, because it shows RobotCode's version, which is still 2.7.0 until the release.
- **REPL in VS Code**: the command palette's Start Terminal REPL opens `robotcode repl` in the terminal panel, and a library keyword is called there. The harness terminal is bash with a prompt without user or host name and with the example project's environment active, as the Python extension would activate it. The REPL's banner shows RobotCode's version.

### D7: Terminal sessions come from `capture.sh`

`capture.sh` gets a `# Feature tour` section per new session. The output is abridged by hand like the existing sessions, and the commands match the spec's list.

- **CLI**:
  - `discover tests -i smoke` and `discover tests -btm "Requirement:SHOP-110"`
  - `analyze code`, in the default output
  - `results summary` after a run
  - `doc ShopLibrary`
- **Run and debug**: `robot-debug` on `Login Works`, reusing the agent conversation's capture: stop at the failure, then `.where` and `.print`.
- **REPL**: the Browser library at the shop page, reusing the conversation's capture. The debugger session attaches at the prompt: `Import Resource`, `.debug on`, `.break Place Order`, then a call of `Create Order` stops at `(rdb)` inside it, and `.print ${product}` shows the argument. `repl --break "Create Order"` was not used, because it stops at the call in the prompt, where `${product}` does not exist yet.
- **Configuration**: the CI example is a file step showing `.github/workflows/tests.yml` of the demo project, which runs `robotcode -p ci robot`. A local run of the same command is left out, because it would make the session taller than a recording.

### D8: Texts and links

A feature's description gains a few words only where its examples show something it does not name: the Documentation Viewer and the Keywords view for Code intelligence, CI for the configuration, and the debugger at the prompt for the REPL. Links point only to existing pages:

- Code intelligence: `/guides/browsing-documentation/`
- REPL: the section "Debugging at the prompt" of `/guides/repl/`

## Risks / Trade-offs

- **[A VS Code update changes the screencast settings]** (as `onlyKeyboardShortcuts` disappeared) → The test frame of task 2.1 is repeated before recording.
- **[Even Better TOML needs network access or a VSIX in the harness]** → Install it from a downloaded VSIX into the harness's `exts/`. If that fails, record the schema example without the extension's hover and say so.
- **[The log may not open in VS Code under Xvfb]** (integrated browser or Simple Browser in the harness) → Try `openOutputTarget` `simpleBrowser`. If it does not render, drop that example and report.
- **[The tour gets long]** (about 1–1.5 min per feature) → The dots let readers select any example. Feature order and the first example stay as they are, so the first impression does not change.
- **[Recordings show a feature that changes later]** → Scenes stay in the playground and are re-run like scenes 1–4, the same as the demo text, which is adapted by hand.

## Migration Plan

1. Implement on top of the switch (`docs/` is the Starlight site).
2. Archive this change after `migrate-docs-to-starlight`, whose delta adds the Home page demos requirement modified here.
3. Nothing is published before the site goes live with v2.8.0. The change can ship with that deploy or with a later one.
