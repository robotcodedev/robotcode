// Generates the Starlight content of the preview from ../docs. Runs before every `npm run dev` and
// `npm run build`; its output (src/content/docs/, src/assets/, public/, .generated/) is git-ignored.
// Content is edited in docs/ only. A new page in docs/ needs an entry in PAGES below.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import GithubSlugger from "github-slugger";
import { dump, load } from "js-yaml";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.dirname(ROOT);
const SRC = path.join(REPO, "docs");
const CONTENT = path.join(ROOT, "content");
const OUT = path.join(ROOT, "src/content/docs");
const ASSETS = path.join(ROOT, "src/assets");
const PUBLIC = path.join(ROOT, "public");
const GENERATED = path.join(ROOT, ".generated");
const SITE = "https://robotcode.io";
const EDIT_URL = "https://github.com/robotcodedev/robotcode/edit/main/";

// Page map: every Markdown file under docs/ (path relative to docs/) -> page of the preview.
//   id           page id, the URL path without slashes
//   title        replaces the title of the source (else its frontmatter title, else its H1)
//   label/order  sidebar label and position; the gaps leave room for planned pages
//   description  meta description; one sentence
//   tags         news posts: exactly one kind tag (release, april-fools, tips) plus a topic tag for each topic the
//                post has its own section about: analysis, editor, vscode, intellij, cli, configuration, ci,
//                debugging, ai-agents, performance
//   excerpt      news posts whose first paragraph does not work as excerpt
//   steps        first items of ordered lists that are procedures; rendered as <Steps>
//   moveSections headings whose sections move to another page (at its `{/* sections */}` marker)
//   notice       aside put in front of the content
//   replacedBy   the file is not converted: a hand-written page in content/ or starlight-blog replaces it
// Release posts named news/YYYY-MM-DD-whats-new-vX.Y.Z.md need no entry (see releasePost()).
const PAGES = {
  "index.md": { id: "", replacedBy: "content/index.mdx" },
  "01_about/index.md": {
    id: "about",
    label: "About",
    description:
      "Overview of what RobotCode offers for Robot Framework in VS Code, IntelliJ and on the command line: completion, navigation, diagnostics, debugging, REPL.",
  },
  "02_get_started/index.md": {
    id: "getting-started/vscode",
    title: "Get Started with VS Code",
    label: "VS Code",
    order: 10,
    description:
      "Install the RobotCode extension for VS Code, set up a Python virtual environment with Robot Framework, select the interpreter and run your first test.",
    moveSections: { Requirements: "getting-started" },
    steps: [
      /^Open Visual Studio Code\./,
      /^Right-click on the RobotCode extension/,
      /^Open the Command Palette/,
      /^Create a virtual environment/,
      /^Open the terminal in Visual Studio Code/,
    ],
  },
  "04_tip_and_tricks/04_neovim_lsp_setup.md": {
    id: "getting-started/neovim",
    label: "Neovim",
    order: 30,
    description:
      "Use the RobotCode language server in Neovim 0.11+ without Mason import errors, via a project-local install or a global install with PYTHONPATH set.",
  },
  "02_get_started/configuration.md": {
    id: "getting-started/configuration",
    label: "Configuration",
    order: 90,
    description:
      "Set up robot.toml for your Robot Framework project: core settings, profiles with inheritance and precedence, running tests and config file loading order.",
  },
  "04_tip_and_tricks/index.md": { id: "guides", replacedBy: "content/guides/index.mdx" },
  "03_reference/discovering-tests.md": {
    id: "guides/discovering-tests",
    label: "Discovering Tests",
    order: 10,
    description:
      "List the suites, tests, tasks, tags and source files Robot Framework would pick up with robotcode discover, without running anything, as a tree or as JSON.",
  },
  "03_reference/analyzing-code.md": {
    id: "guides/analyzing-code",
    label: "Analyzing Code",
    order: 20,
    description:
      "Run static analysis with robotcode analyze code, tune severities and exit codes, and produce JSON, SARIF, GitHub or GitLab reports for CI pipelines.",
  },
  "03_reference/analyzing-results.md": {
    id: "guides/analyzing-results",
    label: "Analyzing Results",
    order: 30,
    description:
      "Summarize, list, walk, aggregate and diff Robot Framework run results with robotcode results in the terminal or CI, using filters, search and JSON output.",
  },
  "03_reference/repl.md": {
    id: "guides/repl",
    label: "REPL",
    order: 40,
    description:
      "Call Robot Framework keywords line by line in robotcode repl: import libraries, keep variables across lines, run REPL scripts, capture a log and debug.",
  },
  "03_reference/robot-debug.md": {
    id: "guides/robot-debug",
    label: "Command-line Debugging",
    order: 50,
    description:
      "Debug Robot Framework suites in the terminal with robotcode robot-debug: break on a line, keyword or failure, step, and inspect the stack and variables.",
  },
  "03_reference/wrapper.md": {
    id: "guides/wrapper",
    label: "Wrapper",
    order: 110,
    description:
      "Run tests through a wrapper command like xvfb-run or your own script, set in robot.toml or on the CLI, to bring the test environment up and tear it down.",
  },
  "03_reference/ignoring-files.md": {
    id: "guides/ignoring-files",
    label: ".robotignore",
    order: 120,
    description:
      "Keep build output, dependencies and other folders out of discovery, analysis and the language server using gitignore-style patterns in .robotignore.",
  },
  "03_reference/ai-agents.md": {
    id: "guides/ai-agents",
    label: "AI Agents",
    order: 130,
    description:
      "Set up the RobotCode chat plugin for Copilot Chat, Claude Code and other agents so they run, discover, debug and inspect tests via the robotcode CLI.",
  },
  "04_tip_and_tricks/01_avoiding_a_global_resource_file.md": {
    id: "guides/avoid-global-resource-file",
    label: "Avoid a Global Resource File",
    order: 210,
    description:
      "Why one catch-all resource file causes circular imports, ambiguous keywords and slow analysis, how to modularize it, and how to suppress the warnings.",
    steps: [/^\*\*Analyze usage patterns\*\*/],
  },
  "04_tip_and_tricks/02_why_variable_not_found.md": {
    id: "guides/variable-not-found",
    label: "Variable Not Found",
    order: 220,
    description:
      "Why RobotCode's static analysis flags VariableNotFound for variables that work at runtime, and how Variables sections, defaults and RETURN avoid it.",
  },
  "04_tip_and_tricks/03_vscode_customizations.md": {
    id: "guides/vscode-highlighting",
    label: "VS Code Highlighting",
    order: 230,
    description:
      "Add token color rules to VS Code settings.json to set font styles for Robot Framework keywords, test case names, section headers and documentation.",
    steps: [/^Open your VSCode user settings/],
  },
  "03_reference/index.md": { id: "reference", replacedBy: "content/reference/index.mdx" },
  "03_reference/cli.md": {
    id: "reference/cli",
    label: "CLI",
    order: 1,
    description:
      "All robotcode commands and options, from robot, rebot and discover to analyze, debug, repl and results, and which package to install for each.",
    // The commands sit at H3 to H6.
    frontmatter: { tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 6 } },
  },
  "03_reference/config.md": {
    id: "reference/config",
    label: "robot.toml",
    order: 2,
    description:
      "Every robot.toml setting with its type and examples: profiles, robot, rebot, libdoc and testdoc options, and the tool.robotcode-analyze settings.",
    // The JSON schema links to these anchors (scripts/create_robot_toml_json_schema.py).
    explicitIds: true,
  },
  "03_reference/diagnostics-modifiers.md": {
    id: "reference/diagnostics-modifiers",
    label: "Diagnostic Modifiers",
    order: 3,
    description:
      "Use robotcode: comments to ignore diagnostics or change their severity per line, block or file, or set the same rules project-wide in robot.toml.",
  },
  "05_contributing/index.md": {
    id: "contributing",
    label: "Support & Contribute",
    description:
      "Ways to support RobotCode: sponsor it on Open Collective or GitHub Sponsors, or contribute code, documentation, bug reports, feedback and community help.",
  },
  "news/index.md": { id: "news", replacedBy: "starlight-blog" },
  "news/2026-03-31-whats-new-v2.5.0.md": {
    id: "news/v2-5-0",
    tags: ["release", "performance", "analysis", "editor", "cli"],
    description:
      "RobotCode 2.5.0 adds a persistent analysis cache and faster keyword matching, plus Literal completion, CLI unused keyword checks and cache commands.",
  },
  "news/2026-04-01-whats-new-v2.5.0.md": {
    id: "news/v2-5-0-april-1st",
    tags: ["april-fools"],
    description:
      "April Fools version of the 2.5.0 notes with made-up features like predictive caching and emotional code completion, plus a link to the real release.",
    excerpt:
      "Happy April 1st! The April Fools' edition of the v2.5.0 release notes: predictive analysis caching, a proactive performance mode, emotional code completion and a keyword adoption program. None of them exist.",
    notice: [
      ":::caution[April Fools' joke]",
      "This post is an April Fools' joke: none of the features it describes exist. The real release notes are in [What's New in v2.5.0](/news/v2-5-0/).",
      ":::",
    ],
  },
  "news/2026-04-02-whats-new-v2.5.1.md": {
    id: "news/v2-5-1",
    tags: ["release", "analysis", "editor"],
    description:
      "RobotCode 2.5.1 fixes false VariableNotFound diagnostics for templates with embedded arguments, multi-word BDD prefix matching, and CURDIR on Windows.",
  },
  "news/2026-06-09-whats-new-v2.6.0.md": {
    id: "news/v2-6-0",
    tags: ["release", "cli", "analysis", "ci", "debugging", "ai-agents", "editor", "vscode"],
    description:
      "RobotCode 2.6.0 adds the results command, CI-ready analysis reports, a CLI debugger, chat plugins for AI agents, and an experimental SemanticModel preview.",
    excerpt:
      "**RobotCode** v2.6.0 builds out a Robot Framework project's command line: project-aware commands discover tests, inspect finished runs, check code, explore keyword documentation and debug a run. A first version of chat plugins lets AI agents drive the `robotcode` CLI, and the release introduces the first experimental SemanticModel preview.",
  },
  "news/2026-06-15-whats-new-v2.6.2.md": {
    id: "news/v2-6-2",
    tags: ["release", "vscode", "analysis", "configuration"],
    description:
      "Bug fixes in 2.6.1 and 2.6.2: the Test Explorer recovers after server restarts, corrupt caches rebuild, and stale profiles no longer block test runs.",
  },
  "news/2026-07-15-whats-new-v2.7.0.md": {
    id: "news/v2-7-0",
    tags: ["release", "configuration", "cli", "analysis", "vscode"],
    description:
      "RobotCode 2.7.0 adds a wrapper option to run tests inside a prepared environment, makes the analysis cache reliable, and fixes Test Explorer subset runs.",
  },
};

