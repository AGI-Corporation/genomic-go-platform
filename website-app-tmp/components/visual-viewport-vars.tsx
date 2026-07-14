"use client";

import { useEffect } from "react";

const viewportVariableNames = [
  "--visual-viewport-width",
  "--visual-viewport-height",
  "--visual-viewport-offset-left",
  "--visual-viewport-offset-top",
  "--visual-viewport-center-x",
  "--visual-viewport-center-y",
  "--keyboard-safe-bottom",
];

export function VisualViewportVars() {
  useEffect(() => {
    const root = document.documentElement;
    let frame = 0;

    const update = () => {
      const viewport = window.visualViewport;
      const width = viewport?.width ?? window.innerWidth;
      const height = viewport?.height ?? window.innerHeight;
      const offsetLeft = viewport?.offsetLeft ?? 0;
      const offsetTop = viewport?.offsetTop ?? 0;
      const keyboardSafeBottom = Math.max(0, window.innerHeight - height - offsetTop);

      root.style.setProperty("--visual-viewport-width", `${width}px`);
      root.style.setProperty("--visual-viewport-height", `${height}px`);
      root.style.setProperty("--visual-viewport-offset-left", `${offsetLeft}px`);
      root.style.setProperty("--visual-viewport-offset-top", `${offsetTop}px`);
      root.style.setProperty("--visual-viewport-center-x", `${offsetLeft + width / 2}px`);
      root.style.setProperty("--visual-viewport-center-y", `${offsetTop + height / 2}px`);
      root.style.setProperty("--keyboard-safe-bottom", `${keyboardSafeBottom}px`);
    };

    const scheduleUpdate = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(update);
    };

    update();
    window.addEventListener("resize", scheduleUpdate);
    window.addEventListener("orientationchange", scheduleUpdate);
    window.visualViewport?.addEventListener("resize", scheduleUpdate);
    window.visualViewport?.addEventListener("scroll", scheduleUpdate);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", scheduleUpdate);
      window.removeEventListener("orientationchange", scheduleUpdate);
      window.visualViewport?.removeEventListener("resize", scheduleUpdate);
      window.visualViewport?.removeEventListener("scroll", scheduleUpdate);
      for (const name of viewportVariableNames) {
        root.style.removeProperty(name);
      }
    };
  }, []);

  return null;
}
