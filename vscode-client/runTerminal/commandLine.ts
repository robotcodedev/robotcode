// The command line that a run terminal shows before a run: the program and its arguments, each quoted when a shell
// of the platform would read it otherwise.

// what a POSIX shell takes as a plain word, as Python's shlex.quote
const POSIX_PLAIN = /^[\w@%+=:,./-]+$/;

// what cmd.exe or PowerShell would read in an unquoted argument
const WINDOWS_SPECIAL = /[\s"&|<>^%!()`';,]/;

/** `arg` in single quotes when a POSIX shell would read it, as Python's `shlex.quote` does. */
export function quotePosix(arg: string): string {
  return POSIX_PLAIN.test(arg) ? arg : `'${arg.replace(/'/g, `'"'"'`)}'`;
}

/** `arg` in double quotes when a Windows shell would read it, with quotes and backslashes as Windows programs read them. */
export function quoteWindows(arg: string): string {
  if (arg !== "" && !WINDOWS_SPECIAL.test(arg)) return arg;
  return `"${arg.replace(/(\\*)"/g, '$1$1\\"').replace(/(\\+)$/, "$1$1")}"`;
}

/** The program and its arguments `args` in one line, quoted for the shells of `platform`. */
export function commandLine(args: readonly string[], platform: NodeJS.Platform = process.platform): string {
  const quote = platform === "win32" ? quoteWindows : quotePosix;
  return args.map(quote).join(" ");
}
