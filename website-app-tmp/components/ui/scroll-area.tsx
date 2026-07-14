import { ScrollArea as ScrollAreaPrimitive } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

type FadeTopConfig = boolean | { offset?: number; height?: number; visibleAfter?: number };
type FadeBottomConfig = boolean | { height?: number };
type FadeLeftConfig = boolean | { width?: number };
type FadeRightConfig = boolean | { width?: number };

export const DEFAULT_FADE_HEIGHT = 48;
const DEFAULT_FADE_WIDTH = 48;
const DEFAULT_FADE_COLOR = "var(--background)";

interface ScrollAreaProps extends React.ComponentProps<typeof ScrollAreaPrimitive.Root> {
  /**
   * Forwarded to the Radix Viewport. Pass when consumers need to read
   * scrollTop / scrollHeight, attach IntersectionObserver with
   * `root: viewport`, or call `scrollIntoView`.
   */
  viewportRef?: React.RefObject<HTMLDivElement | null>;
  /**
   * className applied to the Viewport (the actual scrolling element).
   * Use for properties that must live on the scroll element itself,
   * e.g. `scroll-pt-24`, `overflow-x-hidden`.
   */
  viewportClassName?: string;
  /**
   * Inline style applied to the Viewport (the actual scrolling element).
   * Use sparingly for runtime scroll mechanics that must survive re-renders.
   */
  viewportStyle?: React.CSSProperties;
  /**
   * Bottom fading edge — always-on scroll affordance ("more content below").
   * Pure CSS, no listener. Pass `{ height: N }` to override the gradient
   * height (default 48px).
   */
  fadeBottom?: FadeBottomConfig;
  /**
   * Left fading edge — scroll-aware, visible only when `scrollLeft > 0`.
   * Pass `{ width: N }` to override the gradient width (default 48px).
   */
  fadeLeft?: FadeLeftConfig;
  /**
   * Right fading edge — scroll-aware, visible only when there is more
   * horizontal content past the right edge. Pass `{ width: N }` to override
   * the gradient width (default 48px).
   */
  fadeRight?: FadeRightConfig;
  /**
   * Top fading edge — scroll-aware, visible only after the configured scroll threshold.
   * Pass `{ offset: N }` to position the gradient below a sticky header
   * (offset = sticky element height in px). Pass `{ visibleAfter: N }` to
   * keep it hidden until `scrollTop > N`, for example after a sticky header
   * reaches the top. Pass `{ height: N }` to override the gradient height
   * (default 48px). `true` is shorthand for offset 0 with default height.
   */
  fadeTop?: FadeTopConfig;
  /**
   * CSS color value used as the solid end of the fade gradient. Defaults
   * to `var(--background)`. Override when the ScrollArea sits on a
   * non-background surface — e.g. `var(--card)` for the sidebar — so the
   * gradient blends correctly with the visible backdrop. Both edges share
   * the same color since the fade matches the surface, not the edge.
   */
  fadeColor?: string;
}

