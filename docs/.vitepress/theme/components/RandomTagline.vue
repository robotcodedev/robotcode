<script setup lang="ts">
import { onMounted, ref } from "vue";

const TAGLINES: string[] = [
  "Robot Framework testing — same intelligence in your editor, on the command line, and in your CI pipeline. From your first keyword to enterprise scale.",
  "One workflow for the entire Robot Framework lifecycle — write tests in your editor, run them on the command line, ship them through CI.",
  "Robot Framework testing across your editor, command line, and CI — with the same intelligence, the same configuration, from your first keyword to multi-team suites.",
  "Modern Robot Framework tooling that meets you wherever you work — in your editor, on the command line, and in your CI pipeline.",
];

const tagline = ref<string>(TAGLINES[0]);

const pickRandomTagline = () => {
  if (TAGLINES.length <= 1) {
    return;
  }
  const index = Math.floor(Math.random() * TAGLINES.length);
  tagline.value = TAGLINES[index];
};

onMounted(() => {
  pickRandomTagline();
});
</script>

<template>
  <p class="tagline">{{ tagline }}</p>
</template>

<style scoped>
.tagline {
  padding-top: 8px;
  max-width: 392px;
  line-height: 28px;
  font-size: 18px;
  font-weight: 500;
  white-space: pre-wrap;
  color: var(--vp-c-text-2);
  margin: 0 auto;
}

@media (min-width: 640px) {
  .tagline {
    padding-top: 12px;
    max-width: 576px;
    line-height: 32px;
    font-size: 20px;
  }
}

@media (min-width: 960px) {
  .tagline {
    line-height: 36px;
    font-size: 24px;
    margin: 0;
  }
}
</style>
