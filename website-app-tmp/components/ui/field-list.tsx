"use client";

import {
  forwardRef,
  type HTMLAttributes,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  type FieldLayoutContext,
  fieldLayoutClassName,
  resolveFieldLayoutSize,
} from "@/components/ui/field-list-layout";
import { FieldValuePopover } from "@/components/ui/field-value-popover";
import { cn } from "@/lib/utils";
import type { DataField, DataValue } from "@/components/ui/data-types";

export const FieldListGrid = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "grid w-full grid-cols-1 gap-x-5 gap-y-4 sm:grid-cols-2 xl:grid-cols-3",
        className,
      )}
      {...props}
    />
  ),
);
FieldListGrid.displayName = "FieldListGrid";

type FieldListItemFrameProps = {
  label: string;
  children: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

export const FieldListItemFrame = forwardRef<HTMLDivElement, FieldListItemFrameProps>(
  ({ label, children, className, ...props }, ref) => (
    <div ref={ref} className={cn("min-w-0 space-y-1", className)} {...props}>
      <p className="truncate text-xs font-normal leading-4 text-tertiary-foreground">{label}</p>
      <div className="min-w-0 text-sm leading-5">{children}</div>
    </div>
  ),
);
FieldListItemFrame.displayName = "FieldListItemFrame";

function hasFieldValue(value: unknown): boolean {
  if (value == null || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function parsePixelTrackList(value: string) {
  if (!value || value === "none") return [];
  return value
    .split(/\s+/)
    .map((track) => Number.parseFloat(track))
    .filter((track) => Number.isFinite(track) && track > 0);
}

function roundLayoutNumber(value: number) {
  return Math.round(value * 100) / 100;
}

function readFieldListLayoutContext(node: HTMLDivElement): FieldLayoutContext | null {
  const style = window.getComputedStyle(node);
  const columns = parsePixelTrackList(style.gridTemplateColumns);
  if (columns.length === 0) return null;
  const columnWidth = Math.min(...columns);
  return {
    columnCount: columns.length,
    columnWidth: roundLayoutNumber(columnWidth),
    columnGap: roundLayoutNumber(Number.parseFloat(style.columnGap) || 0),
  };
}

function sameLayoutContext(
  current: FieldLayoutContext | undefined,
  next: FieldLayoutContext | null,
) {
  if (!current || !next) return current === undefined && next === null;
  return (
    current.columnCount === next.columnCount &&
    current.columnWidth === next.columnWidth &&
    current.columnGap === next.columnGap
  );
}

function useFieldListLayoutContext() {
  const gridRef = useRef<HTMLDivElement | null>(null);
  const [layoutContext, setLayoutContext] = useState<FieldLayoutContext>();

  useEffect(() => {
    const node = gridRef.current;
    if (!node) return;

    const updateLayoutContext = () => {
      const next = readFieldListLayoutContext(node);
      setLayoutContext((current) =>
        sameLayoutContext(current, next) ? current : (next ?? undefined),
      );
    };

    updateLayoutContext();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateLayoutContext);
      return () => window.removeEventListener("resize", updateLayoutContext);
    }

    const observer = new ResizeObserver(updateLayoutContext);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return { gridRef, layoutContext };
}

export function FieldList({
  fields,
  values,
  displayCount = 999,
  className,
  onFieldCommit,
}: {
  fields: DataField[];
  values: Record<string, DataValue>;
  displayCount?: number;
  className?: string;
  onFieldCommit?: (field: DataField, value: DataValue) => void | Promise<void>;
}) {
  const visibleFields = useMemo(
    () => fields.filter((field) => field.required || hasFieldValue(values[field.key])),
    [fields, values],
  );
  const { gridRef, layoutContext } = useFieldListLayoutContext();

  if (visibleFields.length === 0) return null;

  return (
    <FieldListGrid ref={gridRef} className={className}>
      {visibleFields.map((field) => {
        const value = values[field.key];
        const size = resolveFieldLayoutSize(field, value, layoutContext);
        return (
          <FieldListItemFrame
            key={field.key}
            label={field.label}
            className={fieldLayoutClassName(size)}
          >
            <FieldValuePopover
              value={value}
              field={field}
              displayCount={displayCount}
              onCommit={onFieldCommit ? (nextValue) => onFieldCommit(field, nextValue) : undefined}
              variant="field-list"
            />
          </FieldListItemFrame>
        );
      })}
    </FieldListGrid>
  );
}
