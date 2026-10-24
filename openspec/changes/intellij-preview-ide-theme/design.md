# Design

## Context

See proposal.md for the motivation. What the change builds on:

- **The preview:** `RobotCodeOutputPreviewEditor` in `RobotCodeOutputPreview.kt` builds its browser with the file's URL (`JBCefBrowser.createBuilder().setUrl(file.pageUrl).build()`). `reload()` loads the file again after a run, in the same browser. Nothing in the plugin looks at the IDE's theme yet.
- **Robot Framework's theme** (`view.js` of RF 7.0.1, 7.1.1, 7.2.2, 7.3, 7.4 and 7.5; RF 6.1.1 has none):
  - At load, the page takes `?theme=dark|light` from its URL and keeps it, otherwise the kept choice (`robot-framework-theme-preference` in the local storage), otherwise `prefers-color-scheme`.
  - Afterwards it follows each change of `prefers-color-scheme` and each change of the kept choice in another page, and keeps the new value. Its own switch keeps the choice too.
- **Harness, 2026-10-24** (UI-test PyCharm 2026.1, JCEF in its remote mode, RF 7.5, report opened with "Open Report"):
  - The browser had kept "dark" from the guide's recording scripts, which load the preview with `?theme=`. Without it, the report still showed dark in Islands Light: JCEF reported `prefers-color-scheme: dark` with Islands Light and Islands Dark alike.
  - `Emulation.setEmulatedMedia` with `prefers-color-scheme: light`, sent over the browser's DevTools client, turned the open report light at once and kept it light after a reload. `dark` turned it back.
  - With the kept choice removed and `light` emulated, a reload showed light.
- **JCEF** (`JetBrains/jcef`, `dev`):
  - `CefBrowser.getDevToolsClient()` gives the one DevTools client of a browser. It returns null while the browser is not created yet, and also when the browser is closed or closing.
  - `CefDevToolsClient` is `AutoCloseable`. Its `executeDevToolsMethod(method, parametersAsJson)` returns a `CompletableFuture`.
  - No `ApiStatus` markers on either.
  - None of `CefBrowser`, `CefRequestContext`, `JBCefBrowser` and `JBCefApp` in PyCharm 2026.1 has a method that sets the color scheme. The platform does not emulate `prefers-color-scheme` anywhere.
- **Platform** (`idea/261.22158.277`):
  - `JBCefBrowserBase.loadURL` defers a load until the browser is created.
  - Installing a theme sets `JBColor`'s dark flag (`UIThemeLookAndFeelInfoImpl` → `AppUIUtil.updateForDarcula`) before `LafManagerImpl.updateUI` notifies `LafManagerListener.TOPIC`.
- **DevTools protocol:** `Emulation.setEmulatedMedia` with `features`, a list of name and value pairs, is not marked experimental.

## Goals / Non-Goals

**Goals:**

- The page sees the IDE's theme from its first load, so that it does not first show the other theme.
- An open tab follows a change of the theme as it is, with its history, its scroll position and the opened parts of the log.

**Non-Goals:**

- Changing what Robot Framework keeps in the local storage. The plugin neither reads nor writes it.
- Pages other than reports and logs in the tab: they see the same `prefers-color-scheme`, and what they do with it is theirs.

## Decisions

### D1: The IDE's theme as `prefers-color-scheme`, set over the DevTools client

The preview sends `Emulation.setEmulatedMedia` with the feature `prefers-color-scheme` set to `light` or `dark` to its browser's DevTools client. The setting belongs to the browser, so it holds for every page of the tab and for every later load, and Robot Framework's page follows a change by itself.

Alternatives:
- `?theme=light|dark` at every load. Robot Framework keeps the parameter, so every load overrides a choice made with the page's own switch. A theme change shows only at the next load, or the plugin loads the page again and loses the scroll position and the opened parts of the log.
- Setting Robot Framework's theme with JavaScript in the page. That depends on its script, the `theme` object and the storage key, which can change between versions.
- A color scheme for JCEF as a whole. PyCharm 2026.1 offers none (see Context).

### D2: The IDE's UI theme decides

The preview sends `dark` when `JBColor.isBright()` is false and `light` otherwise. That is the UI theme, not the editor's color scheme: the tab's toolbar and frame around the page are drawn in the UI theme. On a theme change, `JBColor` already has the new value when `LafManagerListener` is notified (see Context).

Alternative: the editor's color scheme. The preview shows no text of the editor, and a dark scheme in a light UI would give a dark page in a light frame.

### D3: Color scheme first, page second; again on every theme change

- **First load:** the browser is built without a URL. When JCEF reports it created (`CefLifeSpanHandler.onAfterCreated` on the browser's client), the preview sends the color scheme and loads the file when the call has completed. It also loads the file when the call failed or there is no DevTools client; the page then looks as it does today.
- **Theme changes:** the editor subscribes to `LafManagerListener.TOPIC` on the application's message bus, with itself as the parent disposable, and sends the new color scheme to its browser.
- **Disposal:** the editor closes the DevTools client when it is disposed, before the browser.

Alternative: keep the URL in the builder and send the color scheme after the browser is created. The page's first load then races the call, and when the call comes second, the page first shows the other theme. Robot Framework then also keeps the switched value as if it were a choice.

### D4: The parameters as a function of their own

A small function builds the call's parameters for light and dark. A unit test pins the JSON, `{"features":[{"name":"prefers-color-scheme","value":"dark"}]}`, since the platform tests have no browser to check the page with.

## Risks / Trade-offs

- [A choice made with the page's own switch wins at the next load] → Wanted, see the spec. Robot Framework does the same in a browser whose theme follows the system. The next change of the IDE's theme takes over again.
- [The DevTools client is missing or the call fails, for example in another JCEF mode] → the page loads anyway and looks as today. Checked in the harness only in the default mode of PyCharm 2026.1.
- [`verifyPlugin` reports the DevTools client as experimental or internal] → JCEF's sources have no such markers. Task 3.1 checks it, and a reported usage gets decided then.
- [Robot Framework stops following `prefers-color-scheme`] → the plugin uses the standard media feature, not Robot Framework's script. Its theme logic has been the same from 7.0 to 7.5.
