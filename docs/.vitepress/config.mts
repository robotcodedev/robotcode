import { defineConfig } from "vitepress";
import { generateSidebar } from "vitepress-sidebar";
import llmstxtPlugin from "vitepress-plugin-llmstxt";
import taskLists from "markdown-it-task-lists";
import kbd from "markdown-it-kbd";
import abbr from "markdown-it-abbr";
import { tabsMarkdownPlugin } from "vitepress-plugin-tabs";
import robotframework from "../../syntaxes/robotframework.tmLanguage.json";
import { readFileSync } from "fs";
import pkg from "../../package.json";
//import python_svg from "../images/python.svg?raw";
const python_svg = readFileSync("images/python.svg", "utf-8");
const vscode_svg = readFileSync("images/vscode.svg", "utf-8");
const pycharm_svg = readFileSync("images/pycharm.svg", "utf-8");
const opencollective_svg = readFileSync("images/opencollective.svg", "utf-8");

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "RobotCode",
  description: "Robot Framework for Visual Studio Code and more",

  lastUpdated: true,
  cleanUrls: true,
  metaChunk: true,
  sitemap: {
    hostname: "https://robotcode.io",
  },
  head: [
    ["link", { rel: "icon", type: "image/svg+xml", href: "/robotcode-logo.svg" }],
    ["link", { rel: "icon", type: "image/png", href: "/robotcode-logo-mini.png" }],
    ["meta", { name: "theme-color", content: "#5f67ee" }],
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:locale", content: "en" }],
    ["meta", { property: "og:title", content: "RobotCode | Robot Framework for Visual Studio Code and more" }],
    ["meta", { property: "og:site_name", content: "RobotCode" }],
    ["meta", { property: "og:image", content: "https://robotcode.io/robotcode-logo.jpg" }],
    ["meta", { property: "og:url", content: "https://robotcode.io/" }],
  ],
  vite: {
    plugins: [llmstxtPlugin()],
  },
  vue: {
    template: {
      compilerOptions: {
        isCustomElement: (tag) => tag === "lite-youtube",
      },
    },
  },
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: { src: "/robotcode-logo.svg", alt: "RobotCode Logo" },
    outline: {
      level: "deep",
    },
    externalLinkIcon: true,
    footer: {
      message:
        'Released under the <a href="https://github.com/robotcodedev/robotcode/blob/main/LICENSE.txt">Apache-2.0</a>.',
      copyright: 'Copyright © 2022-present <a href="https://github.com/d-biehl">Daniel Biehl</a>',
    },
    nav: [
      { text: "Home", link: "/" },
      { text: "Documentation", link: "/01_about" },
      { text: "Support & Contribute", link: "/05_contributing" },
      { text: "Q&A", link: "https://github.com/robotcodedev/robotcode/discussions/categories/q-a" },
      {
        text: pkg.version,
        items: [
          {
            text: "Changelog",
            link: "https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md",
          },
          {
            text: "Contributing",
            link: "https://github.com/robotcodedev/robotcode/blob/main/CONTRIBUTING.md",
          },
        ],
      },
    ],
    search: {
      provider: "algolia",
      options: {
        appId: "7D5ZR1RO6N",
        apiKey: "699cc9be1fe74f0953afdd17beb6e9c9",
        indexName: "robotcode",
      },
    },
    editLink: {
      pattern: "https://github.com/robotcodedev/robotcode/edit/main/docs/:path",
    },
    // sidebar: [
    //   {
    //     text: 'Examples',
    //     items: [
    //       { text: 'Markdown Examples', link: '/markdown-examples' },
    //       { text: 'Runtime API Examples', link: '/api-examples' }
    //     ]
    //   }
    // ],
    sidebar: generateSidebar({
      documentRootPath: ".",
      collapsed: true,
      useTitleFromFileHeading: true,
      useTitleFromFrontmatter: true,
      useFolderLinkFromIndexFile: true,
      useFolderTitleFromIndexFile: true,
    }),
    socialLinks: [
      { icon: "github", link: "https://github.com/robotcodedev/robotcode" },
      { icon: { svg: python_svg }, link: "https://pypi.org/project/robotcode/" },
      { icon: { svg: vscode_svg }, link: "https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode" },
      { icon: { svg: pycharm_svg }, link: "https://plugins.jetbrains.com/plugin/26216" },
      { icon: { svg: opencollective_svg }, link: "https://opencollective.com/robotcode" },
    ],
  },
  markdown: {
    config(md: any) {
      md.use(kbd);
      md.use(abbr);
      md.use(taskLists);
      md.use(tabsMarkdownPlugin);
    },
    attrs: {
      disable: false,
    },
    image: {
      lazyLoading: true,
    },
    //lineNumbers: true,
    theme: { light: "material-theme-lighter", dark: "material-theme-darker" },
    headers: {
      level: [2, 3, 4],
    },
    math: false,
    languages: [robotframework as any],
    toc: {
      level: [2, 3, 4],
    },
  },
});