// Release posts without a page-map entry: tagged `release`, excerpt after the first paragraph.
const RELEASE_POST = /^news\/\d{4}-\d{2}-\d{2}-whats-new-v(\d+)\.(\d+)\.(\d+)\.md$/;
function releasePost(rel) {
  const m = RELEASE_POST.exec(rel);
  return m && { id: `news/v${m[1]}-${m[2]}-${m[3]}`, tags: ["release"], automatic: true };
}

// Static files served unchanged, and images and screen recordings of the hand-written pages (target in src/assets/ ->
// source in docs/).
const PUBLIC_FILES = ["robotcode-logo.svg", "robotcode-logo-mini.png", "robotcode-logo.jpg", "schemas/robot.toml.json"];
const HANDWRITTEN_ASSETS = {
  "robotcode-logo.svg": "public/robotcode-logo.svg",
  "screenshots/autocomplete1.mp4": "images/autocomplete1.mp4",
  "screenshots/running-tests.mp4": "images/running_tests.mp4",
  "screenshots/neovim-diagnostics.png": "images/neovim-diagnostics.png",
  "screenshots/neovim-completion.png": "images/neovim-completion.png",
  "screenshots/neovim-inlayhints.png": "images/neovim-inlayhints.png",
  "screenshots/neovim-references.png": "images/neovim-references.png",
  "logos/imbus.svg": "images/imbus-web-logo.svg",
  "logos/rf-foundation.svg": "images/RFFoundation.svg",
  "logos/jetbrains.svg": "images/jetbrains.svg",
};
// The pictures of the home page (the ones docs/.vitepress/theme/components/RandomHeroImage.vue shows).
const HERO_PICTURES = ["toy-tray", "vintage", "vintage-new", "golf", "rock", "soccer", "max", "playmo", "rise"];

