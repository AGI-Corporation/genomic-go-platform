"use client";

import { ContextMenu as ContextMenuPrimitive } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

function ContextMenu({ ...props }: React.ComponentProps<typeof ContextMenuPrimitive.Root>) {
  return <ContextMenuPrimitive.Root data-slot="context-menu" {...props} />;
}

function ContextMenuTrigger({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Trigger>) {
  return <ContextMenuPrimitive.Trigger data-slot="context-menu-trigger" {...props} />;
}

type ContextMenuContentProps = React.ComponentProps<typeof ContextMenuPrimitive.Content> & {
  "data-expand-direction"?: "down";
};

function ContextMenuContent({
  className,
  collisionPadding = 12,
  "data-expand-direction": expandDirection,
  onCloseAutoFocus,
  ...props
}: ContextMenuContentProps) {
  const expandsDown = expandDirection === "down";

  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.Content
        data-slot="context-menu-content"
        data-expand-direction={expandDirection}
        collisionPadding={collisionPadding}
        onCloseAutoFocus={onCloseAutoFocus ?? ((e) => e.preventDefault())}
        className={cn(
          "z-50 max-h-(--radix-context-menu-content-available-height) min-w-[8rem] overflow-x-hidden overflow-y-auto rounded-lg border bg-popover p-1 text-popover-foreground shadow-md data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
          expandsDown
            ? "origin-top-left data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-top-2 data-[side=right]:slide-in-from-top-2 data-[side=top]:slide-in-from-top-2"
            : "origin-(--radix-context-menu-content-transform-origin) data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
          className,
        )}
        {...props}
      />
    </ContextMenuPrimitive.Portal>
  );
}

function ContextMenuItem({
  className,
  inset,
  variant = "default",
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Item> & {
  inset?: boolean;
  variant?: "default" | "destructive";
}) {
  return (
    <ContextMenuPrimitive.Item
      data-slot="context-menu-item"
      data-inset={inset}
      data-variant={variant}
      className={cn(
        "relative flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-popover-foreground outline-hidden select-none dark:text-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[inset]:pl-8 focus:shadow-[inset_0_0_0_9999px_var(--press-overlay)] data-[variant=destructive]:hover:bg-destructive/10 data-[variant=destructive]:hover:text-destructive data-[variant=destructive]:focus:bg-destructive/10 data-[variant=destructive]:focus:text-destructive data-[variant=destructive]:data-[highlighted]:bg-destructive/10 data-[variant=destructive]:data-[highlighted]:text-destructive dark:data-[variant=destructive]:hover:bg-destructive/20 dark:data-[variant=destructive]:focus:bg-destructive/20 dark:data-[variant=destructive]:data-[highlighted]:bg-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-muted-foreground dark:[&_svg:not([class*='text-'])]:text-foreground/75 data-[variant=destructive]:hover:*:[svg]:text-destructive! data-[variant=destructive]:focus:*:[svg]:text-destructive! data-[variant=destructive]:data-[highlighted]:*:[svg]:text-destructive!",
        className,
      )}
      {...props}
    />
  );
}

export { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger };
