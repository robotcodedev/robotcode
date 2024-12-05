import type { ActivationFunction } from "vscode-notebook-renderer";
import { render } from "preact";
import { Renderer } from "./renderer";
import commonCss from "./common.css";
import rendererCss from "./log.css";
import docFormattingCss from "./docFormatting.css";

export const activate: ActivationFunction = (_context) => {
  const commonStyle = new CSSStyleSheet({ media: "all" });
  commonStyle.replaceSync(commonCss);

  const logStyle = new CSSStyleSheet({ media: "all" });
  logStyle.replaceSync(rendererCss);

  const docFormattingStyle = new CSSStyleSheet({ media: "all" });
  docFormattingStyle.replaceSync(docFormattingCss);

  return {
    renderOutputItem(data, element, _signal) {
      let shadow = element.shadowRoot;

      if (!shadow) {
        shadow = element.attachShadow({ mode: "open" });

        shadow.adoptedStyleSheets = [...document.adoptedStyleSheets, commonStyle, logStyle, docFormattingStyle];

        const root = document.createElement("div");
        root.id = "root";

        shadow?.append(root);
      }

      const root = shadow.querySelector("#root");

      if (root) {
        render(<Renderer data={data.json()} />, root);
      }
    },
  };
};
