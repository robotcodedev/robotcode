// Starlight names a sidebar group it builds from a subdirectory after the directory, and neither a page nor the
// config can change that label. This middleware gives such groups their display names.
import { defineRouteMiddleware, type StarlightRouteData } from "@astrojs/starlight/route-data";

const GROUP_LABELS: Record<string, string> = { vscode: "VS Code", pycharm: "PyCharm" };

function relabel(entries: StarlightRouteData["sidebar"]): void {
  for (const entry of entries) {
    if (entry.type !== "group") continue;
    entry.label = GROUP_LABELS[entry.label] ?? entry.label;
    relabel(entry.entries);
  }
}

export const onRequest = defineRouteMiddleware((context) => {
  relabel(context.locals.starlightRoute.sidebar);
});
