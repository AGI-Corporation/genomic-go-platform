"use client";

import { Link2 } from "lucide-react";
import { Fragment } from "react";
import { Badge } from "@/components/ui/badge";
import { type OverflowItem, OverflowList } from "@/components/ui/overflow-list";
import { cn } from "@/lib/utils";
import {
  ATTACH_FONT,
  BADGE_GAP,
  fieldAvailableWidth,
  measureTextWidth,
  primitiveLabel,
  toArray,
  visibleItemCount,
  type FieldValueViewProps,
} from "./shared";

const RELATION_FIXED_WIDTH = 12 + 4 + 16;

export function RelationFieldView({
  value,
  field,
  cellWidth,
  availableWidth,
  displayCount,
  className,
}: FieldValueViewProps) {
  const values = toArray(value);
  const resolvedAvailableWidth = fieldAvailableWidth(cellWidth, availableWidth);
  const labelField = field.config?.relation_label_field;
  const items: OverflowItem[] = values.map((item, index) => ({
    key: `${primitiveLabel(item, labelField)}-${index}`,
    element: (
      <Badge variant="outline" className="max-w-[148px] justify-start rounded-sm px-2 py-1 text-xs font-normal">
        <Link2 className="icon-12 shrink-0 text-muted-foreground" />
        <span className="truncate">{primitiveLabel(item, labelField)}</span>
      </Badge>
    ),
  }));
  const visibleCount = visibleItemCount({
    itemWidths: values.map((item) => {
      const textWidth = Math.min(measureTextWidth(primitiveLabel(item, labelField), ATTACH_FONT), 120);
      return RELATION_FIXED_WIDTH + textWidth;
    }),
    availableWidth: resolvedAvailableWidth,
    gap: BADGE_GAP,
    displayCount: displayCount ?? (resolvedAvailableWidth == null ? field.config?.max_visible ?? 2 : undefined),
  });
  if (visibleCount >= items.length) {
    return (
      <span className={cn("flex min-w-0 flex-wrap items-center gap-1 overflow-hidden", className)}>
        {items.map((item) => (
          <Fragment key={item.key}>{item.element}</Fragment>
        ))}
      </span>
    );
  }
  return (
    <OverflowList
      items={items}
      visibleCount={visibleCount}
      className={className}
      renderPopoverContent={(hidden) => (
        <div className="flex flex-wrap items-center gap-1">
          {hidden.map((item) => (
            <span key={item.key} className="inline-flex items-center leading-none">
              {item.element}
            </span>
          ))}
        </div>
      )}
    />
  );
}
