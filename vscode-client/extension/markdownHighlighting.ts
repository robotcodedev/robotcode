import * as fs from "fs";
import { createHighlighterCoreSync, type HighlighterCore, type ThemeRegistrationRaw } from "shiki/core";
import { createJavaScriptRegexEngine } from "shiki/engine/javascript";
import * as vscode from "vscode";

// markdown-it passes the first word of the info string of a fenced code block as its language
const ROBOT_LANGUAGES = new Set(["robotframework", "robot"]);

// a theme without colors: the classes come from the scopes of the tokens
const SCOPES_THEME: ThemeRegistrationRaw = { name: "robotcode-scopes", settings: [] };

// For each token, the innermost scope that starts with one of these prefixes decides the class. The classes are
// the ones that the highlight.css of VS Code's Markdown preview colors.
const SCOPE_CLASSES: [prefix: string, cssClass: string][] = [
  ["keyword.other.header", "hljs-section"],
  ["entity.name.function.testcase.name", "hljs-title"],
  ["entity.name.function.keyword.name", "hljs-title"],
  ["entity.name.function.keyword-call", "hljs-built_in"],
  ["keyword.control.settings", "hljs-keyword"],
  ["keyword.control.flow", "hljs-keyword"],
  ["keyword.other.var", "hljs-keyword"],
  ["variable.name", "hljs-variable"],
  ["punctuation.definition.variable", "hljs-variable"],
  ["punctuation.definition.envvar", "hljs-variable"],
  ["punctuation.definition.expression", "hljs-variable"],
  ["comment", "hljs-comment"],
  ["constant.numeric", "hljs-number"],
  ["keyword.operator.continue", "hljs-meta"],
];

type Highlight = (code: string, lang: string, attrs: string) => string;

interface MarkdownIt {
  options: { highlight?: Highlight | null };
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function scopeClass(scopes: string[]): string | undefined {
  for (let i = scopes.length - 1; i >= 0; i--) {
    const scope = scopes[i];
    const entry = SCOPE_CLASSES.find(([prefix]) => scope === prefix || scope.startsWith(`${prefix}.`));
    if (entry) return entry[1];
  }
  return undefined;
}

// one line of code as HTML; neighbouring parts with the same class share one span, `${x}` is three tokens
function lineHtml(parts: { content: string; cssClass: string | undefined }[]): string {
  const merged: { content: string; cssClass: string | undefined }[] = [];
  for (const part of parts) {
    const last = merged.at(-1);
    if (last !== undefined && last.cssClass === part.cssClass) last.content += part.content;
    else merged.push({ ...part });
  }
  return merged
    .map(({ content, cssClass }) =>
      cssClass ? `<span class="${cssClass}">${escapeHtml(content)}</span>` : escapeHtml(content),
    )
    .join("");
}

/**
 * The `extendMarkdownIt` of VS Code's Markdown extension: Robot Framework code blocks get the `hljs-*` classes of
 * RobotCode's TextMate grammar, all other code blocks keep the highlighting of the Markdown extension.
 */
export function createExtendMarkdownIt(grammarPath: string, outputChannel: vscode.OutputChannel) {
  let highlighter: HighlighterCore | undefined;
  let failed = false;

  function highlightRobot(code: string): string | undefined {
    if (failed) return undefined;
    try {
      // created on first use, so that activating the extension does not pay for it
      highlighter ??= createHighlighterCoreSync({
        themes: [SCOPES_THEME],
        langs: [JSON.parse(fs.readFileSync(grammarPath, "utf8"))],
        engine: createJavaScriptRegexEngine(),
      });
      return highlighter
        .codeToTokensBase(code, { lang: "robotframework", theme: SCOPES_THEME.name, includeExplanation: "scopeName" })
        .map((line) =>
          lineHtml(
            line
              .flatMap((token) => token.explanation ?? [{ content: token.content, scopes: [] }])
              .map(({ content, scopes }) => ({ content, cssClass: scopeClass(scopes.map((s) => s.scopeName)) })),
          ),
        )
        .join("\n");
    } catch (error) {
      failed = true;
      outputChannel.appendLine(`Robot Framework code blocks in Markdown are not highlighted: ${String(error)}`);
      return undefined;
    }
  }

  return (md: MarkdownIt): MarkdownIt => {
    const original = md.options.highlight;
    md.options.highlight = (code, lang, attrs) => {
      if (code && ROBOT_LANGUAGES.has(lang?.toLowerCase())) {
        const html = highlightRobot(code);
        if (html !== undefined) return html;
      }
      return original ? original(code, lang, attrs) : "";
    };
    return md;
  };
}
