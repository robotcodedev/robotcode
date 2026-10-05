// Target of the redirect /news/latest/: the newest release post, by the `date` and `tags` in the frontmatter of the
// posts (drafts left out), so that a tips or April Fools post never becomes the target. The "What's New?"
// notification of the VS Code extension opens /news/latest/.
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { load } from "js-yaml";

const NEWS = fileURLToPath(new URL("../src/content/docs/news/", import.meta.url));

export function latestNews() {
  const posts = fs
    .readdirSync(NEWS)
    .filter((name) => /\.mdx?$/.test(name))
    .map((name) => ({
      id: name.replace(/\.mdx?$/, ""),
      ...load(/^---\n([\s\S]*?)\n---\n/.exec(fs.readFileSync(NEWS + name, "utf8"))[1]),
    }))
    .filter((post) => post.tags?.includes("release") && !post.draft)
    // js-yaml 5 reads the dates as strings.
    .sort((a, b) => new Date(b.date) - new Date(a.date));
  if (posts.length === 0) throw new Error("latest-news: no release posts");
  return `/news/${posts[0].id}/`;
}
