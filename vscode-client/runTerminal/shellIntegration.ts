// The sequences of VS Code's shell integration (OSC 633) with which a run terminal marks each run as a command: VS Code
// then draws its command decoration, colored by the exit code, and offers copying the command line and the output.
// See https://code.visualstudio.com/docs/terminal/shell-integration#_vs-code-custom-sequences-osc-633-st

function osc(data: string): string {
  return `\x1b]633;${data}\x07`;
}

// tells VS Code that the sequences below come where they belong, which its sticky scroll requires
export const RICH_COMMAND_DETECTION = osc("P;HasRichCommandDetection=True");

export const PROMPT_START = osc("A");
export const COMMAND_START = osc("B");
export const COMMAND_EXECUTED = osc("C");

/** `value` escaped as VS Code's own `serializeVSCodeOscMessage` does: `\` doubled, `;` and up to 0x20 as `\xAB`. */
export function escapeOscValue(value: string): string {
  return value.replace(/[\\;\x00-\x20]/g, (char) =>
    char === "\\" ? "\\\\" : `\\x${char.charCodeAt(0).toString(16).padStart(2, "0")}`,
  );
}

/** The command line of the command, which VS Code shows and copies. */
export function commandLineSequence(commandLine: string): string {
  return osc(`E;${escapeOscValue(commandLine)}`);
}

/** The end of the command, with its exit code when there is one. */
export function commandFinished(exitCode: number | null): string {
  return osc(exitCode === null ? "D" : `D;${exitCode}`);
}
