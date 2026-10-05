// Checks the links of the pages in src/pages/ (the not-found page), which the link check of the build does not read:
// each must lead to a page of src/content/docs/ or to the news.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SRC = fileURLToPath(new URL("../src/", import.meta.url));
const DOCS = path.join(SRC, "content/docs");
const PAGES = path.join(SRC, "pages");

const known = new Set(["/news/"]);
for (const e of fs.readdirSync(DOCS, { withFileTypes: true, recursive: true })) {
  if (!e.isFile() || !/\.mdx?$/.test(e.name)) continue;
  const id = path
    .relative(DOCS, path.join(e.parentPath, e.name))
    .split(path.sep)
    .join("/")
    .replace(/(?:^|\/)index\.mdx?$/, "")
    .replace(/\.mdx?$/, "");
  known.add(id ? `/${id}/` : "/");
}

const problems = [];
for (const file of fs.readdirSync(PAGES)) {
  for (const [, href] of fs.readFileSync(path.join(PAGES, file), "utf8").matchAll(/href="(\/[^"#?]*)/g)) {
    if (!known.has(href)) problems.push(`src/pages/${file}: link to a page that does not exist: ${href}`);
  }
}
for (const p of problems) console.error(`check-page-links: error: ${p}`);
if (problems.length) process.exit(1);
