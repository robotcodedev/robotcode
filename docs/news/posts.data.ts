import { createContentLoader } from "vitepress";

export default createContentLoader("news/*.md", {
  transform(raw) {
    return raw
      .filter((p) => p.url !== "/news/")
      .filter((p) => !p.frontmatter.aprilFools || new Date() <= new Date("2026-04-02T12:00:00"))
      .sort((a, b) => {
        return +new Date(b.frontmatter.date) - +new Date(a.frontmatter.date);
      });
  },
});