function ScrollArea({
  className,
  children,
  viewportRef,
  viewportClassName,
  viewportStyle,
  fadeBottom,
  fadeLeft,
  fadeRight,
  fadeTop,
  fadeColor = DEFAULT_FADE_COLOR,
  ...props
}: ScrollAreaProps) {
  const internalRef = React.useRef<HTMLDivElement>(null);
  const effectiveViewportRef = viewportRef ?? internalRef;
  const fadeTopOffset = typeof fadeTop === "object" ? (fadeTop.offset ?? 0) : 0;
  const fadeTopVisibleAfter = typeof fadeTop === "object" ? (fadeTop.visibleAfter ?? 0) : 0;
  const fadeTopHeight =
    typeof fadeTop === "object" ? (fadeTop.height ?? DEFAULT_FADE_HEIGHT) : DEFAULT_FADE_HEIGHT;
  const fadeBottomHeight =
    typeof fadeBottom === "object"
      ? (fadeBottom.height ?? DEFAULT_FADE_HEIGHT)
      : DEFAULT_FADE_HEIGHT;
  const fadeLeftWidth =
    typeof fadeLeft === "object" ? (fadeLeft.width ?? DEFAULT_FADE_WIDTH) : DEFAULT_FADE_WIDTH;
  const fadeRightWidth =
    typeof fadeRight === "object" ? (fadeRight.width ?? DEFAULT_FADE_WIDTH) : DEFAULT_FADE_WIDTH;

  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative overflow-hidden", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        ref={effectiveViewportRef}
        data-slot="scroll-area-viewport"
        // The `[&>div]:!*` overrides target the Radix-internal measurement
        // wrapper that sits between Viewport and our children. Radix renders
        // it as `<div style="display: table; min-width: 100%">` so it can
        // size to content for measurement — but `display: table` then sizes
        // to *intrinsic* content width, which makes any unbreakable child
        // (long URL, code block, fixed-width element) push the wrapper
        // wider than the viewport and break the surrounding flex layout.
        // We force it back to `display: block` and let it follow the
        // viewport width. The selector depends on Radix's current internal
        // structure (first DOM child of Viewport); if Radix ever wraps in a
        // different element these overrides become no-ops, but they will
        // not produce wrong layout.
        className={cn(
          "size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1",
          "[&>div]:!block [&>div]:!w-full [&>div]:!min-w-0",
          viewportClassName,
        )}
        style={viewportStyle}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      {fadeTop ? (
        <FadingEdgeOverlay
          edge="top"
          offset={fadeTopOffset}
          height={fadeTopHeight}
          visibleAfter={fadeTopVisibleAfter}
          color={fadeColor}
          viewportRef={effectiveViewportRef}
        />
      ) : null}
      {fadeBottom ? (
        <FadingEdgeOverlay
          edge="bottom"
          height={fadeBottomHeight}
          color={fadeColor}
          viewportRef={effectiveViewportRef}
        />
      ) : null}
      {fadeLeft ? (
        <FadingEdgeOverlay
          edge="left"
          width={fadeLeftWidth}
          color={fadeColor}
          viewportRef={effectiveViewportRef}
        />
      ) : null}
      {fadeRight ? (
        <FadingEdgeOverlay
          edge="right"
          width={fadeRightWidth}
          color={fadeColor}
          viewportRef={effectiveViewportRef}
        />
      ) : null}
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  );
}

