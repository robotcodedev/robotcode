import { createContentLoader } from "vitepress";

export default createContentLoader("news/*.md", {
  transform(raw) {
    return raw
      .filter((p) => p.url !== "/news/")
      .sort((a, b) => {
        return +new Date(b.frontmatter.date) - +new Date(a.frontmatter.date);
      });
  },
});
