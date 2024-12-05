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
    outfile: "out/extension.js",
    external: ["vscode"],
  },
  {
    entryPoints: ["./vscode-client/rendererHtml"],
    format: "esm",
    platform: "browser",
    outfile: "out/rendererHtml.js",
    external: ["vscode"],
    loader: {
      ".jstemp": "text",
      ".csstemp": "text",
    },
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
