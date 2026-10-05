import type { HTMLAttributes } from "preact";

declare global {
  function acquireVsCodeApi(): {
    postMessage(message: unknown): void;
    getState(): unknown;
    setState(state: unknown): void;
  };
}

type CustomElement<P> = HTMLAttributes<HTMLElement> & P;

declare module "preact" {
  namespace JSX {
    interface IntrinsicElements {
      "vscode-toolbar-container": CustomElement<object>;
      "vscode-toolbar-button": CustomElement<{
        icon?: string;
        label?: string;
        toggleable?: boolean;
        checked?: boolean;
      }>;
      "vscode-textfield": CustomElement<{ value?: string; placeholder?: string; label?: string }>;
      "vscode-split-layout": CustomElement<{
        split?: "horizontal" | "vertical";
        "initial-handle-position"?: string;
        "handle-position"?: string;
        "min-start"?: string;
        "min-end"?: string;
        "fixed-pane"?: "start" | "end" | "none";
        "reset-on-dbl-click"?: boolean;
      }>;
      "vscode-progress-bar": CustomElement<{ indeterminate?: boolean }>;
    }
  }
}
