// The text that a run terminal shows before a run, with the sequences of VS Code's shell integration (OSC 633) that
// mark the run as a command: VS Code then draws its command decoration, colored by the exit code, and offers copying
// the command line and the output. The run terminal's script writes the end of the command itself.
// See https://code.visualstudio.com/docs/terminal/shell-integration#_vs-code-custom-sequences-osc-633-st

function osc(data: string): string {
  return `\x1b]633;${data}\x07`;
}

const PROMPT_START = osc("A");
const COMMAND_START = osc("B");
const COMMAND_EXECUTED = osc("C");

// marks a line of the terminal itself, as VS Code marks its own: " * " in inverse video
const MARK = "\x1b[0m\x1b[7m * \x1b[0m ";

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

/**
 * The text before a run whose full command line is `fullLine`, showing the command line `shownLine`.
 *
 * The command line comes first, as a shell terminal shows the typed command, and is the command of VS Code's shell
 * integration, so that it gets VS Code's decoration with its menu. The mark and "Executing: " are the prompt. The
 * command line goes once more after the start of the output: VS Code reads the command from the screen at that point,
 * and only a command line sent after it wins over that without the nonce that VS Code gives its own shells.
 * VS Code shows the shown line and copies the full one with Copy Command.
 */
export function runHeader(shownLine: string, fullLine: string): string {
  return `${PROMPT_START}${MARK}Executing: ${COMMAND_START}${shownLine}\r\n${COMMAND_EXECUTED}${commandLineSequence(fullLine)}`;
}
