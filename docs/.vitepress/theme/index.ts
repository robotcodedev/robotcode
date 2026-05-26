// https://vitepress.dev/guide/custom-theme
import { h } from "vue";
import type { Theme } from "vitepress";
import { inBrowser } from "vitepress";
import DefaultTheme from "vitepress/theme";
import { enhanceAppWithTabs } from "vitepress-plugin-tabs/client";
import RandomHeroImage from "./components/RandomHeroImage.vue";
import RandomTagline from "./components/RandomTagline.vue";
import "./style.css";
import "lite-youtube-embed/src/lite-yt-embed.css";

if (inBrowser) {
  // @ts-ignore
  import("lite-youtube-embed");
}

export default {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      // Render a randomized hero image each time the page loads in the browser.
      "home-hero-image": () => h(RandomHeroImage),
      // Render a randomized tagline each time the page loads in the browser.
      "home-hero-info-after": () => h(RandomTagline),
    }),
  enhanceApp({ app, router, siteData }) {
    // ...
    enhanceAppWithTabs(app);
  },
} satisfies Theme;
