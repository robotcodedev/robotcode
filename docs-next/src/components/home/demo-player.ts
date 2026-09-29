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
// the demo is paused or out of view. Without motion, the panels are only switched by hand, show all their steps at
// once and play no video.
class RcDemo extends HTMLElement {
  #index = 0;
  #panels: HTMLElement[] = [];
  #tabs: HTMLButtonElement[] = [];

  connectedCallback() {
    this.#panels = [...this.querySelectorAll<HTMLElement>("[data-demo-panel]")];
    this.#tabs = [...this.querySelectorAll<HTMLButtonElement>("[data-demo-tab]")];
    this.#tabs.forEach((tab, index) => tab.addEventListener("click", () => this.#show(index)));
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
    let started = false;
    new IntersectionObserver(
      ([entry]) => {
        this.classList.toggle("is-hidden", !entry.isIntersecting);
        if (entry.isIntersecting && !started) {
          started = true;
          this.#show(0);
        } else {
          this.#syncVideos();
        }
      },
      { threshold: 0.3 },
    ).observe(this);
  }

  #show(index: number) {
    this.#index = index;
    this.classList.remove("is-playing");
    this.#panels.forEach((panel, i) => panel.classList.toggle("is-active", i === index));
    this.#tabs.forEach((tab, i) => tab.setAttribute("aria-pressed", String(i === index)));
    const title = this.querySelector("[data-demo-title]");
    if (title) title.textContent = this.#panels[index].dataset.title ?? "";
    // Restarts the step and progress animations, also when the same panel is selected again.
    void this.offsetWidth;
    this.classList.add("is-playing");
    this.#syncVideos(true);
  }

  #syncVideos(restart = false) {
    const hold =
      !this.classList.contains("is-armed") ||
      this.classList.contains("is-paused") ||
      this.classList.contains("is-hidden");
    this.#panels.forEach((panel, i) => {
      for (const video of panel.querySelectorAll("video")) {
        if (i !== this.#index || hold) {
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
