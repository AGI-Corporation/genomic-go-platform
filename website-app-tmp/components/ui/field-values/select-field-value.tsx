"use client";

import { Fragment } from "react";
import { type OverflowItem, OverflowList } from "@/components/ui/overflow-list";
import { cn } from "@/lib/utils";
import type { DataValue } from "@/components/ui/data-types";
import { FieldEditOptionList } from "./edit-option-list";
import {
  BADGE_FONT,
  BADGE_GAP,
  BADGE_H_PAD,
  fieldAvailableWidth,
  measureTextWidth,
  OptionBadge,
  selectOption,
  toArray,
  visibleItemCount,
  type FieldValueEditProps,
  type FieldValueViewProps,
} from "./shared";

export function SelectFieldView({
  value,
  field,
}: FieldValueViewProps) {
  return <OptionBadge option={selectOption(field, value)} />;
}

export function MultiSelectFieldView({
  value,
  field,
  cellWidth,
  availableWidth,
  displayCount,
  wrapText = true,
  overflowBadgeTrigger = "button",
  className,
}: FieldValueViewProps) {
  const values = toArray(value);
  const resolvedAvailableWidth = fieldAvailableWidth(cellWidth, availableWidth);
  const items: OverflowItem[] = values.map((item, index) => {
    const option = selectOption(field, item);
    return {
      key: `${option.id}-${index}`,
      element: <OptionBadge option={option} />,
    };
  });
  const visibleCount = visibleItemCount({
    itemWidths: values.map((item) => measureTextWidth(selectOption(field, item).label, BADGE_FONT) + BADGE_H_PAD),
    availableWidth: resolvedAvailableWidth,
    gap: BADGE_GAP,
    displayCount: displayCount ?? (resolvedAvailableWidth == null ? field.config?.max_visible : undefined),
  });
  if (visibleCount >= items.length) {
    return (
      <span className={cn("flex min-w-0 items-center gap-1 overflow-hidden", wrapText ? "flex-wrap" : "flex-nowrap", className)}>
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
      overflowBadgeTrigger={overflowBadgeTrigger}
      overflowBadgeClassName={overflowBadgeTrigger === "span" ? "cursor-pointer" : undefined}
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

export function SelectFieldEdit({ value, field, onChange, onCommit, autoFocus, presentation }: FieldValueEditProps) {
  const current = String(value ?? "");
  const options = field.config?.options ?? [];
  return (
    <FieldEditOptionList
      searchPlaceholder="Search options"
      autoFocusSearch={autoFocus}
      variant={presentation}
      items={options.map((option) => {
        const selected = option.id === current || option.label === current;
        return {
          id: option.id,
          label: option.label,
          selected,
          content: <OptionBadge option={selectOption(field, option.id)} />,
          onSelect: () => {
            onChange(option.id);
            onCommit(option.id);
          },
        };
      })}
    />
  );
}

export function MultiSelectFieldEdit({ value, field, onChange, onCommit, autoFocus, presentation }: FieldValueEditProps) {
  const selected = new Set(toArray(value).map((item) => String(item)));
  const options = field.config?.options ?? [];
  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    const nextValue = [...next] as DataValue;
    onChange(nextValue);
    return nextValue;
  };
  return (
    <FieldEditOptionList
      searchPlaceholder="Search options"
      autoFocusSearch={autoFocus}
      variant={presentation}
      onKeyDown={(event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          onCommit([...selected]);
        }
      }}
      items={options.map((option) => {
        const isSelected = selected.has(option.id) || selected.has(option.label);
        return {
          id: option.id,
          label: option.label,
          selected: isSelected,
          content: <OptionBadge option={selectOption(field, option.id)} />,
          onSelect: () => {
            toggle(option.id);
          },
        };
      })}
    />
  );
}
