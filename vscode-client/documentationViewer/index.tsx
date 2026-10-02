import "@vscode-elements/elements/dist/vscode-progress-bar/index.js";
import "@vscode-elements/elements/dist/vscode-split-layout/index.js";
import "@vscode-elements/elements/dist/vscode-textfield/index.js";
import "@vscode-elements/elements/dist/vscode-toolbar-button/index.js";
import "@vscode-elements/elements/dist/vscode-toolbar-container/index.js";
import { render } from "preact";
import { App, Controller } from "./app";

const root = document.getElementById("root");
if (root !== null) render(<App controller={new Controller()} />, root);
