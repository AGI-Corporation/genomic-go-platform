"use client";

import { Popover as PopoverPrimitive } from "radix-ui";
import { Fragment, type ReactNode, useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export interface OverflowItem {
  key: string;
  element: ReactNode;
}

interface OverflowListProps {
  items: OverflowItem[];
  visibleCount: number;
  renderPopoverContent: (hiddenItems: OverflowItem[]) => ReactNode;
  gap?: number;
  className?: string;
  overflowBadgeClassName?: string;
  overflowBadgeTrigger?: "button" | "span";
}

export function OverflowList({
  items,
  visibleCount,
  renderPopoverContent,
  gap = 4,
  className,
  overflowBadgeClassName,
  overflowBadgeTrigger = "button",
}: OverflowListProps) {
  const clamped = Math.max(1, Math.min(visibleCount, items.length));
  const hiddenItems = items.slice(clamped);
  const visibleItems = items.slice(0, clamped);
  const hasOverflow = hiddenItems.length > 0;

  return (
    <span className={cn("flex items-center overflow-hidden", className)} style={{ gap }}>
      {visibleItems.map((item) => (
        <Fragment key={item.key}>{item.element}</Fragment>
      ))}
      {hasOverflow ? (
        <OverflowBadge
          count={hiddenItems.length}
          className={overflowBadgeClassName}
          trigger={overflowBadgeTrigger}
        >
          {renderPopoverContent(hiddenItems)}
        </OverflowBadge>
      ) : null}
    </span>
  );
}

function OverflowBadge({
  count,
  children,
  className,
  trigger,
}: {
  count: number;
  children: ReactNode;
  className?: string;
  trigger: "button" | "span";
}) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleOpen = useCallback(() => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    setOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    closeTimer.current = setTimeout(() => setOpen(false), 150);
  }, []);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        {trigger === "button" ? (
          <button
            type="button"
            className={cn(
              "inline-flex shrink-0 cursor-default items-center self-center rounded-[6px] bg-muted px-1.5 py-0.5 text-xs font-semibold leading-4 text-muted-foreground outline-hidden",
              className,
            )}
            onMouseEnter={handleOpen}
            onMouseLeave={handleClose}
          >
            +{count}
          </button>
        ) : (
          <span
            className={cn(
              "inline-flex shrink-0 cursor-default items-center self-center rounded-[6px] bg-muted px-1.5 py-0.5 text-xs font-semibold leading-4 text-muted-foreground outline-hidden",
              className,
            )}
            onMouseEnter={handleOpen}
            onMouseLeave={handleClose}
          >
            +{count}
          </span>
        )}
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="bottom"
          align="start"
          sideOffset={4}
          className="z-50 max-h-60 max-w-80 overflow-auto rounded-md border bg-popover p-2 text-popover-foreground shadow-md outline-hidden data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"
          onMouseEnter={handleOpen}
          onMouseLeave={handleClose}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
        >
          {children}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
