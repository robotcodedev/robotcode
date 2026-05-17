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
const suppressNextClick = ref(false);

const SWIPE_MIN_DISTANCE = 48;
const SWIPE_INTENT_DISTANCE = 10;
const SWIPE_DIRECTION_RATIO = 1.35;
const CLICK_SUPPRESSION_TIMEOUT_MS = 250;

type SwipeState = {
  pointerId: number;
  startX: number;
  startY: number;
  isHorizontalIntent: boolean;
};

let activeSwipe: SwipeState | undefined;
let clickSuppressTimeout: ReturnType<typeof setTimeout> | undefined;

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

const suppressClickOnce = () => {
  suppressNextClick.value = true;

  if (clickSuppressTimeout !== undefined) {
    clearTimeout(clickSuppressTimeout);
  }

  clickSuppressTimeout = setTimeout(() => {
    suppressNextClick.value = false;
    clickSuppressTimeout = undefined;
  }, CLICK_SUPPRESSION_TIMEOUT_MS);
};

const consumeSuppressedClick = (event: MouseEvent) => {
  if (!suppressNextClick.value) {
    return false;
  }

  event.preventDefault();
  event.stopPropagation();
  suppressNextClick.value = false;
  return true;
};

const onHeroImageClick = (event: MouseEvent) => {
  if (consumeSuppressedClick(event)) {
    return;
  }

  openLightbox();
};

const onLightboxClick = (event: MouseEvent) => {
  if (consumeSuppressedClick(event)) {
    return;
  }

  closeLightbox();
};

const onSwipePointerDown = (event: PointerEvent) => {
  if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) {
    return;
  }

  activeSwipe = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    isHorizontalIntent: false,
  };

  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
};

const onSwipePointerMove = (event: PointerEvent) => {
  if (activeSwipe === undefined || event.pointerId !== activeSwipe.pointerId) {
    return;
  }

  const deltaX = event.clientX - activeSwipe.startX;
  const deltaY = event.clientY - activeSwipe.startY;

  if (
    !activeSwipe.isHorizontalIntent &&
    Math.abs(deltaX) >= SWIPE_INTENT_DISTANCE &&
    Math.abs(deltaX) > Math.abs(deltaY) * SWIPE_DIRECTION_RATIO
  ) {
    activeSwipe.isHorizontalIntent = true;
  }

  if (activeSwipe.isHorizontalIntent) {
    event.preventDefault();
  }
};

const onSwipePointerUp = (event: PointerEvent) => {
  if (activeSwipe === undefined || event.pointerId !== activeSwipe.pointerId) {
    return;
  }

  const swipe = activeSwipe;
  activeSwipe = undefined;

  const element = event.currentTarget as HTMLElement;
  if (element.hasPointerCapture?.(event.pointerId)) {
    element.releasePointerCapture(event.pointerId);
  }

  const deltaX = event.clientX - swipe.startX;
  const deltaY = event.clientY - swipe.startY;
  const isHorizontalSwipe =
    Math.abs(deltaX) >= SWIPE_MIN_DISTANCE && Math.abs(deltaX) > Math.abs(deltaY) * SWIPE_DIRECTION_RATIO;

  if (!isHorizontalSwipe) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();
  suppressClickOnce();

  if (deltaX > 0) {
    showPreviousHero();
    return;
  }

  showNextHero();
};

const onSwipePointerCancel = (event: PointerEvent) => {
  if (activeSwipe === undefined || event.pointerId !== activeSwipe.pointerId) {
    return;
  }

  activeSwipe = undefined;

  const element = event.currentTarget as HTMLElement;
  if (element.hasPointerCapture?.(event.pointerId)) {
    element.releasePointerCapture(event.pointerId);
  }
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

  if (clickSuppressTimeout !== undefined) {
    clearTimeout(clickSuppressTimeout);
  }
});
</script>

<template>
  <div class="random-hero">
    <button v-if="HERO_IMAGES.length > 1" class="hero-nav hero-nav-prev" type="button" aria-label="Show previous image" @click="showPreviousHero">
      ‹
    </button>

    <button
      class="hero-image-button"
      type="button"
      :aria-label="`Open image: ${hero.alt}`"
      @click="onHeroImageClick"
      @pointerdown="onSwipePointerDown"
      @pointermove="onSwipePointerMove"
      @pointerup="onSwipePointerUp"
      @pointercancel="onSwipePointerCancel"
    >
      <img class="VPImage image-src" :src="withBase(hero.src)" :alt="hero.alt" loading="eager" decoding="async" />
    </button>

    <button v-if="HERO_IMAGES.length > 1" class="hero-nav hero-nav-next" type="button" aria-label="Show next image" @click="showNextHero">
      ›
    </button>

    <Teleport to="body">
      <div
        v-if="isLightboxOpen"
        class="random-hero-lightbox"
        role="dialog"
        aria-modal="true"
        :aria-label="hero.alt"
        @click="onLightboxClick"
      >
        <button class="random-hero-lightbox-close" type="button" aria-label="Close image" @click.stop="closeLightbox">×</button>
        <button
          v-if="HERO_IMAGES.length > 1"
          class="random-hero-lightbox-nav random-hero-lightbox-nav-prev"
          type="button"
          aria-label="Show previous image"
          @click.stop="showPreviousHero"
        >
          ‹
        </button>
        <div
          class="random-hero-lightbox-frame"
          @click.stop
          @pointerdown="onSwipePointerDown"
          @pointermove="onSwipePointerMove"
          @pointerup="onSwipePointerUp"
          @pointercancel="onSwipePointerCancel"
        >
          <img class="random-hero-lightbox-image" :src="withBase(hero.src)" :alt="hero.alt" loading="eager" decoding="async" />
        </div>
        <button
          v-if="HERO_IMAGES.length > 1"
          class="random-hero-lightbox-nav random-hero-lightbox-nav-next"
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
