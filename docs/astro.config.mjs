// @ts-check
import fs from "node:fs";
import { defineConfig } from "astro/config";
import { satteri } from "@astrojs/markdown-satteri";
import starlight from "@astrojs/starlight";
import starlightDocSearch from "@astrojs/starlight-docsearch";
import starlightBlog from "starlight-blog";
import starlightLinksValidator from "starlight-links-validator";
import starlightLlmsTxt from "starlight-llms-txt";
import { latestNews } from "./scripts/latest-news.mjs";
import { llmsIndex } from "./scripts/llms-index.mjs";

const robotGrammar = JSON.parse(
  fs.readFileSync(new URL("../syntaxes/robotframework.tmLanguage.json", import.meta.url), "utf8"),
);
// Shiki has no grammar for the patterns of .gitignore and .robotignore files.
const gitignoreGrammar = {
  name: "gitignore",
  scopeName: "source.gitignore",
  patterns: [
    { match: "^\\s*#.*$", name: "comment.line.number-sign.gitignore" },
    { match: "^\\s*(!)", captures: { 1: { name: "keyword.operator.negation.gitignore" } } },
    { match: "\\*\\*|[*?]", name: "keyword.operator.wildcard.gitignore" },
  ],
};

export default defineConfig({
  site: "https://robotcode.io",
  // The "What's New?" notification of the VS Code extension opens /news/latest/.
  redirects: { "/news/latest": latestNews() },
  markdown: {
    // No typographic replacements: `--include` must not become an en dash.
    processor: satteri({ features: { headingAttributes: true, smartPunctuation: false } }),
  },
  vite: {
    // Starlight imports js-yaml 4 with a default import. Astro's prerender build keeps that import external, so
    // it would load js-yaml 5 of scripts/llms-index.mjs from node_modules/ and fail; bundled, it keeps Starlight's own
    // copy (the same problem Astro solves for neotraverse, withastro/astro#17508).
    environments: { prerender: { resolve: { noExternal: ["js-yaml"] } } },
    build: {
      rolldownOptions: {
        onwarn(warning, warn) {
          // Astro prepends a directive it no longer reads to every MDX page with components, and rolldown warns
          // about it once per page; remove once withastro/astro#18087 is fixed in a release.
          if (warning.code === "MODULE_LEVEL_DIRECTIVE" && warning.message.includes("astro:head-inject")) return;
          warn(warning);
        },
      },
    },
  },
  integrations: [
    starlight({
      title: "RobotCode",
      description: "Robot Framework for Visual Studio Code and more",
      logo: { src: "./src/assets/robotcode-logo.svg" },
      favicon: "/robotcode-logo.svg",
      head: [
        { tag: "link", attrs: { rel: "icon", type: "image/png", href: "/robotcode-logo-mini.png" } },
        { tag: "meta", attrs: { property: "og:image", content: "https://robotcode.io/robotcode-logo.jpg" } },
      ],
      social: [
        { icon: "github", label: "GitHub", href: "https://github.com/robotcodedev/robotcode" },
        { icon: "seti:python", label: "PyPI", href: "https://pypi.org/project/robotcode/" },
        {
          icon: "vscode",
          label: "VS Code Marketplace",
          href: "https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode",
        },
        { icon: "jetbrains", label: "JetBrains Marketplace", href: "https://plugins.jetbrains.com/plugin/26216" },
        { icon: "openCollective", label: "Open Collective", href: "https://opencollective.com/robotcode" },
      ],
      editLink: { baseUrl: "https://github.com/robotcodedev/robotcode/edit/main/docs/" },
      lastUpdated: true,
      // The not-found page is src/pages/404.astro.
      disable404Route: true,
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 4 },
      customCss: ["./src/styles/custom.css", "./src/styles/home.css"],
      expressiveCode: {
        themes: ["material-theme-darker", "material-theme-lighter"],
        shiki: { langs: [robotGrammar, gitignoreGrammar] },
      },
      sidebar: [
        "about",
        { label: "Getting Started", items: [{ autogenerate: { directory: "getting-started" } }] },
        { label: "Guides", items: [{ autogenerate: { directory: "guides" } }] },
        { label: "Reference", items: [{ autogenerate: { directory: "reference" } }] },
        "contributing",
      ],
      components: {
        Header: "./src/components/Header.astro",
        Hero: "./src/components/Hero.astro",
        Footer: "./src/components/Footer.astro",
      },
      plugins: [
        // Algolia DocSearch instead of Pagefind; the key is the public search-only key of the index.
        starlightDocSearch({ appId: "7D5ZR1RO6N", apiKey: "699cc9be1fe74f0953afdd17beb6e9c9", indexName: "robotcode" }),
        starlightBlog({
          prefix: "news",
          title: "News",
          // News is an entry of the top navigation (src/components/TopNav.astro).
          navigation: "none",
          authors: {
            daniel: {
              name: "Daniel Biehl",
              url: "https://github.com/d-biehl",
              picture: "https://github.com/d-biehl.png",
            },
          },
        }),
        starlightLinksValidator({
          // Routes generated by starlight-blog, which the validator does not know.
          exclude: ["/news/", "/news/[0-9]*/", "/news/tags/**", "/news/authors/**", "/news/rss.xml"],
        }),
        starlightLlmsTxt({ details: llmsIndex(), customSelectors: { all: ["[data-llms-skip]"] } }),
      ],
    }),
  ],
});
