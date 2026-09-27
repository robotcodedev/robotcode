import { defineCollection } from "astro:content";
import { docsLoader, i18nLoader } from "@astrojs/starlight/loaders";
import { docsSchema, i18nSchema } from "@astrojs/starlight/schema";
import { blogSchema } from "starlight-blog/schema";

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({ extend: (context) => blogSchema(context) }),
  }),
  // Overrides of Starlight's UI strings; src/content/i18n/en.json overrides none. Starlight reads this collection
  // on every page, and Astro 7 warns during the build when it is missing or empty.
  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),
};