function FadingEdgeOverlay({
  edge,
  offset = 0,
  height = DEFAULT_FADE_HEIGHT,
  width = DEFAULT_FADE_WIDTH,
  visibleAfter = 0,
  color = DEFAULT_FADE_COLOR,
  viewportRef,
}: {
  edge: "top" | "bottom" | "left" | "right";
  offset?: number;
  height?: number;
  width?: number;
  visibleAfter?: number;
  color?: string;
  viewportRef?: React.RefObject<HTMLDivElement | null>;
}) {
  // Both fades are scroll-aware affordances ("there's more above" / "there's
  // more below"). Each hides when the corresponding edge of the scrollable
  // area is already at the viewport edge — there's nothing left to fade
  // INTO and the gradient would otherwise just visually clip the last/first
  // bit of real content.
  //
  //   • Top fade  · hidden at `scrollTop === 0` (nothing scrolled above).
  //     Without this it would overlap the sticky header before any content
  //     had been pinned, and on first paint the very first row would look
  //     muted for no reason.
  //   • Bottom fade · hidden when `scrollTop + clientHeight >= scrollHeight`
  //     within a sub-pixel epsilon (nothing scrolled below). The "thinking
  //     strip" / latest-message tail used to slide INTO this gradient when
  //     auto-scroll pinned the user to the bottom — the user reported
  //     reading "Thinking" content fade out at the bottom of the viewport
  //     even though they were already at the latest position. With the
  //     scroll-aware hide, the gradient only appears when there is actually
  //     content past the bottom edge to telegraph, and disappears the
  //     moment auto-scroll-to-bottom lands the user at the tail.
  //
  // Default = visible so the very first paint (before refs / scroll listeners
  // attach) doesn't briefly show unstyled content; the effect immediately
  // recomputes after mount.
  const [visible, setVisible] = React.useState(true);

  React.useEffect(() => {
    const viewport = viewportRef?.current;
    if (!viewport) return;
    const update = () => {
      if (edge === "top") {
        setVisible(viewport.scrollTop > visibleAfter);
        return;
      }
      if (edge === "bottom") {
        // 1px epsilon absorbs sub-pixel rounding from auto-scroll-to-bottom
        // (browsers occasionally land at e.g. 0.5px short of the bottom even
        // after a clean `scrollIntoView`/`scrollTop = maxScrollTop`).
        const distanceFromBottom =
          viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
        setVisible(distanceFromBottom > 1);
        return;
      }
      if (edge === "left") {
        setVisible(viewport.scrollLeft > 0);
        return;
      }
      const distanceFromRight = viewport.scrollWidth - viewport.scrollLeft - viewport.clientWidth;
      setVisible(distanceFromRight > 1);
    };
    update();
    viewport.addEventListener("scroll", update, { passive: true });
    // Content reflow (streaming tokens, image loads, agent bubbles arriving)
    // changes scrollHeight without firing a scroll event. ResizeObserver on
    // the viewport AND its content child catches both kinds of growth so
    // the gradient flips back on the moment new content lands below.
    if (typeof ResizeObserver === "undefined") {
      return () => {
        viewport.removeEventListener("scroll", update);
      };
    }
    const ro = new ResizeObserver(update);
    ro.observe(viewport);
    const inner = viewport.firstElementChild;
    if (inner) ro.observe(inner);
    return () => {
      viewport.removeEventListener("scroll", update);
      ro.disconnect();
    };
  }, [edge, viewportRef, visibleAfter]);

  // Inline gradient (instead of Tailwind utility classes) so callers can
  // pass any CSS color — `var(--card)`, `var(--surface)`, `#fafbf8`, etc.
  // Multiple alpha stops approximate an ease-in-out fade: the edge eases
  // away gently at both ends with a faster transition through the middle.
  const direction =
    edge === "top"
      ? "to bottom"
      : edge === "bottom"
        ? "to top"
        : edge === "left"
          ? "to right"
          : "to left";
  const gradient = `linear-gradient(${direction}, ${color} 0%, color-mix(in oklab, ${color} 94%, transparent) 12%, color-mix(in oklab, ${color} 74%, transparent) 32%, color-mix(in oklab, ${color} 26%, transparent) 68%, color-mix(in oklab, ${color} 6%, transparent) 88%, transparent 100%)`;

  const style: React.CSSProperties = (() => {
    if (edge === "top") return { top: offset, height, backgroundImage: gradient };
    if (edge === "bottom") return { bottom: 0, height, backgroundImage: gradient };
    if (edge === "left") return { left: 0, top: 0, bottom: 0, width, backgroundImage: gradient };
    return { right: 0, top: 0, bottom: 0, width, backgroundImage: gradient };
  })();

  return (
    <div
      aria-hidden
      data-slot={`scroll-area-fade-${edge}`}
      className={cn(
        "pointer-events-none absolute z-20 transition-opacity duration-150",
        (edge === "top" || edge === "bottom") && "inset-x-0",
        visible ? "opacity-100" : "opacity-0",
      )}
      style={style}
    />
  );
}

function ScrollBar({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>) {
  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot="scroll-area-scrollbar"
      orientation={orientation}
      className={cn(
        "z-50 flex touch-none p-px transition-colors select-none",
        orientation === "vertical" && "h-full w-2.5 border-l border-l-transparent",
        orientation === "horizontal" && "h-2.5 flex-col border-t border-t-transparent",
        className,
      )}
      {...props}
    >
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot="scroll-area-thumb"
        className="relative flex-1 rounded-full bg-border"
      />
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  );
}

export { ScrollArea, ScrollBar };