const ASIDE = { tip: "tip", info: "note", note: "note", warning: "caution", danger: "danger" };
const FENCE = /^(\s*)(```+|~~~+)\s*([\w+-]*)\s*(?:\[([^\]]+)\])?\s*(.*)$/;
const CONTAINER_OPEN = /^(\s*):::\s*(tip|info|note|warning|danger|details|code-group|tabs)\b\s*(.*)$/;
const CONTAINER_CLOSE = /^\s*:::\s*$/;
const HEADING = /^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$/;
const SECTIONS_MARKER = "{/* sections */}";

const warnings = [];
const stats = { pages: 0, mdx: 0, images: 0, links: 0, anchors: 0 };

// ---- helpers ----

const route = (id) => (id ? `/${id}/` : "/");
const isFenceEnd = (line, fence) => line.trim().startsWith(fence) && /^[`~]+$/.test(line.trim());
const headingText = (s) =>
  s
    .replace(/\s*\{#[^}]*\}\s*$/, "")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/`/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\*\*|__/g, "")
    .trim();
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
// VitePress' slugify, used only to recognize the anchors of the current site.
const vitepressSlug = (s) =>
  s
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[\s~`!@#$%^&*()\-_+=[\]{}|\\;:"'“”‘’<>,.?/]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/^(\d)/, "_$1")
    .toLowerCase();
// Same rule as _to_anchor() in scripts/create_robot_toml_json_schema.py.
const schemaAnchor = (s) =>
  s
    .trim()
    .toLowerCase()
    .replace(/\./g, "-")
    .replace(/[^\w\s-]/g, "")
    .replace(/[-\s]+/g, "-")
    .replace(/^-+|-+$/g, "");
const jsxAttr = (v) => (/["{}<>]/.test(v) ? `{${JSON.stringify(v)}}` : `"${v}"`);

function git(...args) {
  try {
    return execFileSync("git", args, { cwd: REPO, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}
// In a shallow clone every file would get the date of the newest commit, so pages get no date there.
const FULL_HISTORY = git("rev-parse", "--is-shallow-repository") === "false";
function lastChange(...files) {
  const date = FULL_HISTORY ? git("log", "-1", "--format=%cs", "--", ...files) : "";
  return date ? new Date(date) : undefined;
}

function splitFrontmatter(raw) {
  const m = /^---\n([\s\S]*?)\n---\n/.exec(raw);
  return m ? { fm: load(m[1]) ?? {}, body: raw.slice(m[0].length) } : { fm: {}, body: raw };
}

function findMarkdown(dir, rel = "") {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    if (["node_modules", ".vitepress", "public"].includes(e.name)) return [];
    const r = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) return findMarkdown(path.join(dir, e.name), r);
    return /\.mdx?$/.test(e.name) ? [r] : [];
  });
}

// ---- pass 0: page map and restructuring ----

const pages = new Map(); // docs-relative path -> page entry
const unmapped = [];
for (const rel of findMarkdown(SRC)) {
  const page = PAGES[rel] ?? releasePost(rel);
  if (page) pages.set(rel, page);
  else unmapped.push(rel);
}
if (unmapped.length) {
  fail(
    unmapped.map((rel) => `docs/${rel}: no entry in the page map (PAGES in docs-next/scripts/convert.mjs)`),
    "Every page in docs/ needs a page-map entry; see docs-next/README.md.",
  );
}
for (const rel of Object.keys(PAGES)) if (!pages.has(rel)) warnings.push(`page map entry without file: docs/${rel}`);

// Removes the H1, demotes further top-level headings with their subtrees, cuts out moved sections and
// adds the explicit heading IDs. Works on the VitePress source, so later passes see the final headings.
function restructure(rel, page, lines) {
  const out = [];
  const moved = {};
  let h1 = null;
  let shift = 0;
  let moving = null;
  let fence = null;
  const push = (l) => (moving ? moved[moving.to] : out).push(l);
  for (const line of lines) {
    if (fence) {
      if (isFenceEnd(line, fence)) fence = null;
      push(line);
      continue;
    }
    const f = /^\s*(```+|~~~+)/.exec(line);
    if (f) {
      fence = f[1];
      push(line);
      continue;
    }
    const h = HEADING.exec(line);
    if (!h) {
      push(line);
      continue;
    }
    let level = h[1].length;
    const text = h[2];
    if (level === 1 && h1 === null) {
      h1 = headingText(text);
      continue;
    }
    if (level === 1) shift = 1;
    level = Math.min(level + shift, 6);
    if (moving && level <= moving.level) moving = null;
    const to = page.moveSections?.[headingText(text)];
    if (to) {
      moving = { to, level };
      moved[to] ??= [];
    }
    push(`${"#".repeat(level)} ${text}${page.explicitIds ? ` {#${schemaAnchor(headingText(text))}}` : ""}`);
  }
  if (page.moveSections) {
    for (const [heading, to] of Object.entries(page.moveSections)) {
      if (!moved[to]) fail([`docs/${rel}: section "${heading}" to move to /${to}/ not found`]);
    }
  }
  return { lines: out, moved, h1 };
}

const sources = new Map(); // rel -> { fm, lines, moved, h1 }
for (const [rel, page] of pages) {
  if (page.replacedBy) continue;
  const { fm, body } = splitFrontmatter(fs.readFileSync(path.join(SRC, rel), "utf8").replace(/\r\n/g, "\n"));
  sources.set(rel, { fm, ...restructure(rel, page, body.split("\n")) });
}

// ---- pass 1: where each heading of the current site ends up ----
// Per source page: normalized forms of heading text, VitePress ID and new ID -> { page id, new ID }.

const headings = new Map();
for (const [rel, src] of sources) {
  const index = new Map();
  const add = (lines, id) => {
    const slugger = new GithubSlugger();
    const vpSeen = new Map();
    let fence = null;
    for (const line of lines) {
      if (fence) {
        if (isFenceEnd(line, fence)) fence = null;
        continue;
      }
      const f = /^\s*(```+|~~~+)/.exec(line);
      if (f) {
        fence = f[1];
        continue;
      }
      const h = HEADING.exec(line);
      if (!h) continue;
      const text = headingText(h[2]);
      const explicit = /\{#([^}]+)\}\s*$/.exec(h[2])?.[1];
      const anchor = explicit ?? slugger.slug(text);
      let vp = vitepressSlug(text);
      const n = vpSeen.get(vp);
      vpSeen.set(vp, (n ?? -1) + 1);
      if (n !== undefined) vp = `${vp}-${n + 1}`;
      for (const key of [norm(vp), norm(anchor), norm(text)]) {
        if (key && !index.has(key)) index.set(key, { id, anchor });
      }
    }
  };
  add(src.lines, pages.get(rel).id);
  for (const [to, lines] of Object.entries(src.moved)) add(lines, to);
  headings.set(rel, index);
}

function findPage(p) {
  p = decodeURI(p).replace(/^\//, "").replace(/\/$/, "");
  for (const cand of [p, `${p}.md`, `${p}/index.md`, p === "" ? "index.md" : null]) {
    if (cand && pages.has(cand)) return cand;
  }
  return null;
}

function resolveLink(href, ctx) {
  href = href.replace(/^https?:\/\/(www\.)?robotcode\.io(?=\/|$)/, "") || "/";
  if (/^([a-z]+:|\/\/)/i.test(href)) return href;
  const [p, hash] = href.split("#");
  let target = ctx.rel;
  if (p) {
    const abs = p.startsWith("/") ? p : path.posix.join("/", path.posix.dirname(ctx.rel), p);
    if (/\.(png|gif|jpe?g|svg|webp|json|xml|txt)$/i.test(abs)) return href;
    target = findPage(abs);
    if (!target) {
      warnings.push(`docs/${ctx.rel}: link to unknown page ${href}`);
      return href;
    }
    stats.links++;
  }
  let id = pages.get(target).id;
  let anchor = hash;
  if (hash) {
    const found = headings.get(target)?.get(norm(decodeURIComponent(hash)));
    if (found) {
      ({ id, anchor } = found);
      stats.anchors++;
    } else {
      // Left as it is; the link check of the build reports it.
      warnings.push(`docs/${ctx.rel}: anchor not found: ${href}`);
    }
  }
  if (!p && id === ctx.pageId) return `#${anchor}`;
  return route(id) + (anchor ? `#${anchor}` : "");
}

// ---- pass 2: conversion ----

// Images go to src/assets/ and are referenced relatively, so Astro optimizes them.
const copiedAssets = new Map(); // target -> source
function copyAsset(source, target) {
  const previous = copiedAssets.get(target);
  if (previous && previous !== source && !fs.readFileSync(previous).equals(fs.readFileSync(source))) {
    fail([`${path.relative(ROOT, target)}: different files map to it: ${previous} and ${source}`]);
  }
  if (!previous) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(source, target);
    copiedAssets.set(target, source);
    stats.images++;
  }
}

function importImage(src, ctx) {
  const file = src.startsWith("/")
    ? path.join(SRC, "public", src)
    : path.resolve(path.join(SRC, path.dirname(ctx.rel)), src);
  if (!fs.existsSync(file)) {
    warnings.push(`docs/${ctx.rel}: image not found: ${src}`);
    return src;
  }
  const target = path.join(ASSETS, "screenshots", path.basename(file).toLowerCase().replace(/_/g, "-"));
  copyAsset(file, target);
  return path.relative(ctx.outDir, target).split(path.sep).join("/");
}

function inlineTransforms(line, ctx) {
  line = line.replace(/(!?)\[((?:[^\]`]|`[^`]*`)*)\]\(([^)\s]+)((?:\s+"[^"]*")?)\)/g, (m, bang, text, href, title) =>
    bang
      ? /^[a-z]+:/i.test(href)
        ? m
        : `![${text}](${importImage(href, ctx)}${title})`
      : `[${text}](${resolveLink(href, ctx)}${title})`,
  );
  // [[KEY]] outside code spans (markdown-it-kbd)
  return line
    .split(/(`[^`]*`)/)
    .map((part, i) =>
      i % 2 === 1 ? part : part.replace(/\[\[([^\]]+)\]\]/g, (_, k) => `<kbd>${k.replace(/`/g, "&#96;")}</kbd>`),
    )
    .join("");
}

// ```lang [title] -> title="…"; Shiki notation comments -> Expressive Code line markers.
function emitCode(block, { withTitle = true } = {}) {
  const [, indent, fence, lang, label, rest] = FENCE.exec(block[0]);
  const marks = { del: [], mark: [] };
  const body = block.slice(1, -1).map((l, i) => {
    const n = /\s*(?:#|--|\/\/)\s*\[!code (error|focus|warning|highlight|--|\+\+)\]\s*/.exec(l);
    if (!n) return l;
    (n[1] === "error" || n[1] === "--" ? marks.del : marks.mark).push(i + 1);
    const tail = l.slice(n.index + n[0].length);
    return tail ? `${l.slice(0, n.index)}  # ${tail}` : l.slice(0, n.index);
  });
  const meta = [];
  if (label && withTitle) meta.push(`title=${JSON.stringify(label)}`);
  if (marks.del.length) meta.push(`del={${marks.del.join(",")}}`);
  if (marks.mark.length) meta.push(`mark={${marks.mark.join(",")}}`);
  if (rest) meta.push(rest);
  return [`${indent}${fence}${lang}${meta.length ? ` ${meta.join(" ")}` : ""}`, ...body, block.at(-1)];
}

function blockEnd(lines, i, fence) {
  let j = i + 1;
  while (j < lines.length && !isFenceEnd(lines[j], fence)) j++;
  return j;
}

function collectContainer(lines, start, rel) {
  let depth = 1;
  for (let i = start; i < lines.length; i++) {
    const f = FENCE.exec(lines[i]);
    if (f) {
      i = blockEnd(lines, i, f[2]);
      continue;
    }
    if (CONTAINER_OPEN.test(lines[i])) depth++;
    else if (CONTAINER_CLOSE.test(lines[i]) && --depth === 0) return { inner: lines.slice(start, i), end: i };
  }
  fail([`docs/${rel}: unterminated ::: container`]);
}

function convertLines(lines, ctx) {
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const f = FENCE.exec(line);
    if (f) {
      const j = blockEnd(lines, i, f[2]);
      out.push(...emitCode(lines.slice(i, j + 1)));
      i = j;
      continue;
    }
    const o = CONTAINER_OPEN.exec(line);
    if (o) {
      const [, indent, kind, title] = o;
      const { inner, end } = collectContainer(lines, i + 1, ctx.rel);
      i = end;
      if (ASIDE[kind]) {
        out.push(`${indent}:::${ASIDE[kind]}${title ? `[${title}]` : ""}`, ...convertLines(inner, ctx), `${indent}:::`);
      } else if (kind === "details") {
        out.push(
          `${indent}<details>`,
          `${indent}<summary>${title || "Details"}</summary>`,
          "",
          ...convertLines(inner, ctx),
          "",
          `${indent}</details>`,
        );
      } else if (kind === "code-group") {
        const blocks = [];
        for (let k = 0; k < inner.length; k++) {
          const cf = FENCE.exec(inner[k]);
          if (cf) {
            const e = blockEnd(inner, k, cf[2]);
            blocks.push(inner.slice(k, e + 1));
            k = e;
          }
        }
        if (blocks.length === 1) {
          out.push(...emitCode(blocks[0]));
          continue;
        }
        ctx.imports.add("Tabs").add("TabItem");
        out.push(`${indent}<Tabs syncKey="os">`);
        for (const b of blocks) {
          const cf = FENCE.exec(b[0]);
          out.push(
            `${indent}<TabItem label=${jsxAttr(cf[4] || cf[3] || "Code")}>`,
            "",
            ...emitCode(b, { withTitle: false }),
            "",
            `${indent}</TabItem>`,
          );
        }
        out.push(`${indent}</Tabs>`);
      } else if (kind === "tabs") {
        ctx.imports.add("Tabs").add("TabItem");
        const parts = [];
        for (const l of inner) {
          const t = /^\s*===\s+(.+)$/.exec(l);
          if (t) parts.push({ label: t[1].trim(), lines: [] });
          else parts.at(-1)?.lines.push(l);
        }
        out.push(`${indent}<Tabs>`);
        for (const p of parts) {
          out.push(
            `${indent}<TabItem label=${jsxAttr(p.label)}>`,
            "",
            ...convertLines(p.lines, ctx),
            "",
            `${indent}</TabItem>`,
          );
        }
        out.push(`${indent}</Tabs>`);
      }
      continue;
    }
    const li = /^(\s*)1\.\s+(.*)$/.exec(line);
    if (li && !ctx.inSteps && ctx.page.steps?.some((r) => r.test(li[2]))) {
      const indent = li[1];
      const item = new RegExp(`^${indent}\\d+\\.\\s`);
      let j = i + 1;
      while (j < lines.length) {
        const l = lines[j];
        if (!l.trim() || l.startsWith(`${indent} `) || l.startsWith(`${indent}\t`) || item.test(l)) j++;
        else break;
      }
      while (j > i + 1 && !lines[j - 1].trim()) j--;
      ctx.imports.add("Steps");
      ctx.inSteps = true;
      out.push(`${indent}<Steps>`, "", ...convertLines(lines.slice(i, j), ctx), "", `${indent}</Steps>`);
      ctx.inSteps = false;
      i = j - 1;
      continue;
    }
    out.push(inlineTransforms(line, ctx));
  }
  return out;
}

// First sentence of the first paragraph, as plain text.
function firstSentence(lines) {
  const para = firstParagraph(lines);
  if (!para) return undefined;
  const text = lines
    .slice(para.start, para.end)
    .join(" ")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\*\*|__|`/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return /^.*?[.!?](?=\s|$)/.exec(text)?.[0] ?? text;
}

function firstParagraph(lines) {
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].trim() || (i > 0 && lines[i - 1].trim())) continue;
    if (/^\s*([#<:|>`{!-]|\d+\.\s|[*+]\s)/.test(lines[i])) continue;
    let end = i;
    while (end < lines.length && lines[end].trim()) end++;
    return { start: i, end };
  }
  return undefined;
}

// MDX has no HTML comments: <!-- … --> outside code becomes {/* … */}.
function toMdx(lines, imports) {
  let fence = null;
  const body = lines.map((l) => {
    const f = /^\s*(```+|~~~+)/.exec(l);
    if (fence) {
      if (isFenceEnd(l, fence)) fence = null;
      return l;
    }
    if (f) {
      fence = f[1];
      return l;
    }
    return l.replace(/<!--(.*?)-->/g, "{/*$1*/}");
  });
  return imports.size
    ? [`import { ${[...imports].join(", ")} } from "@astrojs/starlight/components";`, "", ...body]
    : body;
}

const sourceOf = new Map(); // written page -> its source, for messages

function writePage(file, front, lines, source) {
  sourceOf.set(file, source);
  const text = `---\n${dump(front, { lineWidth: -1 }).trim()}\n---\n\n${lines.join("\n").replace(/^\n+/, "").replace(/\n*$/, "\n")}`;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
  stats.pages++;
  if (file.endsWith(".mdx")) stats.mdx++;
}

const index = []; // for /llms.txt: { id, title, description, order, date }
const movedSections = {}; // page id -> converted lines

function convertPage(rel, page, src) {
  const outBase = path.join(OUT, page.id);
  const ctx = { rel, page, pageId: page.id, outDir: path.dirname(outBase), imports: new Set() };
  let lines = convertLines(src.lines, ctx);
  for (const [to, moved] of Object.entries(src.moved)) {
    const movedCtx = { ...ctx, pageId: to, outDir: path.join(OUT, to), imports: new Set() };
    movedSections[to] = { lines: convertLines(moved, movedCtx), source: rel };
  }

  const title = page.title ?? src.fm.title ?? src.h1;
  if (!title) fail([`docs/${rel}: no title`]);
  const description = page.description ?? src.fm.description ?? (page.automatic ? firstSentence(lines) : undefined);
  if (!description) fail([`docs/${rel}: no description; add one to the page map`]);
  const front = { title, description };
  if (page.label || page.order !== undefined) {
    front.sidebar = {
      ...(page.label && { label: page.label }),
      ...(page.order !== undefined && { order: page.order }),
    };
  }
  if (rel.startsWith("news/")) {
    front.date = new Date(src.fm.date);
    if (Number.isNaN(front.date.getTime())) fail([`docs/${rel}: news post without a valid date`]);
    front.tags = page.tags;
    if (page.excerpt) front.excerpt = page.excerpt;
    else {
      const para = firstParagraph(lines);
      if (para) lines.splice(para.end, 0, "", "<!-- excerpt -->");
    }
  }
  Object.assign(front, page.frontmatter);
  front.editUrl = `${EDIT_URL}docs/${rel}`;
  const date = lastChange(`docs/${rel}`);
  if (date) front.lastUpdated = date;
  if (page.notice) lines = [...page.notice, "", ...lines];

  const mdx = ctx.imports.size > 0;
  writePage(`${outBase}.${mdx ? "mdx" : "md"}`, front, mdx ? toMdx(lines, ctx.imports) : lines, `docs/${rel}`);
  index.push({ id: page.id, title: front.title, description, order: page.order, date: front.date });
}

// Hand-written pages (content/) are copied with edit link and last change, unless they set their own.
function copyHandwritten(file) {
  const rel = path.relative(CONTENT, file).split(path.sep).join("/");
  const { fm, body } = splitFrontmatter(fs.readFileSync(file, "utf8"));
  const id = rel.replace(/(?:^|\/)index\.mdx?$/, "").replace(/\.mdx?$/, "");
  const sources = [`docs-next/content/${rel}`];
  let lines = body.split("\n");
  const marker = lines.findIndex((l) => l.trim() === SECTIONS_MARKER);
  if (marker >= 0) {
    const moved = movedSections[id];
    if (!moved) fail([`docs-next/content/${rel}: no sections are moved to /${id}/`]);
    lines.splice(marker, 1, ...(rel.endsWith(".mdx") ? toMdx(moved.lines, new Set()) : moved.lines));
    sources.push(`docs/${moved.source}`);
    delete movedSections[id];
  }
  const front = { ...fm };
  front.editUrl ??= `${EDIT_URL}docs-next/content/${rel}`;
  const date = lastChange(...sources);
  if (front.lastUpdated === undefined && date) front.lastUpdated = date;
  writePage(path.join(OUT, rel), front, lines, sources.join(", "));
  if (id) index.push({ id, title: fm.title, description: fm.description, order: fm.sidebar?.order });
}

// ---- run ----

for (const dir of [OUT, ASSETS, PUBLIC, GENERATED]) fs.rmSync(dir, { recursive: true, force: true });

for (const [rel, src] of sources) convertPage(rel, pages.get(rel), src);
for (const file of findFiles(CONTENT)) copyHandwritten(file);
for (const [id, moved] of Object.entries(movedSections)) {
  fail([
    `docs/${moved.source}: sections moved to /${id}/, but content/ has no page with the ${SECTIONS_MARKER} marker`,
  ]);
}

for (const f of PUBLIC_FILES) copyAsset(path.join(SRC, "public", f), path.join(PUBLIC, f));
for (const [target, source] of Object.entries(HANDWRITTEN_ASSETS))
  copyAsset(path.join(SRC, source), path.join(ASSETS, target));
for (const name of HERO_PICTURES) {
  copyAsset(path.join(SRC, "public", `robotcode-${name}.png`), path.join(ASSETS, "hero", `robotcode-${name}.png`));
}

writeLlmsIndex();
selfCheck();
checkPageLinks();

for (const w of warnings) console.warn(`convert: warning: ${w}`);
console.log(
  `convert: ${stats.pages} pages (${stats.mdx} MDX), ${stats.images} files copied, ${stats.links} links and ${stats.anchors} anchors mapped`,
);

// Page index for /llms.txt, in sidebar order; starlight-llms-txt puts it after the description.
function writeLlmsIndex() {
  const entry = (p) => `- [${p.title}](${SITE}${route(p.id)}): ${p.description}`;
  const area = (prefix) =>
    index
      .filter((p) => p.id === prefix || p.id.startsWith(`${prefix}/`))
      .sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity) || a.title.localeCompare(b.title))
      .map(entry);
  const byId = (id) => index.filter((p) => p.id === id).map(entry);
  const groups = [
    ["About", byId("about")],
    ["Getting Started", area("getting-started")],
    ["Guides", area("guides")],
    ["Reference", area("reference")],
    ["Support & Contribute", byId("contributing")],
    [
      "News",
      index
        .filter((p) => p.id.startsWith("news/"))
        .sort((a, b) => b.date - a.date)
        .map(entry),
    ],
  ];
  const listed = new Set(groups.flatMap(([, items]) => items));
  const missing = index.map(entry).filter((e) => !listed.has(e));
  if (missing.length) fail(missing.map((e) => `page outside the sidebar areas: ${e}`));
  const text = groups.map(([label, items]) => `**${label}**\n\n${items.join("\n")}`).join("\n\n");
  fs.mkdirSync(GENERATED, { recursive: true });
  fs.writeFileSync(path.join(GENERATED, "llms-index.md"), `${text}\n`);
}

// Syntax only VitePress knows renders as plain text in Starlight, without an error: fail instead.
function selfCheck() {
  const patterns = [
    [/:::[ \t]+\S/, "VitePress container (`::: name`)"],
    [/:::(?:info|warning|details|code-group|tabs|raw|v-pre)\b/, "container Starlight does not know"],
    [/\[\[/, "`[[KEY]]` keyboard syntax"],
    [/\[!code/, "Shiki `[!code …]` notation"],
    [/^=== /, "`=== label` tab syntax"],
  ];
  const problems = [];
  for (const file of findFiles(OUT)) {
    const rel = `${sourceOf.get(file)} (${path.relative(ROOT, file)}`;
    const checks = file.endsWith(".mdx") ? [...patterns, [/\{#/, "`{#id}` heading attribute in MDX"]] : patterns;
    let fence = null;
    fs.readFileSync(file, "utf8")
      .split("\n")
      .forEach((line, i) => {
        if (fence) {
          if (isFenceEnd(line, fence)) fence = null;
          return;
        }
        const f = /^\s*(```+|~~~+)/.exec(line);
        if (f) {
          fence = f[1];
          return;
        }
        const text = line.replace(/`[^`]*`/g, "");
        for (const [re, what] of checks) if (re.test(text)) problems.push(`${rel}:${i + 1}): ${what}: ${line.trim()}`);
      });
  }
  if (problems.length) {
    fail(problems, "Add a conversion rule to docs-next/scripts/convert.mjs or use syntax both sites support.");
  }
}

// The link check of the build reads only the docs collection, not the pages in src/pages/ (the not-found page).
function checkPageLinks() {
  const known = new Set([...pages.values(), ...index].map((p) => route(p.id)));
  const dir = path.join(ROOT, "src/pages");
  const problems = [];
  for (const file of fs.readdirSync(dir)) {
    for (const [, href] of fs.readFileSync(path.join(dir, file), "utf8").matchAll(/href="(\/[^"#?]*)/g)) {
      if (!known.has(href)) problems.push(`src/pages/${file}: link to a page that does not exist: ${href}`);
    }
  }
  if (problems.length) fail(problems);
}

function findFiles(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true, recursive: true })
    .filter((e) => e.isFile() && /\.mdx?$/.test(e.name))
    .map((e) => path.join(e.parentPath, e.name))
    .sort();
}

function fail(messages, hint) {
  for (const m of messages) console.error(`convert: error: ${m}`);
  if (hint) console.error(`convert: ${hint}`);
  process.exit(1);
}
