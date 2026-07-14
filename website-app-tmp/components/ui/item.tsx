import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

const itemVariants = cva(
  "group/item relative flex w-full items-center gap-3 overflow-hidden rounded-lg border-[0.5px] border-border bg-background text-sm outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring-subtle",
  {
    variants: {
      variant: {
        default: "",
        ghost: "bg-transparent",
        muted: "bg-card",
      },
      size: {
        default: "p-3",
        sm: "px-3 py-2",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

type ItemProps = React.ComponentProps<"div"> &
  VariantProps<typeof itemVariants> & {
    asChild?: boolean;
  };

function Item({ className, variant, size, asChild = false, ...props }: ItemProps) {
  const Comp = asChild ? Slot.Root : "div";
  return (
    <Comp
      data-slot="item"
      data-variant={variant ?? "default"}
      data-size={size ?? "default"}
      className={cn(itemVariants({ variant, size }), className)}
      {...props}
    />
  );
}

function ItemGroup({ className, ...props }: React.ComponentProps<"ul">) {
  return (
    <ul data-slot="item-group" className={cn("flex list-none flex-col", className)} {...props} />
  );
}

function ItemSeparator({ className, ...props }: React.ComponentProps<"hr">) {
  return (
    <hr
      data-slot="item-separator"
      className={cn("my-0 border-t-[0.5px] border-border", className)}
      {...props}
    />
  );
}

function ItemMedia({
  className,
  variant = "default",
  ...props
}: React.ComponentProps<"div"> & { variant?: "default" | "icon" | "image" }) {
  return (
    <div
      data-slot="item-media"
      data-variant={variant}
      className={cn(
        "flex shrink-0 items-center justify-center",
        variant === "icon" && "size-5 text-tertiary-foreground [&>svg]:size-5",
        variant === "image" &&
          "size-8 overflow-hidden rounded bg-card [&>img]:size-full [&>img]:object-cover",
        className,
      )}
      {...props}
    />
  );
}

function ItemContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-content"
      className={cn("flex min-w-0 flex-1 flex-col gap-2", className)}
      {...props}
    />
  );
}

function ItemTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-title"
      className={cn(
        "flex items-center gap-2 text-sm font-semibold leading-5 tracking-[-0.01em] text-foreground",
        className,
      )}
      {...props}
    />
  );
}

function ItemDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-description"
      className={cn("text-sm leading-5 text-muted-foreground [&_p]:leading-5", className)}
      {...props}
    />
  );
}

function ItemHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-header"
      className={cn(
        "relative w-full overflow-hidden bg-muted [&>img]:block [&>img]:w-full [&>img]:object-cover",
        className,
      )}
      {...props}
    />
  );
}

function ItemFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-footer"
      className={cn("mt-1 flex items-center gap-2 text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}

function ItemActions({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-actions"
      className={cn(
        "ml-auto flex size-8 shrink-0 items-center justify-center gap-1.5 rounded text-tertiary-foreground transition-colors hover:bg-hover-overlay hover:text-foreground",
        className,
      )}
      {...props}
    />
  );
}

export {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemFooter,
  ItemGroup,
  ItemHeader,
  ItemMedia,
  ItemSeparator,
  ItemTitle,
  itemVariants,
};
