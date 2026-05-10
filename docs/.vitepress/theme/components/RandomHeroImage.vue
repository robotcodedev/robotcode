<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
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
  { src: "/robotcode-rock.png", alt: "RobotCode playing rock music" },
  { src: "/robotcode-soccer.png", alt: "RobotCode playing soccer" },
  { src: "/robotcode-max.png", alt: "Robert Code" },
  { src: "/robotcode-playmo.png", alt: "RobotCode Playmobil" },
  { src: "/robotcode-rise.png", alt: "Rise of the RobotCode" },
  //   { src: "/robotcode-vintage-christmas.png", alt: "Festive RobotCode postcard" },
];

const hero = ref<HeroImage>(HERO_IMAGES[0]);
const heroIndex = ref(0);
const isLightboxOpen = ref(false);

const pickRandomHero = () => {
  if (HERO_IMAGES.length <= 1) {
    return;
  }
  const index = Math.floor(Math.random() * HERO_IMAGES.length);
  heroIndex.value = index;
  hero.value = HERO_IMAGES[index];
};

const showHeroAtIndex = (index: number) => {
  if (HERO_IMAGES.length === 0) {
    return;
  }
  const nextIndex = (index + HERO_IMAGES.length) % HERO_IMAGES.length;
  heroIndex.value = nextIndex;
  hero.value = HERO_IMAGES[nextIndex];
};

const showPreviousHero = () => {
  showHeroAtIndex(heroIndex.value - 1);
};

const showNextHero = () => {
  showHeroAtIndex(heroIndex.value + 1);
};

const openLightbox = () => {
  isLightboxOpen.value = true;
  document.body.style.overflow = "hidden";
};

const closeLightbox = () => {
  isLightboxOpen.value = false;
  document.body.style.overflow = "";
};

const onWindowKeyDown = (event: KeyboardEvent) => {
  if (!isLightboxOpen.value) {
    return;
  }

  if (event.key === "Escape") {
    closeLightbox();
    return;
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    showPreviousHero();
    return;
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();
    showNextHero();
  }
};

onMounted(() => {
  pickRandomHero();
  window.addEventListener("keydown", onWindowKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onWindowKeyDown);
  document.body.style.overflow = "";
});
</script>

<template>
  <div class="random-hero">
    <button v-if="HERO_IMAGES.length > 1" class="hero-nav hero-nav-prev" type="button" aria-label="Show previous image" @click="showPreviousHero">
      ‹
    </button>

    <button class="hero-image-button" type="button" :aria-label="`Open image: ${hero.alt}`" @click="openLightbox">
      <img class="VPImage image-src" :src="withBase(hero.src)" :alt="hero.alt" loading="eager" decoding="async" />
    </button>

    <button v-if="HERO_IMAGES.length > 1" class="hero-nav hero-nav-next" type="button" aria-label="Show next image" @click="showNextHero">
      ›
    </button>

    <Teleport to="body">
      <div v-if="isLightboxOpen" class="lightbox" role="dialog" aria-modal="true" :aria-label="hero.alt" @click="closeLightbox">
        <button class="lightbox-close" type="button" aria-label="Close image" @click.stop="closeLightbox">×</button>
        <button
          v-if="HERO_IMAGES.length > 1"
          class="lightbox-nav lightbox-nav-prev"
          type="button"
          aria-label="Show previous image"
          @click.stop="showPreviousHero"
        >
          ‹
        </button>
        <div class="lightbox-frame" @click.stop>
          <img class="lightbox-image" :src="withBase(hero.src)" :alt="hero.alt" loading="eager" decoding="async" />
        </div>
        <button
          v-if="HERO_IMAGES.length > 1"
          class="lightbox-nav lightbox-nav-next"
          type="button"
          aria-label="Show next image"
          @click.stop="showNextHero"
        >
          ›
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.random-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 0 0.75rem;
  box-sizing: border-box;
}

.hero-nav {
  position: absolute;
  top: 50%;
  z-index: 3;
  width: 2.4rem;
  height: 2.4rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 1.5rem;
  line-height: 1;
  transform: translateY(-50%);
  cursor: pointer;
  opacity: 1;
  transition: opacity 0.2s ease;
}

.hero-nav-prev {
  left: 0.25rem;
}

.hero-nav-next {
  right: 0.25rem;
}

@media (hover: hover) and (pointer: fine) {
  .hero-nav {
    opacity: 0;
  }

  .random-hero:hover .hero-nav,
  .random-hero:focus-within .hero-nav,
  .hero-nav:hover,
  .hero-nav:focus-visible {
    opacity: 1;
  }
}

@media (min-width: 640px) {
  .random-hero {
    padding: 0 2.5rem;
  }

  .hero-nav-prev {
    left: 0.5rem;
  }

  .hero-nav-next {
    right: 0.5rem;
  }
}

@media (min-width: 960px) {
  .random-hero {
    padding: 0 3.5rem;
  }
}

.hero-image-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
  line-height: 0;
}

.image-src {
  position: static !important;
  top: auto !important;
  left: auto !important;
  transform: none !important;
  object-fit: contain;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 100%;
}

.lightbox {
  position: fixed;
  inset: 0;
  z-index: 2147483647;
  display: grid;
  place-items: center;
  box-sizing: border-box;
  padding: 1rem;
  background: rgb(0 0 0 / 90%);
  cursor: zoom-out;
}

