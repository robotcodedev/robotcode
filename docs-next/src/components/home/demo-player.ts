// <rc-demo>: plays the panels of a home page demo one after another while it is visible.
//
// Markup: panels marked [data-demo-panel] (the first one with class "is-active"), one button marked [data-demo-tab]
// per panel, in the same order, whose --duration says how long its panel stays and which holds a
// .rc-demo-progress bar, an optional [data-demo-pause] button and an optional [data-demo-title] element that shows the
// data-title of the active panel. The styles for the classes set here are in src/styles/home.css.
//
// The next panel starts when the progress bar of the current one has run out, so everything that holds the bar
// (hovering, keyboard focus, the pause button, scrolling the demo out of view, the class "is-holding") holds the
// demo. A video in a panel plays from the start whenever its panel is shown, and pauses while the panel is not shown,
// the demo is paused or out of view. A panel with slides ([data-demo-slide], one [data-demo-slide-tab] each) shows
// them one after another, each for its data-slide-seconds, from the first whenever it is shown, while the demo is
// not held; the last slide stays until the panel changes. A video in a slide plays only while its slide is shown, from
// the start. The window title shows the data-title of the slide. Without motion, panels and slides are only switched
// by hand, the panels show all their steps at once and play no video.
class RcDemo extends HTMLElement {
  #index = 0;
  #panels: HTMLElement[] = [];
  #tabs: HTMLButtonElement[] = [];
  #slide = 0;
  #slideTimer: number | undefined;
  // Whether a panel has been shown: the demo starts with the first one when it first comes into view, unless a panel
  // was chosen before.
  #started = false;

  connectedCallback() {
    this.#panels = [...this.querySelectorAll<HTMLElement>("[data-demo-panel]")];
    this.#tabs = [...this.querySelectorAll<HTMLButtonElement>("[data-demo-tab]")];
    this.#tabs.forEach((tab, index) => tab.addEventListener("click", () => this.#show(index)));
    for (const panel of this.#panels) {
      panel.querySelectorAll("[data-demo-slide-tab]").forEach((tab, index) =>
        tab.addEventListener("click", () => {
          this.#showSlide(index);
          this.#startSlides();
        }),
      );
    }
    this.classList.add("is-ready");

    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    this.classList.add("is-armed");
    const pause = this.querySelector<HTMLButtonElement>("[data-demo-pause]");
    if (pause) {
      pause.hidden = false;
      pause.addEventListener("click", () => {
        const paused = this.classList.toggle("is-paused");
        pause.setAttribute("aria-pressed", String(paused));
        pause.setAttribute("aria-label", paused ? "Play the demo" : "Pause the demo");
        this.#syncVideos();
      });
    }
    for (const tab of this.#tabs) {
      tab.querySelector(".rc-demo-progress")?.addEventListener("animationend", () => {
        this.#show((this.#index + 1) % this.#tabs.length);
      });
    }
    new IntersectionObserver(
      ([entry]) => {
        this.classList.toggle("is-hidden", !entry.isIntersecting);
        if (entry.isIntersecting && !this.#started) {
          this.#show(0);
        } else {
          this.#syncVideos();
        }
      },
      { threshold: 0.3 },
    ).observe(this);
  }

  #show(index: number) {
    this.#started = true;
    this.#index = index;
    this.classList.remove("is-playing");
    this.#panels.forEach((panel, i) => panel.classList.toggle("is-active", i === index));
    this.#tabs.forEach((tab, i) => tab.setAttribute("aria-pressed", String(i === index)));
    this.#setTitle(this.#panels[index].dataset.title);
    // Restarts the step and progress animations, also when the same panel is selected again.
    void this.offsetWidth;
    this.classList.add("is-playing");
    this.#syncVideos(true);
    this.#showSlide(0);
    this.#startSlides();
  }

  #setTitle(text: string | undefined) {
    const title = this.querySelector("[data-demo-title]");
    if (title) title.textContent = text ?? "";
  }

  #showSlide(index: number) {
    const panel = this.#panels[this.#index];
    const slides = panel.querySelectorAll<HTMLElement>("[data-demo-slide]");
    if (slides.length === 0) return;
    this.#slide = index;
    slides.forEach((slide, i) => slide.classList.toggle("is-current", i === index));
    panel
      .querySelectorAll("[data-demo-slide-tab]")
      .forEach((tab, i) => tab.setAttribute("aria-pressed", String(i === index)));
    this.#setTitle(slides[index].dataset.title);
    this.#syncVideos(true);
  }

  #startSlides() {
    clearTimeout(this.#slideTimer);
    const slides = this.#panels[this.#index].querySelectorAll<HTMLElement>("[data-demo-slide]");
    if (slides.length === 0 || !this.classList.contains("is-armed")) return;
    // While the demo is held, the slide's time is up only once the hold ends.
    const next = (seconds: number) => {
      this.#slideTimer = window.setTimeout(() => {
        const held = ["is-paused", "is-hidden", "is-holding"].some((name) => this.classList.contains(name));
        if (held || this.matches(":hover")) return next(0.5);
        if (this.#slide + 1 === slides.length) return;
        this.#showSlide(this.#slide + 1);
        next(Number(slides[this.#slide].dataset.slideSeconds));
      }, seconds * 1000);
    };
    next(Number(slides[this.#slide].dataset.slideSeconds));
  }

  #syncVideos(restart = false) {
    const hold =
      !this.classList.contains("is-armed") ||
      this.classList.contains("is-paused") ||
      this.classList.contains("is-hidden");
    this.#panels.forEach((panel, i) => {
      for (const video of panel.querySelectorAll("video")) {
        const slide = video.closest("[data-demo-slide]");
        if (i !== this.#index || hold || (slide && !slide.classList.contains("is-current"))) {
          video.pause();
          continue;
        }
        if (restart) video.currentTime = 0;
        void video.play().catch(() => {});
      }
    });
  }
}

customElements.define("rc-demo", RcDemo);
