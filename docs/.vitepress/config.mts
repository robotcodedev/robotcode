import { defineConfig } from "vitepress";
import { generateSidebar } from "vitepress-sidebar";
import robotframework from "../../syntaxes/robotframework.tmLanguage.json";
import { readFileSync } from "fs";

const python_svg = readFileSync("docs/images/python.svg", "utf-8");
const vscode_svg = readFileSync("docs/images/vscode.svg", "utf-8");
const opencollective_svg = readFileSync("docs/images/opencollective.svg", "utf-8");

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "RobotCode",
  description: "Robot Framework for Visual Studio Code and more",

  lastUpdated: true,
  cleanUrls: true,
  metaChunk: true,

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
      { text: "Contribute", link: "https://github.com/robotcodedev" },
      { text: "Q&A", link: "https://github.com/robotcodedev/robotcode/discussions/categories/q-a" },
    ],
    search: {
      provider: "local",
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
      documentRootPath: "docs",
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
      { icon: { svg: opencollective_svg }, link: "https://opencollective.com/robotcode" },
    ],
  },
  markdown: {
    image: {
      lazyLoading: true
    },
    lineNumbers: true,
    theme: { light: "material-theme-lighter", dark: "material-theme-darker" },
    headers: {
      level: [2, 3, 4],
    },
    math: true,
    languages: [robotframework as any],
    languageAlias: {
      robot: "robotframework",
    },
    toc: {
      level: [2, 3, 4],
    },
  },
});
