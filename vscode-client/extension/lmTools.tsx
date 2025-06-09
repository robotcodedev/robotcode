/* eslint-disable class-methods-use-this */
import * as vscode from "vscode";
import { LanguageClientsManager } from "./languageclientsmanger";

function resolveWorkspaceFolder(filepath?: string): vscode.WorkspaceFolder | undefined {
  if (!filepath) {
    return vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0] : undefined;
  }

  try {
    return vscode.workspace.getWorkspaceFolder(vscode.Uri.parse(filepath));
  } catch {
    return vscode.workspace.getWorkspaceFolder(vscode.Uri.file(filepath));
  }
}

interface GetLibraryInfoToolParamters {
  libraryName: string;
  resourcePath?: string;
}

export class GetLibraryInfoTool implements vscode.LanguageModelTool<GetLibraryInfoToolParamters> {
  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {}

  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GetLibraryInfoToolParamters>,
    token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelToolResult> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);

    if (!workspaceFolder) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart("No workspace folder found. Please open a Robot Framework project."),
      ]);
    }

    const libdoc = await this.languageClientsManager.getLibraryDocumentation(
      workspaceFolder,
      options.input.libraryName,
      token,
    );
    if (!libdoc) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(
          "Failed to retrieve library documentation. Ensure the Robot Framework extension is properly configured and the library is installed.",
        ),
      ]);
    }

    const keywords = libdoc.keywords
      ? libdoc.keywords.map((kw) => `- ${kw.name}${kw.signature}`)
      : [new vscode.LanguageModelTextPart("No keywords available.")];

    const initializers = libdoc.initializers
      ? libdoc.initializers.map((kw) => `- ${kw.name}${kw.signature}`)
      : [new vscode.LanguageModelTextPart("No keywords available.")];

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(libdoc.documentation ?? "No documentation available."),
      new vscode.LanguageModelTextPart(`## Initializers:\n${initializers.join("\n")}`),
      new vscode.LanguageModelTextPart(`## Keywords:\n${keywords.join("\n")}`),
    ]);
  }

  async prepareInvocation?(
    options: vscode.LanguageModelToolInvocationPrepareOptions<GetLibraryInfoToolParamters>,
    _token: vscode.CancellationToken,
  ): Promise<vscode.PreparedToolInvocation> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);
    if (!workspaceFolder) {
      return {
        invocationMessage: "No workspace folder found. Please open a Robot Framework project.",
      };
    }

    return {
      invocationMessage: `Retrieving Robot Framework Library details for library: '${options.input.libraryName}'`,
    };
  }
}

interface GetKeywordInfoToolParamters {
  keywordName: string;
  libraryName: string;
  resourcePath?: string;
}

export class GetKeywordInfoTool implements vscode.LanguageModelTool<GetKeywordInfoToolParamters> {
  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {}

  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GetKeywordInfoToolParamters>,
    token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelToolResult> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);

    if (!workspaceFolder) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart("No workspace folder found. Please open a Robot Framework project."),
      ]);
    }

    const keyword = await this.languageClientsManager.getKeywordDocumentation(
      workspaceFolder,
      options.input.libraryName,
      options.input.keywordName,
      token,
    );
    if (!keyword) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(
          "Failed to retrieve Keyword documentation. Ensure the Robot Framework extension is properly configured and the library is installed.",
        ),
      ]);
    }

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(
        `# Keyword: ${keyword.name}${keyword.signature}\n\n${keyword.documentation ?? "No documentation available."}`,
      ),
    ]);
  }

  async prepareInvocation?(
    options: vscode.LanguageModelToolInvocationPrepareOptions<GetKeywordInfoToolParamters>,
    _token: vscode.CancellationToken,
  ): Promise<vscode.PreparedToolInvocation> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);
    if (!workspaceFolder) {
      return {
        invocationMessage: "No workspace folder found. Please open a Robot Framework project.",
      };
    }

    return {
      invocationMessage: `Retrieving Robot Framework Keyword details for keyword: '${options.input.keywordName}' from library: '${options.input.libraryName}'`,
    };
  }
}

interface GetDocumentImportsToolParamters {
  resourcePath: string;
}

export class GetDocumentImportsTool implements vscode.LanguageModelTool<GetDocumentImportsToolParamters> {
  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {}

  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GetDocumentImportsToolParamters>,
    token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelToolResult> {
    vscode.workspace.textDocuments.forEach((doc) => {
      if (doc.uri.toString() === options.input.resourcePath) {
        vscode.window.showTextDocument(doc, { preview: true });
      }
    });
    const keyword = await this.languageClientsManager.getDocumentImports(options.input.resourcePath, true, token);

    return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify(keyword))]);
  }

  async prepareInvocation?(
    options: vscode.LanguageModelToolInvocationPrepareOptions<GetDocumentImportsToolParamters>,
    _token: vscode.CancellationToken,
  ): Promise<vscode.PreparedToolInvocation> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);
    if (!workspaceFolder) {
      return {
        invocationMessage: "No workspace folder found. Please open a Robot Framework project.",
      };
    }

    return {
      invocationMessage: `Retrieving Robot Framework Document Imports for '${options.input.resourcePath}'`,
    };
  }
}

interface GetEnvironmentDetailsParamters {
  resourcePath?: string;
}

export class GetEnvironmentDetails implements vscode.LanguageModelTool<GetEnvironmentDetailsParamters> {
  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {}

  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GetLibraryInfoToolParamters>,
    token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelToolResult> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);

    if (!workspaceFolder) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart("No workspace folder found. Please open a Robot Framework project."),
      ]);
    }

    const projectInfo = await this.languageClientsManager.getProjectInfo(workspaceFolder, token);
    if (!projectInfo) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(
          "Failed to retrieve project information. Ensure the Robot Framework extension is properly configured.",
        ),
      ]);
    }

    const message = [
      "# Environment Details",
      `**Workspace Folder:** ${workspaceFolder.name}`,
      `**Python Interpreter Version:** ${projectInfo.pythonVersionString || "Not set"}`,
      `**Python Executable:** ${projectInfo.pythonExecutable || "Not set"}`,
      `**Robot Framework Version:** ${projectInfo.robotVersionString || "Not installed"}`,
      `**RobotCode Version:** ${projectInfo.robotCodeVersionString || "Not set"}`,
      `**Robocop Version:** ${projectInfo.robocopVersionString || "Not installed"}`,
      `**Robotidy Version:** ${projectInfo.tidyVersionString || "Not installed"}`,
    ];
    return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(message.join("\n"))]);
  }

  async prepareInvocation?(
    options: vscode.LanguageModelToolInvocationPrepareOptions<GetLibraryInfoToolParamters>,
    _token: vscode.CancellationToken,
  ): Promise<vscode.PreparedToolInvocation> {
    const workspaceFolder = resolveWorkspaceFolder(options.input.resourcePath);
    if (!workspaceFolder) {
      return {
        invocationMessage: "No workspace folder found. Please open a Robot Framework project.",
      };
    }

    return {
      invocationMessage: "Retrieving Robot Framework environment details",
    };
  }
}
