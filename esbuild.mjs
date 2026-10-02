import * as esbuild from "esbuild";
import * as fs from "fs";
import * as path from "path";
import * as process from "process";
import { typecheckPlugin } from "@jgoz/esbuild-plugin-typecheck";
/**
 * @type {import('esbuild').LogLevel}
 */
const LOG_LEVEL = "error";

/**
 * @type {boolean}
 */
const production = process.argv.includes("--production");

/**
 * @type {import('esbuild').BuildOptions[]}
 */
const projects = [
  {
    entryPoints: ["./vscode-client/extension"],
    format: "cjs",
    platform: "node",
    // The extension runs in the Node.js of VS Code's Electron, not in the one that builds it.
    target: "node24",
    outfile: "out/extension.js",
    external: ["vscode"],
  },
  {
    entryPoints: ["./vscode-client/rendererLog"],
    format: "esm",
    platform: "browser",
    outfile: "out/rendererLog.js",
    external: ["vscode"],
    loader: {
      ".ttf": "file",
      ".css": "text",
    },
  },
  {
    // The page of the Documentation Viewer; codicon.css is linked by the page, as vscode-elements expects.
    entryPoints: [
      "./vscode-client/documentationViewer",
      "./vscode-client/documentationViewer/viewer.css",
      "./node_modules/@vscode/codicons/dist/codicon.css",
    ],
    format: "esm",
    platform: "browser",
    outdir: "out/documentationViewer",
    entryNames: "[name]",
    loader: {
      ".ttf": "file",
    },
  },
];

/**
 *
 * @param {import('esbuild').BuildOptions} project
 */
async function buildProject(project) {
  const ctx = await esbuild.context({
    bundle: true,
    minify: production,
    sourcemap: !production,
    sourcesContent: false,
    logLevel: LOG_LEVEL,
    // for the third-party notices
    metafile: production,

    ...project,

    plugins: [
      typecheckPlugin({ configFile: project.entryPoints[0] + "/tsconfig.json" }),
      /* add to the end of plugins array */
      //esbuildProblemMatcherPlugin,
    ],
  });

  const result = await ctx.rebuild();
  await ctx.dispose();
  return result.metafile;
}

/**
 * The directory of the npm package a file of a build comes from, by the last `node_modules` in its path.
 *
 * @param {string} file
 */
function packageDirectory(file) {
  const parts = file.split(/[\\/]/);
  const index = parts.lastIndexOf("node_modules");
  if (index < 0 || index + 1 >= parts.length) return undefined;
  return parts.slice(0, index + (parts[index + 1].startsWith("@") ? 3 : 2)).join("/");
}

/**
 * Writes `out/ThirdPartyNotices.txt`: name, version, licence and licence texts of every npm package with files in
 * the bundles or among their assets.
 *
 * @param {import('esbuild').Metafile[]} metafiles
 */
function writeThirdPartyNotices(metafiles) {
  const directories = new Set();
  for (const metafile of metafiles) {
    for (const file of Object.keys(metafile.inputs)) {
      const directory = packageDirectory(file);
      if (directory !== undefined) directories.add(directory);
    }
  }

  const entries = [...directories]
    .map((directory) => {
      const manifest = JSON.parse(fs.readFileSync(path.join(directory, "package.json"), "utf8"));
      const license = typeof manifest.license === "string" ? manifest.license : (manifest.license?.type ?? "");
      const texts = fs
        .readdirSync(directory)
        .filter((name) => /^(licen[cs]e|copying|notice)([-._].*)?$/i.test(name))
        .sort()
        .map((name) => fs.readFileSync(path.join(directory, name), "utf8").trim());
      return { name: manifest.name, version: manifest.version, license, homepage: manifest.homepage, texts };
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  const separator = "=".repeat(80);
  const text = [
    "Third-party notices",
    "",
    "The RobotCode extension for VS Code includes the following open source software. Its licences and notices follow.",
    ...entries.flatMap((entry) => [
      "",
      separator,
      `${entry.name} ${entry.version}${entry.license ? ` (${entry.license})` : ""}`,
      ...(entry.homepage ? [entry.homepage] : []),
      separator,
      ...entry.texts.flatMap((license) => ["", license]),
    ]),
    "",
  ].join("\n");
  fs.writeFileSync("out/ThirdPartyNotices.txt", text);
}

async function main() {
  // Files of earlier builds, such as source maps of a development build, would be packaged too.
  if (production) fs.rmSync("out", { recursive: true, force: true });

  const metafiles = [];
  for (const project of projects) {
    metafiles.push(await buildProject(project));
  }

  if (production) writeThirdPartyNotices(metafiles);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
