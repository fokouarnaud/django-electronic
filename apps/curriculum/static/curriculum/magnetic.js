/*
 * Magnetic hover: [data-magnetic] elements lean a few pixels toward the pointer.
 * Only `transform` is touched (compositor-friendly). Skipped for touch pointers
 * and prefers-reduced-motion.
 */
(() => {
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
  const calm = window.matchMedia("(prefers-reduced-motion: no-preference)");
  if (!fine.matches || !calm.matches) return;

  const STRENGTH = 0.15; // fraction of the pointer offset from the element centre
  const MAX = 6; // px

  const clamp = (v) => Math.max(-MAX, Math.min(MAX, v));

  document.querySelectorAll("[data-magnetic]").forEach((el) => {
    el.addEventListener("pointermove", (event) => {
      const rect = el.getBoundingClientRect();
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      el.style.transform = `translate3d(${clamp(dx * STRENGTH)}px, ${clamp(dy * STRENGTH)}px, 0)`;
    });
    el.addEventListener("pointerleave", () => {
      el.style.transform = "";
    });
  });
})();
