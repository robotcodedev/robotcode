<script setup lang="ts">
import { onMounted, ref } from "vue";
import { withBase } from "vitepress";

type HeroImage = {
  src: string;
  alt: string;
};

const HERO_IMAGES: HeroImage[] = [
  { src: "/robotcode-toy-tray.png", alt: "RobotCode figurines on a tray" },
  { src: "/robotcode-vintage.png", alt: "Vintage RobotCode poster" },
  { src: "/robotcode-vintage-new.png", alt: "New vintage RobotCode artwork" },
  { src: "/robotcode-golf.png", alt: "RobotCode playing golf" },
  { src: "/robotcode-golf.png", alt: "RobotCode playing golf" },
  { src: "/robotcode-rock.png", alt: "RobotCode playing rock music" },
  { src: "/robotcode-soccer.png", alt: "RobotCode playing soccer" },
  //   { src: "/robotcode-vintage-christmas.png", alt: "Festive RobotCode postcard" },
];

const hero = ref<HeroImage>(HERO_IMAGES[0]);

const pickRandomHero = () => {
  if (HERO_IMAGES.length <= 1) {
    return;
  }
  const index = Math.floor(Math.random() * HERO_IMAGES.length);
  hero.value = HERO_IMAGES[index];
};

onMounted(() => {
  pickRandomHero();
});
</script>

<template>
  <div class="random-hero">
    <img class="VPImage image-src" :src="withBase(hero.src)" :alt="hero.alt" loading="eager" decoding="async" />
  </div>
</template>

<style scoped>
.random-hero {
  display: flex;
  justify-content: center;
  width: 100%;
}

.image-src {
  width: auto;
  height: auto;
  max-width: 100%;
}
</style>
