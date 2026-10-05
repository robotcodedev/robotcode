// Page index for /llms.txt, which starlight-llms-txt puts after the site description: every page with its title, URL
// and description, grouped like the sidebar and in its order, the news newest first.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { load } from "js-yaml";

const DOCS = fileURLToPath(new URL("../src/content/docs/", import.meta.url));
const SITE = "https://robotcode.io";

export function llmsIndex() {
  const pages = fs
    .readdirSync(DOCS, { withFileTypes: true, recursive: true })
    .filter((e) => e.isFile() && /\.mdx?$/.test(e.name))
    .map((e) => {
      const file = path.join(e.parentPath, e.name);
      const id = path
        .relative(DOCS, file)
        .split(path.sep)
        .join("/")
        .replace(/(?:^|\/)index\.mdx?$/, "")
        .replace(/\.mdx?$/, "");
      const fm = load(/^---\n([\s\S]*?)\n---\n/.exec(fs.readFileSync(file, "utf8"))[1]);
      return { id, title: fm.title, description: fm.description, order: fm.sidebar?.order, date: fm.date };
    })
    .filter((p) => p.id !== "");

  const entry = (p) => `- [${p.title}](${SITE}/${p.id}/): ${p.description}`;
  const area = (prefix) =>
    pages
      .filter((p) => p.id === prefix || p.id.startsWith(`${prefix}/`))
      .sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity) || a.title.localeCompare(b.title))
      .map(entry);
  const byId = (id) => pages.filter((p) => p.id === id).map(entry);
  const groups = [
    ["About", byId("about")],
    ["Getting Started", area("getting-started")],
    ["Guides", area("guides")],
    ["Reference", area("reference")],
    ["Support & Contribute", byId("contributing")],
    [
      "News",
      pages
        .filter((p) => p.id.startsWith("news/"))
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .map(entry),
    ],
  ];
  const listed = new Set(groups.flatMap(([, items]) => items));
  const missing = pages.map(entry).filter((e) => !listed.has(e));
  if (missing.length) throw new Error(`llms-index: pages outside the sidebar areas:\n${missing.join("\n")}`);
  return `${groups.map(([label, items]) => `**${label}**\n\n${items.join("\n")}`).join("\n\n")}\n`;
}
