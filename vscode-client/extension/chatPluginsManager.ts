import * as vscode from "vscode";
import {
  CHAT_CONFIG_SECTION,
  CHAT_PLUGINS_MARKETPLACE_ID,
  CHAT_PLUGINS_MARKETPLACES,
  CONFIG_AI_ENABLE_CHAT_PLUGINS,
  CONFIG_SECTION,
  CONTEXT_CHAT_PLUGINS_MARKETPLACE_REGISTERED,
} from "./config";

// Forms of the marketplace reference we recognize when checking/removing an
// existing entry: the `owner/repo` shorthand plus the common git-URL variants.
const MARKETPLACE_ALIASES = [
  CHAT_PLUGINS_MARKETPLACE_ID,
  `https://github.com/${CHAT_PLUGINS_MARKETPLACE_ID}`,
  `https://github.com/${CHAT_PLUGINS_MARKETPLACE_ID}.git`,
  `git@github.com:${CHAT_PLUGINS_MARKETPLACE_ID}`,
  `git@github.com:${CHAT_PLUGINS_MARKETPLACE_ID}.git`,
].map((s) => s.toLowerCase());

export class ChatPluginsManager implements vscode.Disposable {
  private readonly _disposables: vscode.Disposable;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this._disposables = vscode.Disposable.from(
      vscode.commands.registerCommand("robotcode.chatPlugins.addMarketplace", () => this.addMarketplace()),
      vscode.commands.registerCommand("robotcode.chatPlugins.removeMarketplace", () => this.removeMarketplace()),
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration(`${CHAT_CONFIG_SECTION}.${CHAT_PLUGINS_MARKETPLACES}`)) {
          ChatPluginsManager.updateContextKey();
        }
      }),
    );

    ChatPluginsManager.updateContextKey();
  }

  private static readMarketplaces(): string[] {
    return vscode.workspace.getConfiguration(CHAT_CONFIG_SECTION).get<string[]>(CHAT_PLUGINS_MARKETPLACES, []);
  }

  private static matchesOurMarketplace(entry: string): boolean {
    return MARKETPLACE_ALIASES.includes(entry.trim().toLowerCase());
  }

  private static isRegistered(list: string[]): boolean {
    return list.some((entry) => ChatPluginsManager.matchesOurMarketplace(entry));
  }

  private static isBundledPluginEnabled(): boolean {
    return vscode.workspace.getConfiguration(CONFIG_SECTION).get<boolean>(CONFIG_AI_ENABLE_CHAT_PLUGINS, true);
  }

  private static updateContextKey(): void {
    void vscode.commands.executeCommand(
      "setContext",
      CONTEXT_CHAT_PLUGINS_MARKETPLACE_REGISTERED,
      ChatPluginsManager.isRegistered(ChatPluginsManager.readMarketplaces()),
    );
  }

  private async writeMarketplaces(list: string[]): Promise<boolean> {
    try {
      await vscode.workspace
        .getConfiguration(CHAT_CONFIG_SECTION)
        .update(CHAT_PLUGINS_MARKETPLACES, list, vscode.ConfigurationTarget.Global);
      ChatPluginsManager.updateContextKey();
      return true;
    } catch (error) {
      this.outputChannel.appendLine(`Failed to update ${CHAT_CONFIG_SECTION}.${CHAT_PLUGINS_MARKETPLACES}: ${error}`);
      await vscode.window.showErrorMessage(
        `Could not update the chat plugin marketplaces setting. This requires GitHub Copilot Chat (or another agent that provides "${CHAT_CONFIG_SECTION}.${CHAT_PLUGINS_MARKETPLACES}") to be installed.`,
      );
      return false;
    }
  }

  private async addMarketplace(): Promise<void> {
    const list = ChatPluginsManager.readMarketplaces();
    if (ChatPluginsManager.isRegistered(list)) {
      await vscode.window.showInformationMessage("The RobotCode chat plugins marketplace is already added.");
      return;
    }

    if (!(await this.writeMarketplaces([...list, CHAT_PLUGINS_MARKETPLACE_ID]))) {
      return;
    }

    if (!ChatPluginsManager.isBundledPluginEnabled()) {
      await vscode.window.showInformationMessage(
        `Added the RobotCode chat plugins marketplace (${CHAT_PLUGINS_MARKETPLACE_ID}).`,
      );
      return;
    }

    // The extension already bundles this plugin, so installing it from the
    // marketplace would run two copies. Offer to switch the bundled one off.
    const disable = "Disable Bundled Plugin";
    const choice = await vscode.window.showInformationMessage(
      `Added the RobotCode chat plugins marketplace (${CHAT_PLUGINS_MARKETPLACE_ID}). The extension also bundles this plugin — if you install it from the marketplace, disable the bundled copy to avoid running it twice.`,
      disable,
    );
    if (choice === disable) {
      await vscode.workspace
        .getConfiguration(CONFIG_SECTION)
        .update(CONFIG_AI_ENABLE_CHAT_PLUGINS, false, vscode.ConfigurationTarget.Global);
    }
  }

  private async removeMarketplace(): Promise<void> {
    const list = ChatPluginsManager.readMarketplaces();
    if (!ChatPluginsManager.isRegistered(list)) {
      await vscode.window.showInformationMessage("The RobotCode chat plugins marketplace is not added.");
      return;
    }

    const next = list.filter((entry) => !ChatPluginsManager.matchesOurMarketplace(entry));
    if (await this.writeMarketplaces(next)) {
      await vscode.window.showInformationMessage("Removed the RobotCode chat plugins marketplace.");
    }
  }

  dispose(): void {
    this._disposables.dispose();
  }
}
