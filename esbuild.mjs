import * as esbuild from "esbuild";
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

    ...project,

    plugins: [
      typecheckPlugin({ configFile: project.entryPoints[0] + "/tsconfig.json" }),
      /* add to the end of plugins array */
      //esbuildProblemMatcherPlugin,
    ],
  });

  await ctx.rebuild();
  await ctx.dispose();
}

async function main() {
  for (const project of projects) {
    await buildProject(project);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
