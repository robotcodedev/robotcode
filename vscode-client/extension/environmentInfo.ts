// The versions of a workspace folder that a report about RobotCode, Robot Framework or Robocop needs, as a Markdown
// list whose lines are named like the fields of RobotCode's bug report template.
import type { ProjectInfo, RobotEnvironmentState } from "./languageclientsmanger";

export const NOT_INSTALLED = "not installed";
export const UNKNOWN = "unknown";

/**
 * The Robot Framework version of a folder as the language status shows it: the version of the folder's language
 * server, else what the check of the environment found. While the folder is in its startup phase (`provisional`), a
 * problem the check found isn't known yet.
 */
export function robotFrameworkVersionText(
  languageServerVersion: string | undefined,
  environment: RobotEnvironmentState | undefined,
  provisional: boolean,
): string {
  const problem = provisional ? undefined : environment?.problem;
  const found = environment?.robotVersion;

  return (
    languageServerVersion ??
    (environment?.state === "usable" && found !== undefined
      ? found
      : problem === "robotTooOld" && found !== undefined
        ? `${found} (not supported)`
        : problem === "robotMissing"
          ? NOT_INSTALLED
          : UNKNOWN)
  );
}

/** The Python version of a folder with the kind of its environment, without a name or a path. */
export function pythonVersionText(
  python: { readonly version: string; readonly kind?: string } | undefined,
  environment: RobotEnvironmentState | undefined,
  provisional: boolean,
): string {
  if (!provisional && environment?.problem === "noInterpreter") return "no interpreter selected";
  if (python === undefined) return UNKNOWN;
  return python.kind ? `${python.version} (${python.kind})` : python.version;
}

/** What the list of a folder is made of; the values of a folder are `undefined` where nothing is known. */
export interface EnvironmentInfoValues {
  readonly vscodeVersion: string;
  readonly appName: string;
  readonly remoteName?: string;
  /** The operating system as VS Code's own system information names it: type, architecture and release. */
  readonly os: string;
  readonly extensionVersion: string;
  /** The answer of the folder's language server. */
  readonly projectInfo?: ProjectInfo;
  readonly environment?: RobotEnvironmentState;
  /** Whether the folder is in its startup phase, in which a problem of its environment isn't known yet. */
  readonly provisional: boolean;
  readonly python?: { readonly version: string; readonly kind?: string };
}

/**
 * The list of the versions in `values`: the six lines of RobotCode's bug report template, and a line for the editor,
 * the remote or the language server's RobotCode where they say something.
 */
export function environmentInfoText(values: EnvironmentInfoValues): string {
  const { projectInfo } = values;
  const languageServerVersion = projectInfo?.robotCodeVersionString;
  const robocop =
    projectInfo === undefined
      ? UNKNOWN
      : projectInfo.robocopVersionString
        ? `robotframework-robocop==${projectInfo.robocopVersionString}`
        : "none";

  const lines: [string, string | undefined][] = [
    ["VS Code Version", values.vscodeVersion],
    // the Insiders build is VS Code too
    ["Editor", values.appName.startsWith("Visual Studio Code") ? undefined : values.appName],
    ["RobotCode Version", values.extensionVersion],
    [
      "RobotCode Language Server Version",
      languageServerVersion && languageServerVersion !== values.extensionVersion ? languageServerVersion : undefined,
    ],
    ["OS", values.os],
    ["Remote", values.remoteName],
    ["Python Version", pythonVersionText(values.python, values.environment, values.provisional)],
    [
      "RobotFramework Version",
      robotFrameworkVersionText(projectInfo?.robotVersionString, values.environment, values.provisional),
    ],
    ["Additional tools", robocop],
  ];

  return lines
    .filter(([, value]) => value !== undefined)
    .map(([name, value]) => `- ${name}: ${value}`)
    .join("\n");
}
