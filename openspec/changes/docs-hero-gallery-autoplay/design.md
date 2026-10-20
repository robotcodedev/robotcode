# Design

## Context

`Hero.astro` defines the gallery as the custom element `rc-hero-gallery`: an inline script picks the first picture while the page is parsed, and `#show(index)` switches pictures for the previous and next buttons, swipes and the arrow keys of the enlarged view. During a season the gallery holds only the season's pictures and sets `data-picture-moon` for the decorations (change `docs-halloween-season`).

## Goals / Non-Goals

**Goals:**

- Move on by itself without showing a picture that has not loaded yet.
- Never move while the reader points at the gallery, works in it with the keyboard or looks at the enlarged view.

**Non-Goals:**

- A visible play and pause control or progress dots.
- A different interval during a season.

## Decisions

- One timer per gallery, restarted at the end of `#show`, so that every change, by hand or by itself, gives the picture the full eight seconds; the moon of a season follows without extra code, because the change goes through `#show`.
- When the timer fires and the gallery is busy (pointer over it, `:focus-visible` inside it, enlarged view open, tab hidden), it waits another round. `:focus-visible` instead of any focus, because a mouse click leaves the focus on the next button and would stop the gallery for good.
- The next picture is loaded and decoded with a detached `Image` first; then the picture fades out in 0.3 seconds (`data-fading` on the gallery), is switched and fades back in.
- With reduced motion no timer is started; a change of that setting while the page is open stops it at the next round.

## Risks / Trade-offs

- [WCAG 2.2.2 asks for a way to pause moving content] → pointing at the gallery or focusing it pauses it, and reduced motion stops it; a visible pause control can follow if needed.
- [A poster's slogan needs time to read] → eight seconds per picture, and the pointer holds it.
