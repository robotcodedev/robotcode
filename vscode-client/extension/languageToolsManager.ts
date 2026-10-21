import * as vscode from "vscode";
import {
  ClientState,
  LanguageClientsManager,
  ProjectInfo,
  describeRobotEnvironmentProblem,
  isRobotFrameworkProblem,
} from "./languageclientsmanger";
import {
  CONFIG_ANALYSIS_DIAGNOSTICMODE,
  CONFIG_ANALYSIS_DIAGNOSTICMODE_OPENFILESONLY,
  CONFIG_ANALYSIS_DIAGNOSTICMODE_WORKSPACE,
  CONFIG_PROFILES,
  CONFIG_ROBOCOP_ENABLED,
  CONFIG_SECTION,
} from "./config";
import { PythonManager } from "./pythonmanger";
import { LanguageStatusSeverity } from "vscode";
import { TestControllerManager } from "./testcontrollermanager";

import * as path from "path";
import * as fs from "fs-extra";

const NOT_INSTALLED = "not installed";
const UNKNOWN = "unknown";

type QuickPickActionItem = {
  label?: string;
  getLabel?(folder?: vscode.WorkspaceFolder): string | undefined;
  kind?: vscode.QuickPickItemKind;

  iconPath?:
    | vscode.Uri
    | {
        light: vscode.Uri;
        dark: vscode.Uri;
      }
    | vscode.ThemeIcon;
  description?: string;
  getDescription?(folder?: vscode.WorkspaceFolder): string | undefined;
  detail?: string;
  getDetail?(folder?: vscode.WorkspaceFolder): string | undefined;
  alwaysShow?: boolean;
  buttons?: readonly vscode.QuickInputButton[];

  action?(folder?: vscode.WorkspaceFolder): Promise<void>;
};

export class LanguageToolsManager {
  private _workspaceFolderLanguageStatuses = new WeakMap<vscode.WorkspaceFolder, ProjectInfo>();
  private _disposables: vscode.Disposable;

  readonly robotCode: vscode.LanguageStatusItem;
  readonly robotVersion: vscode.LanguageStatusItem;
  readonly robocopVersion: vscode.LanguageStatusItem;
  readonly pythonVersion: vscode.LanguageStatusItem;
  readonly profiles: vscode.LanguageStatusItem;

