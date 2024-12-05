import commonCss from "./css/common.csstemp";
import logCss from "./css/log.csstemp";
import printCss from "./css/print.csstemp";
import docFormatting from "./css/doc_formatting.csstemp";

import jqueryJs from "./js/jquery.min.jstemp";
import logJs from "./js/log.jstemp";
import utilJs from "./js/util.jstemp";

import type { ActivationFunction } from "vscode-notebook-renderer";

export const activate: ActivationFunction = (_context) => {
  const commonCssStyle = new CSSStyleSheet({ media: "all" });
  commonCssStyle.replaceSync(commonCss);

  const logCssStyle = new CSSStyleSheet({ media: "all" });
  logCssStyle.replaceSync(logCss);

  const printCssStyle = new CSSStyleSheet({ media: "print" });
  printCssStyle.replaceSync(printCss);

  const docFormattingStyle = new CSSStyleSheet({ media: "all" });
  docFormattingStyle.replaceSync(docFormatting);

  const jqueryJsScript = document.createElement("script");
  jqueryJsScript.text = jqueryJs;

  const logJsScript = document.createElement("script");
  logJsScript.text = logJs;

  const utilJsScript = document.createElement("script");
  utilJsScript.text = utilJs;

  return {
    renderOutputItem(data, element, _signal) {
      let shadow = element.shadowRoot;

      if (!shadow) {
        shadow = element.attachShadow({ mode: "open" });

        shadow.adoptedStyleSheets = [
          ...document.adoptedStyleSheets,
          commonCssStyle,
          logCssStyle,
          printCssStyle,
          docFormattingStyle,
        ];

        shadow.append(jqueryJsScript.cloneNode(true));
        shadow.append(logJsScript.cloneNode(true));
        shadow.append(utilJsScript.cloneNode(true));

        const root = document.createElement("div");
        root.id = "root";
        shadow?.append(root);
      }

      const root = shadow.querySelector("#root");

      if (root) {
        const themeKind = document.body.getAttribute("data-vscode-theme-kind");
        const darkMode = themeKind?.includes("dark") ?? false;
        root.setAttribute("data-theme", darkMode ? "dark" : "light");
        root.innerHTML = data.text();
        const shadow_marker = root.querySelector("div,[data-shadow-marker]");
        if (shadow_marker) {
          const shadow_id = shadow_marker.getAttribute("data-shadow-marker");
          if (shadow_id) {
            element.setAttribute("data-shadow-id", shadow_id);
          }
        }
      }
    },
  };
};