.lightbox-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  border-radius: 0.75rem;
  box-sizing: border-box;
  max-width: calc(100vw - 2rem);
  max-height: calc(100vh - 2rem);
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  box-shadow: 0 1.25rem 3.5rem rgb(0 0 0 / 60%);
  cursor: default;
}

.lightbox-nav {
  position: absolute;
  top: 50%;
  z-index: 2;
  width: 2.6rem;
  height: 2.6rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 1.6rem;
  line-height: 1;
  transform: translateY(-50%);
  cursor: pointer;
}

.lightbox-nav-prev {
  left: max(0.5rem, env(safe-area-inset-left));
}

.lightbox-nav-next {
  right: max(0.5rem, env(safe-area-inset-right));
}

.lightbox-image {
  display: block;
  width: auto;
  height: auto;
  max-width: min(calc(100vw - 3.5rem), 1400px);
  max-height: calc(100vh - 3.5rem);
  border-radius: 0.5rem;
  box-shadow: 0 1rem 3rem rgb(0 0 0 / 50%);
}

.lightbox-close {
  position: absolute;
  top: max(0.75rem, env(safe-area-inset-top));
  right: max(0.75rem, env(safe-area-inset-right));
  width: 2.5rem;
  height: 2.5rem;
  border: 0;
  border-radius: 999px;
  background: rgb(255 255 255 / 92%);
  color: #111;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
}

@media (min-width: 640px) {
  .image-src {
    max-width: 256px;
    max-height: 256px;
  }

  .lightbox {
    padding: 1.5rem;
  }

  .lightbox-frame {
    max-width: calc(100vw - 3rem);
    max-height: calc(100vh - 3rem);
  }

  .lightbox-image {
    max-width: min(calc(100vw - 5rem), 1400px);
    max-height: calc(100vh - 5rem);
  }
}

@media (max-width: 420px) {
  :global(.VPHero .image) {
    margin-top: -40px;
  }

  .random-hero {
    padding: 0 0.25rem;
  }

  .hero-nav {
    width: 2rem;
    height: 2rem;
    font-size: 1.25rem;
  }

  .hero-nav-prev {
    left: 0;
  }

  .hero-nav-next {
    right: 0;
  }

  .image-src {
    max-width: 168px;
    max-height: 168px;
  }

  .lightbox {
    padding: 0.5rem;
  }

  .lightbox-frame {
    padding: 0.5rem;
    max-width: calc(100vw - 1rem);
    max-height: calc(100dvh - 1rem);
  }

  .lightbox-image {
    max-width: min(calc(100vw - 2rem), 1400px);
    max-height: calc(100dvh - 2rem);
  }

  .lightbox-nav {
    width: 2.2rem;
    height: 2.2rem;
    font-size: 1.3rem;
  }

  .lightbox-nav-prev {
    left: 0.25rem;
  }

  .lightbox-nav-next {
    right: 0.25rem;
  }

  .lightbox-close {
    top: 0.5rem;
    right: 0.5rem;
    width: 2.2rem;
    height: 2.2rem;
    font-size: 1.25rem;
  }
}

@media (max-width: 375px) and (max-height: 700px) {
  :global(.VPHero .image) {
    margin-top: -24px;
  }

  .image-src {
    max-width: 156px;
    max-height: 156px;
  }

  .lightbox {
    padding: 0.375rem;
  }

  .lightbox-frame {
    padding: 0.4rem;
    max-width: calc(100vw - 0.75rem);
    max-height: calc(100dvh - 0.75rem);
  }

  .lightbox-image {
    max-width: min(calc(100vw - 1.5rem), 1400px);
    max-height: calc(100dvh - 1.5rem);
  }

  .lightbox-nav {
    width: 2rem;
    height: 2rem;
    font-size: 1.2rem;
  }

  .lightbox-nav-prev {
    left: max(0.125rem, env(safe-area-inset-left));
  }

  .lightbox-nav-next {
    right: max(0.125rem, env(safe-area-inset-right));
  }

  .lightbox-close {
    top: max(0.375rem, env(safe-area-inset-top));
    right: max(0.375rem, env(safe-area-inset-right));
    width: 2rem;
    height: 2rem;
    font-size: 1.15rem;
  }
}

@media (max-width: 320px) and (max-height: 600px) {
  :global(.VPHero .image) {
    margin-top: -10px;
  }

  .image-src {
    max-width: 140px;
    max-height: 140px;
  }

  .hero-nav {
    width: 1.9rem;
    height: 1.9rem;
    font-size: 1.1rem;
  }

  .lightbox {
    padding: 0.25rem;
  }

  .lightbox-frame {
    padding: 0.35rem;
    max-width: calc(100vw - 0.5rem);
    max-height: calc(100dvh - 0.5rem);
  }

  .lightbox-image {
    max-width: min(calc(100vw - 1rem), 1400px);
    max-height: calc(100dvh - 1rem);
  }

  .lightbox-nav {
    width: 1.9rem;
    height: 1.9rem;
    font-size: 1.1rem;
  }

  .lightbox-close {
    width: 1.9rem;
    height: 1.9rem;
    font-size: 1.05rem;
  }
}

@media (min-width: 960px) {
  .image-src {
    max-width: 512px;
    max-height: 512px;
  }
}
</style>