  readonly toolMenu: QuickPickActionItem[] = [
    { label: "Settings", kind: vscode.QuickPickItemKind.Separator },
    {
      label: "Select Configuration Profiles",
      getDetail: (folder?: vscode.WorkspaceFolder): string | undefined => {
        const b = vscode.workspace
          .getConfiguration(CONFIG_SECTION, folder ?? vscode.window.activeTextEditor?.document)
          .get<string[]>(CONFIG_PROFILES);

        return b && b.length > 0 ? `Current ${b?.join(", ")}` : undefined;
      },
      action: async (folder?: vscode.WorkspaceFolder): Promise<void> => {
        this.testControllerManger.selectConfigurationProfiles(folder);
      },
    },
    {
      label: "Start Terminal REPL",
      description: "Starts an interactive Robot Framework REPL session in the terminal",
      async action(folder?: vscode.WorkspaceFolder): Promise<void> {
        if (folder !== undefined) {
          await vscode.commands.executeCommand("robotcode.startTerminalRepl", folder);
        }
      },
    },
    {
      getLabel: (folder?: vscode.WorkspaceFolder): string => {
        const b = vscode.workspace
          .getConfiguration(CONFIG_SECTION, folder ?? vscode.window.activeTextEditor?.document)
          .get<boolean>(CONFIG_ROBOCOP_ENABLED);

        return b ? "Disable Robocop" : "Enable Robocop";
      },
      action: async (folder?: vscode.WorkspaceFolder): Promise<void> => {
        const b = vscode.workspace.getConfiguration(CONFIG_SECTION, folder).get<boolean>(CONFIG_ROBOCOP_ENABLED);

        await vscode.workspace.getConfiguration(CONFIG_SECTION, folder).update(CONFIG_ROBOCOP_ENABLED, !b);
      },
    },
    {
      getLabel(folder?: vscode.WorkspaceFolder): string {
        const b = vscode.workspace
          .getConfiguration(CONFIG_SECTION, folder ?? vscode.window.activeTextEditor?.document)
          .get<string>(CONFIG_ANALYSIS_DIAGNOSTICMODE);

        return b === CONFIG_ANALYSIS_DIAGNOSTICMODE_OPENFILESONLY
          ? "Enable Workspace Wide Diagnostics"
          : "Disable Workspace Wide Diagnostics";
      },
      action: async (folder?: vscode.WorkspaceFolder): Promise<void> => {
        const b = vscode.workspace
          .getConfiguration(CONFIG_SECTION, folder ?? vscode.window.activeTextEditor?.document)
          .get<string>(CONFIG_ANALYSIS_DIAGNOSTICMODE);

        await vscode.workspace
          .getConfiguration(CONFIG_SECTION, folder)
          .update(
            CONFIG_ANALYSIS_DIAGNOSTICMODE,
            b == CONFIG_ANALYSIS_DIAGNOSTICMODE_OPENFILESONLY
              ? CONFIG_ANALYSIS_DIAGNOSTICMODE_WORKSPACE
              : CONFIG_ANALYSIS_DIAGNOSTICMODE_OPENFILESONLY,
          );
      },
    },
    { label: "Environment", kind: vscode.QuickPickItemKind.Separator },
    {
      label: "Select Python Environment",
      description: "Selects the Python interpreter to use",
      action: async (folder?: vscode.WorkspaceFolder) =>
        await this.languageClientsManager.selectPythonEnvironment(folder),
    },
    { label: "Developer Tools", kind: vscode.QuickPickItemKind.Separator },
    {
      label: "Restart Language Server",
      description: "Restarts the language server",
      async action(folder?: vscode.WorkspaceFolder): Promise<void> {
        if (folder !== undefined) {
          await vscode.commands.executeCommand("robotcode.restartLanguageServers", folder?.uri);
        }
      },
    },
    {
      label: "Clear Cache and Restart",
      description: "Clears the cache and restarts the language server",
      async action(folder?: vscode.WorkspaceFolder): Promise<void> {
        if (folder !== undefined) {
          await vscode.commands.executeCommand("robotcode.clearCacheRestartLanguageServers", folder?.uri);
        }
      },
    },
    {
      label: "Open Log",
      action: async (_folder?: vscode.WorkspaceFolder): Promise<void> => {
        this.outputChannel.show();
      },
    },
    {
      label: "Open Language Server Log",
      action: async (folder?: vscode.WorkspaceFolder): Promise<void> => {
        if (folder !== undefined) {
          (await this.languageClientsManager.getLanguageClientForResource(folder?.uri))?.outputChannel.show();
        }
      },
    },
    {
      get label(): string {
        const b =
          vscode.workspace
            .getConfiguration(CONFIG_SECTION, vscode.window.activeTextEditor?.document)
            .get<string[]>("languageServer.extraArgs")?.length ?? 0;

        return b ? "Disable Debug Log" : "Enable Debug Log";
      },
      action: async (folder?: vscode.WorkspaceFolder): Promise<void> => {
        const b =
          vscode.workspace
            .getConfiguration(CONFIG_SECTION, vscode.window.activeTextEditor?.document)
            .get<string[]>("languageServer.extraArgs")?.length ?? 0;
        if (b) {
          await vscode.workspace.getConfiguration(CONFIG_SECTION, folder).update("languageServer.extraArgs", undefined);
        } else {
          await vscode.workspace
            .getConfiguration(CONFIG_SECTION, folder)
            .update("languageServer.extraArgs", ["--verbose", "--log", "--log-level", "DEBUG"]);
        }
      },
    },
    {
      label: "Report Issue",
      action: async (folder?: vscode.WorkspaceFolder): Promise<void> => {
        vscode.commands.executeCommand("robotcode.reportIssue", folder);
      },
    },
  ];

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly pythonManager: PythonManager,
    public testControllerManger: TestControllerManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    const selector = { language: "robotframework" };
    this.robotCode = vscode.languages.createLanguageStatusItem("robotcode1", selector);
    this.robotCode.text = `$(robotcode-robotcode) ${this.extensionContext.extension.packageJSON.version}`;
    this.robotCode.detail = "RobotCode Version";

