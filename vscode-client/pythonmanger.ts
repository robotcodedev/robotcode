import * as path from "path";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";

export class PythonManager {
    public get pythonLanguageServerMain(): string {
        return this._pythonLanguageServerMain;
    }
    public get pythonDebugAdapterMain(): string {
        return this._pythonDebugAdapterMain;
    }
    _pythonLanguageServerMain: string;
    _pythonDebugAdapterMain: string;
    _pythonExtension: vscode.Extension<any>;

    constructor(
        public readonly extensionContext: vscode.ExtensionContext,
        public readonly outputChannel: vscode.OutputChannel
    ) {
        this._pythonLanguageServerMain = this.extensionContext.asAbsolutePath(
            path.join("robotcode", "language_server", "__main__.py")
        );
        this._pythonDebugAdapterMain = this.extensionContext.asAbsolutePath(
            path.join("robotcode", "debug_adapter", "__main__.py")
        );

        this.outputChannel.appendLine("Try to activate Python extension.");
        this._pythonExtension = vscode.extensions.getExtension("ms-python.python")!;

        this.outputChannel.appendLine("Try to activate python extension");
        this._pythonExtension.activate().then((_) => {});
        this.outputChannel.appendLine("Python Extension is active");
    }

    async dispose() {}

    get pythonExtension(): vscode.Extension<any> {
        return this._pythonExtension;
    }

    public getPythonCommand(folder: vscode.WorkspaceFolder | undefined): string | undefined {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
        let result: string | undefined = undefined;

        let configPython = config.get<string>("python");

        if (configPython !== undefined && configPython != "") {
            result = configPython;
        } else {
            const pythonExtension = vscode.extensions.getExtension("ms-python.python")!;
            let pythonExtensionPythonPath: string[] | undefined =
                pythonExtension?.exports?.settings?.getExecutionDetails(folder?.uri)?.execCommand;

            if (pythonExtensionPythonPath !== undefined) {
                result = pythonExtensionPythonPath.join(" ");
            }
        }

        return result;
    }
}