    this.robotVersion = vscode.languages.createLanguageStatusItem("robotcode2", selector);
    this.pythonVersion = vscode.languages.createLanguageStatusItem("robotcode3", selector);
    this.robocopVersion = vscode.languages.createLanguageStatusItem("robotcode4", selector);
    this.profiles = vscode.languages.createLanguageStatusItem("robotcode5", selector);

    this._disposables = vscode.Disposable.from(
      this.robotCode,
      this.robotVersion,
      this.pythonVersion,
      this.robocopVersion,
      this.profiles,
      vscode.commands.registerCommand("robotcode.createNewFile", LanguageToolsManager.createNewFile),
      vscode.commands.registerCommand(
        "robotcode.startTerminalRepl",
        async (folder: vscode.WorkspaceFolder | undefined): Promise<void> => {
          if (folder === undefined) {
            folder =
              vscode.window.activeTextEditor !== undefined
                ? vscode.workspace.getWorkspaceFolder(vscode.window.activeTextEditor?.document.uri)
                : undefined;

            if (!folder) {
              if (vscode.workspace.workspaceFolders?.length === 1) {
                folder = vscode.workspace.workspaceFolders[0];
              } else if (vscode.workspace.workspaceFolders?.length == 0) {
                folder = undefined;
              } else {
                folder = await vscode.window.showWorkspaceFolderPick();
              }
            }
          }
          if (folder === undefined) return;

          await this.startTerminalRepl(folder);
        },
      ),
      vscode.commands.registerCommand("robotcode.disableRoboCop", async () => {
        if (vscode.window.activeTextEditor !== undefined) {
          await vscode.workspace
            .getConfiguration(CONFIG_SECTION, vscode.window.activeTextEditor?.document)
            .update(CONFIG_ROBOCOP_ENABLED, false);
        }
      }),
      vscode.commands.registerCommand("robotcode.enableRoboCop", async () => {
        if (vscode.window.activeTextEditor !== undefined) {
          await vscode.workspace
            .getConfiguration(CONFIG_SECTION, vscode.window.activeTextEditor?.document)
            .update(CONFIG_ROBOCOP_ENABLED, true);
        }
      }),
      vscode.commands.registerCommand(
        "robotcode.selectPythonEnvironment",
        async (folder: vscode.WorkspaceFolder | undefined = undefined) => {
          if (folder === undefined) {
            folder =
              vscode.window.activeTextEditor !== undefined
                ? vscode.workspace.getWorkspaceFolder(vscode.window.activeTextEditor.document.uri)
                : undefined;

            if (!folder) {
              if (vscode.workspace.workspaceFolders?.length === 1) {
                folder = vscode.workspace.workspaceFolders[0];
              } else if (vscode.workspace.workspaceFolders?.length) {
                folder = await vscode.window.showWorkspaceFolderPick();
              }
            }
          }
          if (folder === undefined) return;

          await this.languageClientsManager.selectPythonEnvironment(folder);
        },
      ),

      vscode.commands.registerCommand("robotcode.reportIssue", async (folder?: vscode.WorkspaceFolder) => {
        if (folder === undefined) {
          if (vscode.window.activeTextEditor !== undefined) {
            folder = vscode.workspace.getWorkspaceFolder(vscode.window.activeTextEditor.document.uri);
          }
        }
        if (folder === undefined) {
          if (vscode.workspace.workspaceFolders !== undefined && vscode.workspace.workspaceFolders.length === 1) {
            folder = vscode.workspace.workspaceFolders[0];
          } else {
            if (vscode.workspace.workspaceFolders !== undefined && vscode.workspace.workspaceFolders.length > 1) {
              folder = await vscode.window.showWorkspaceFolderPick();
            }
          }
        }
        const folders = folder !== undefined ? [folder] : (vscode.workspace.workspaceFolders ?? []);

        const bodyTemplatePath = path.join(
          extensionContext.extensionPath,
          "resources",
          "report_issue_body_template.md",
        );
        const issueBody = (await fs.readFile(bodyTemplatePath, { encoding: "utf8" })).replaceAll("\r", "").trim();

        const dataTemplatePath = path.join(
          extensionContext.extensionPath,
          "resources",
          "report_issue_data_template.md",
        );
        let data = (await fs.readFile(dataTemplatePath, { encoding: "utf8" })).replaceAll("\r", "").trim();

        const pythonVersions: string[] = [];
        const robotFrameworkVersions: string[] = [];
        const robocopVersions: string[] = [];

        for (const folder of folders) {
          const pythonInfo = await pythonManager.getPythonInfo(folder);

          if (pythonInfo !== undefined) {
            const n = `${pythonInfo.version}${pythonInfo.type !== undefined ? " " + pythonInfo.type : ""}`;
            if (!pythonVersions.includes(n)) pythonVersions.push(n);
          }

          const info = await this.languageClientsManager.getProjectInfo(folder);
          if (info !== undefined) {
            if (info.robotVersionString && !robotFrameworkVersions.includes(info.robotVersionString))
              robotFrameworkVersions.push(info.robotVersionString);

            if (info.robocopVersionString && !robocopVersions.includes(info.robocopVersionString))
              robocopVersions.push(info.robocopVersionString);
          }
        }

        data = data.replace("${{ PYTHON_VERSION }}", pythonVersions.join(", "));
        data = data.replace("${{ ROBOTFRAMEWORK_VERSION }}", robotFrameworkVersions.join(", "));
        data = data.replace(
          "${{ ADDITIONAL_TOOLS }}",
          robocopVersions.length > 0
            ? [robocopVersions.map((v) => "robotframework-robocop==" + v).join(", ")].join(", ")
            : "",
        );

        const args = {
          extensionId: "d-biehl.robotcode",
          // issueTitle: "Issue with RobotCode",
          issueBody,
          data,
        };

        await vscode.commands.executeCommand("workbench.action.openIssueReporter", args);
      }),

      vscode.commands.registerCommand("robotcode.showToolMenu", async (folder?: vscode.WorkspaceFolder) => {
        let f = folder;

        if (f === undefined) {
          if (vscode.window.activeTextEditor !== undefined) {
            f = vscode.workspace.getWorkspaceFolder(vscode.window.activeTextEditor.document.uri);
            if (f === undefined) {
              vscode.window.showErrorMessage("Active document does not belong to a workspace folder.");
              return;
            }
          } else {
            if (vscode.workspace.workspaceFolders !== undefined && vscode.workspace.workspaceFolders.length === 1) {
              f = vscode.workspace.workspaceFolders[0];
            } else {
              if (vscode.workspace.workspaceFolders !== undefined && vscode.workspace.workspaceFolders.length > 1) {
                f = await vscode.window.showWorkspaceFolderPick();
              }
            }
          }
        }

        if (f !== undefined && this.languageClientsManager.hasClientForResource(f.uri)) {
          folder = f;
        } else {
          vscode.window.showErrorMessage("No RobotCode Language Server running for this workspace folder.");
        }

        if (folder === undefined) {
          return;
        }

        const result = await vscode.window.showQuickPick(
          this.toolMenu.map((v) => {
            return {
              label: v.getLabel !== undefined ? v.getLabel(folder) : v.label,
              action: v.action,
              kind: v.kind,
              iconPath: v.iconPath,
              description: v.getDescription !== undefined ? v.getDescription(folder) : v.description,
              detail: v.getDetail !== undefined ? v.getDetail(folder) : v.detail,
              alwaysShow: v.alwaysShow,
              buttons: v.buttons,
            } as vscode.QuickPickItem & QuickPickActionItem;
          }),
          {
            title: "RobotCode Menu",
            placeHolder: "Select an action",
          },
        );

        if (result !== undefined && result.action !== undefined) {
          await result.action(folder);
        }
      }),
      languageClientsManager.onClientStateChanged(async (status) => {
        const folder = vscode.workspace.getWorkspaceFolder(status.uri);
        if (folder === undefined) {
          return;
        }
        switch (status.state) {
          case ClientState.Starting:
            this.removeFolder(folder);
            this.robotVersion.busy = true;

            break;
          default:
            this.removeFolder(folder);
            this.robotVersion.busy = false;

            break;
        }
        await this.updateItems();
      }),
      languageClientsManager.onRobotEnvironmentStateChanged(async (event) => {
        this.removeFolder(event.folder);
        await this.updateItems();
      }),
      vscode.window.onDidChangeActiveTextEditor(async (editor) => {
        await this.updateItems(editor);
      }),
    );
    setTimeout(() => {
      this.updateItems().then(
        (_) => undefined,
        (_) => undefined,
      );
    }, 500);
  }

  static async createNewFile(destinationFolder?: vscode.Uri): Promise<vscode.TextDocument | undefined> {
    let showSaveDialog = false;

    if (destinationFolder === undefined) {
      let folder: vscode.WorkspaceFolder | undefined = undefined;
      if (vscode.workspace.workspaceFolders?.length == 1) {
        folder = vscode.workspace.workspaceFolders[0];
      } else {
        folder = await vscode.window.showWorkspaceFolderPick({
          placeHolder: "Select a workspace folder to create the file in",
        });
      }
      if (folder === undefined) {
        return undefined;
      }

      destinationFolder = folder.uri;
      showSaveDialog = true;
    }

    const type = (
      await vscode.window.showQuickPick(
        [
          { description: "Robot Framework suite file", label: ".robot", picked: true, type: "robot" },
          { description: "Robot Framework resource file", label: ".resource", type: "resource" },
          {
            description: "Robot Framework suite init file",
            label: "__init__.robot",
            type: "init",
          },
        ],
        { title: "Select a Robot Framework file type", placeHolder: "Select a file type" },
      )
    )?.type;

    if (type === undefined) {
      return undefined;
    }

    let uri: vscode.Uri | undefined = undefined;

    if (type === "init") {
      uri = vscode.Uri.joinPath(destinationFolder, `__init__.robot`);
    } else {
      uri = vscode.Uri.joinPath(destinationFolder, `newfile.${type}`);
      let i = 1;
      while (await fs.pathExists(uri.fsPath)) {
        uri = vscode.Uri.joinPath(destinationFolder, `newfile-${i++}.${type}`);
      }
    }

    if (showSaveDialog) {
      uri = await vscode.window.showSaveDialog({
        defaultUri: uri,
        filters: { "Robot Framework": ["robot", "resource"] },
        title: "Create new Robot Framework file",
      });

      if (uri === undefined) {
        return;
      }
    }

    await fs.ensureFile(uri.fsPath);

    const doc = await vscode.workspace.openTextDocument(uri);

    await vscode.window.showTextDocument(doc);

    if (!showSaveDialog && type !== "init") {
      await vscode.commands.executeCommand("workbench.files.action.focusFilesExplorer");
      await vscode.commands.executeCommand("revealInExplorer", uri);
      await vscode.commands.executeCommand("renameFile", uri);
    }

    return doc;
  }

  private removeFolder(folder: vscode.WorkspaceFolder) {
    if (this._workspaceFolderLanguageStatuses.has(folder)) {
      this._workspaceFolderLanguageStatuses.delete(folder);
    }
  }

  dispose(): void {
    this._disposables.dispose();
  }

  // Starts the REPL as the terminal's own process, with the interpreter RobotCode uses for the folder and the settings
  // runs get. The terminal is created hidden and shown at once: the Python extensions activate every visible terminal
  // that opens by typing a command into it, which would end up as input of the REPL.
  private async startTerminalRepl(folder: vscode.WorkspaceFolder): Promise<void> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    if (this.languageClientsManager.isDisabledForFolder(folder)) {
      void vscode.window.showErrorMessage(
        config.get<boolean>("disableExtension")
          ? `RobotCode is switched off for the workspace folder '${folder.name}' by the setting robotcode.disableExtension.`
          : `RobotCode is switched off for the workspace folder '${folder.name}' for this session; RobotCode: Restart Language Servers switches it on again.`,
      );
      return;
    }

    // a known problem may be solved by now, for example by an install that the polling has not seen yet
    const usable =
      this.languageClientsManager.getRobotEnvironmentState(folder).state === "unusable"
        ? await this.languageClientsManager.checkRobotEnvironmentAgain(folder)
        : await this.languageClientsManager.isValidRobotEnvironmentInFolder(folder);
    const state = this.languageClientsManager.getRobotEnvironmentState(folder);
    if (!usable || state.executable === undefined) {
      void vscode.window.showErrorMessage(
        `Cannot start the Robot REPL for '${folder.name}': ${describeRobotEnvironmentProblem(state)}.`,
      );
      return;
    }

    const shellArgs = [
      "-u",
      "-X",
      "utf8",
      this.pythonManager.robotCodeMain,
      ...config.get<string[]>("extraArgs", []),
      ...config.get<string[]>("profiles", []).flatMap((profile) => ["-p", profile]),
      "repl",
      ...config.get<string[]>("robot.pythonPath", []).flatMap((entry) => ["-P", entry]),
      ...config.get<string[]>("robot.variableFiles", []).flatMap((file) => ["-V", file]),
      ...Object.entries(config.get<{ [key: string]: unknown }>("robot.variables", {})).flatMap(([name, value]) => [
        "-v",
        `${name}:${String(value)}`,
      ]),
    ];
    const env = Object.fromEntries(
      Object.entries(config.get<{ [key: string]: unknown }>("robot.env", {})).map(([name, value]) => [
        name,
        value === null ? null : String(value),
      ]),
    );

    const terminal = vscode.window.createTerminal({
      name: `Robot REPL${vscode.workspace.workspaceFolders?.length === 1 ? "" : ` (${folder.name})`}`,
      shellPath: state.executable,
      shellArgs,
      cwd: folder.uri,
      env,
      iconPath: new vscode.ThemeIcon("robotcode-robot"),
      hideFromUser: true,
      isTransient: true,
    });
    terminal.show();
  }

  async updateItems(editor?: vscode.TextEditor): Promise<void> {
    if (editor === undefined) {
      editor = vscode.window.activeTextEditor;
    }
    if (editor === undefined || !this.languageClientsManager.supportedLanguages.includes(editor.document.languageId)) {
      return;
    }

    const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);

    if (folder !== undefined && !this._workspaceFolderLanguageStatuses.has(folder)) {
      const info = await this.languageClientsManager.getProjectInfo(folder);
      if (info !== undefined) {
        this._workspaceFolderLanguageStatuses.set(folder, info);
      }
    }

    this.robotCode.command = {
      title: "Show Tool Menu",
      command: "robotcode.showToolMenu",
      tooltip: "Show RobotCode's Tool Menu",
      arguments: [folder],
    };

    const profiles = vscode.workspace
      .getConfiguration(CONFIG_SECTION, folder ?? vscode.window.activeTextEditor?.document)
      .get<string[]>(CONFIG_PROFILES);

    this.profiles.text = profiles && profiles.length > 0 ? `${profiles?.join(", ")}` : "None";
    this.profiles.detail = "Configuration Profiles";
    this.profiles.command = {
      title: "Select",
      command: "robotcode.selectConfigurationProfiles",
      arguments: [folder],
    };

    const projectInfo = folder !== undefined ? this._workspaceFolderLanguageStatuses.get(folder) : undefined;

    const environmentState =
      folder !== undefined ? this.languageClientsManager.getRobotEnvironmentState(folder) : undefined;
    const robotProblem = environmentState?.problem;
    const installedRobotVersion = environmentState?.robotVersion;

    // the version of the language server, else the one the environment check found; while Robot Framework cannot be
    // checked, because the interpreter has a problem or the first check runs, it is unknown
    this.robotVersion.text = `$(robotcode-robot) ${
      projectInfo?.robotVersionString ??
      (environmentState?.state === "usable" && installedRobotVersion !== undefined
        ? installedRobotVersion
        : robotProblem === "robotTooOld" && installedRobotVersion !== undefined
          ? `${installedRobotVersion} (not supported)`
          : robotProblem === "robotMissing"
            ? NOT_INSTALLED
            : UNKNOWN)
    }`;
    this.robotVersion.detail = `Robot Framework Version${
      robotProblem === "robotMissing"
        ? " - not installed in the Python environment"
        : robotProblem === "robotTooOld"
          ? " - RobotCode needs 5.0 or newer"
          : ""
    }`;

    if (isRobotFrameworkProblem(robotProblem)) {
      this.robotVersion.severity = LanguageStatusSeverity.Error;
    } else {
      this.robotVersion.severity = LanguageStatusSeverity.Information;
    }

    this.robocopVersion.text = `$(robotcode-robocop) ${projectInfo?.robocopVersionString ?? NOT_INSTALLED}`;
    this.robocopVersion.detail = "Robocop Version";

    const robocopEnabled = vscode.workspace
      .getConfiguration(CONFIG_SECTION, vscode.window.activeTextEditor?.document)
      .get<boolean>(CONFIG_ROBOCOP_ENABLED);

    this.robocopVersion.command = {
      title: robocopEnabled ? "Disable" : "Enable",
      command: robocopEnabled ? "robotcode.disableRoboCop" : "robotcode.enableRoboCop",
    };

    const pythonInfo = folder !== undefined ? await this.pythonManager.getPythonInfo(folder) : undefined;

    const pythonProblem =
      robotProblem !== undefined && !isRobotFrameworkProblem(robotProblem) ? robotProblem : undefined;

    // the Python side names a global interpreter with its version already, for example `Python 3.15.0`
    const pythonDescription =
      pythonInfo === undefined
        ? NOT_INSTALLED
        : pythonInfo.name.includes(pythonInfo.version)
          ? pythonInfo.name
          : `${pythonInfo.version} ${pythonInfo.name}`;
    this.pythonVersion.text = `$(robotcode-python) ${
      pythonProblem === "noInterpreter" ? "no interpreter selected" : pythonDescription
    }`;
    this.pythonVersion.detail = `Python Version${
      pythonProblem === "interpreterMissing"
        ? " - the interpreter no longer exists or cannot be started"
        : pythonProblem === "pythonTooOld"
          ? " - RobotCode needs 3.10 or newer"
          : ""
    }`;
    this.pythonVersion.command = {
      title: "Select Environment",
      command: "robotcode.selectPythonEnvironment",
      arguments: [folder],
      tooltip: pythonInfo?.path,
    };

    // a problem of the interpreter, which the detail names, or no interpreter at all; a missing Robot Framework marks
    // the Robot Framework item
    if (pythonProblem === undefined && pythonInfo !== undefined) {
      this.pythonVersion.severity = LanguageStatusSeverity.Information;
    } else {
      this.pythonVersion.severity = LanguageStatusSeverity.Error;
    }
  }
}
