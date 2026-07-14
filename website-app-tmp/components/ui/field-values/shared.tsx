"use client";

import { Fragment } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DataField, DataUserOption, DataValue } from "@/components/ui/data-types";

export type CommitFieldValue = (value: DataValue) => void;

export interface FieldValueViewProps {
  value: DataValue | undefined;
  field: DataField;
  cellWidth?: number;
  availableWidth?: number;
  displayCount?: number;
  wrapText?: boolean;
  overflowBadgeTrigger?: "button" | "span";
  className?: string;
}

export interface FieldValueEditProps {
  value: DataValue | undefined;
  field: DataField;
  onChange: (value: DataValue) => void;
  onCommit: (value: DataValue) => void;
  autoFocus?: boolean;
  presentation?: "popover" | "sheet";
}

export const OPTION_COLORS: Record<string, { bg: string; text: string }> = {
  blue: { bg: "bg-palette-blue-bg", text: "text-palette-blue-fg" },
  purple: { bg: "bg-palette-purple-bg", text: "text-palette-purple-fg" },
  green: { bg: "bg-palette-kylon-bg", text: "text-palette-kylon-fg" },
  amber: { bg: "bg-palette-brown-bg", text: "text-palette-brown-fg" },
  rose: { bg: "bg-destructive-subtle", text: "text-destructive" },
  red: { bg: "bg-destructive-subtle", text: "text-destructive" },
  cyan: { bg: "bg-palette-mint-bg", text: "text-palette-mint-fg" },
  indigo: { bg: "bg-info-subtle", text: "text-info" },
  orange: { bg: "bg-palette-orange-bg", text: "text-palette-orange-fg" },
  teal: { bg: "bg-success-subtle", text: "text-success" },
  pink: { bg: "bg-palette-pink-bg", text: "text-palette-pink-fg" },
};

const FALLBACK_COLORS = ["blue", "purple", "green", "amber", "cyan", "orange"];

export const BADGE_FONT = '600 12px "Geist", ui-sans-serif, system-ui, sans-serif';
export const BADGE_H_PAD = 12;
export const BADGE_GAP = 4;
export const CHIP_FONT = '400 14px "Geist", ui-sans-serif, system-ui, sans-serif';
export const CHIP_AVATAR_WIDTH = 22;
export const CHIP_GAP = 10;
export const CELL_H_PAD = 24;
export const ATTACH_FONT = '400 12px "Geist", ui-sans-serif, system-ui, sans-serif';
export const FIELD_OPTION_SEARCH_THRESHOLD = 6;

let measureCanvas: HTMLCanvasElement | null = null;

export function measureTextWidth(text: string, font: string) {
  if (typeof document === "undefined") return text.length * 7;
  measureCanvas ??= document.createElement("canvas");
  const context = measureCanvas.getContext("2d");
  if (!context) return text.length * 7;
  context.font = font;
  return context.measureText(text).width;
}

export function isObjectValue(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function primitiveLabel(value: unknown, labelField?: string): string {
  if (value == null) return "";
  if (isObjectValue(value)) {
    const explicit = labelField ? value[labelField] : undefined;
    const candidate =
      explicit ??
      value.label ??
      value.name ??
      value.fileName ??
      value.filename ??
      value.email ??
      value.url ??
      value.id;
    return candidate == null ? "" : String(candidate);
  }
  return String(value);
}

export function emptyValue(value: unknown) {
  return value == null || value === "" || (Array.isArray(value) && value.length === 0);
}

export function EmptyValue() {
  return <span className="text-muted-foreground">{"\u2014"}</span>;
}

export function toArray(value: unknown): unknown[] {
  if (value == null || value === "") return [];
  return Array.isArray(value) ? value : [value];
}

export function fieldAvailableWidth(cellWidth?: number, availableWidth?: number) {
  if (availableWidth != null) return availableWidth;
  if (cellWidth != null) return Math.max(0, cellWidth - CELL_H_PAD);
  return undefined;
}

export function visibleItemCount({
  itemWidths,
  availableWidth,
  gap,
  displayCount,
}: {
  itemWidths: number[];
  availableWidth?: number;
  gap: number;
  displayCount?: number;
}) {
  if (displayCount != null) return Math.max(1, Math.min(displayCount, itemWidths.length));
  if (availableWidth == null) return itemWidths.length;
  if (itemWidths.length <= 1) return itemWidths.length;

  const overflowBadgeWidth =
    measureTextWidth(`+${itemWidths.length - 1}`, BADGE_FONT) + BADGE_H_PAD;
  let used = 0;
  for (let index = 0; index < itemWidths.length; index += 1) {
    const itemWidth = itemWidths[index] + (index > 0 ? gap : 0);
    const remaining = itemWidths.length - index - 1;
    if (remaining === 0) {
      return used + itemWidth <= availableWidth ? itemWidths.length : Math.max(1, index);
    }
    if (used + itemWidth + gap + overflowBadgeWidth > availableWidth) {
      return Math.max(1, index);
    }
    used += itemWidth;
  }
  return itemWidths.length;
}

export function selectOption(field: DataField, raw: unknown) {
  const options = field.config?.options ?? [];
  const rawLabel = primitiveLabel(raw);
  const option = options.find((item) => item.id === rawLabel || item.label === rawLabel);
  const index = Math.max(0, option ? options.indexOf(option) : 0);
  const colorName = option?.color ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length] ?? "blue";
  return {
    id: option?.id ?? rawLabel,
    label: option?.label ?? rawLabel,
    color: OPTION_COLORS[colorName] ?? OPTION_COLORS.blue,
  };
}

export function OptionBadge({ option }: { option: { label: string; color: { bg: string; text: string } } }) {
  return (
    <Badge
      variant="ghost"
      className={cn(
        "min-w-[24px] justify-center rounded-[6px] px-1.5 py-0.5 text-xs font-semibold leading-4",
        option.color.bg,
        option.color.text,
      )}
    >
      {option.label}
    </Badge>
  );
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function UserChip({ user }: { user: DataUserOption }) {
  return (
    <span className="inline-flex min-w-0 shrink-0 items-center gap-1.5 rounded-sm px-0.5 py-0.5">
      <Avatar size="xs" className="bg-secondary text-secondary-foreground">
        {user.avatar_url ? <AvatarImage src={user.avatar_url} alt={user.name} /> : null}
        <AvatarFallback className="bg-transparent font-medium">{getInitials(user.name)}</AvatarFallback>
      </Avatar>
      <span className="truncate text-sm">{user.name}</span>
    </span>
  );
}

export function renderItems(items: Array<{ key: string; element: React.ReactNode }>) {
  return items.map((item) => <Fragment key={item.key}>{item.element}</Fragment>);
}

export function textFromValue(value: unknown) {
  if (Array.isArray(value)) return value.map((item) => primitiveLabel(item)).join(", ");
  return primitiveLabel(value);
}

export function commitOnEnter(
  event: React.KeyboardEvent<HTMLElement>,
  value: DataValue,
  onCommit: CommitFieldValue,
) {
  if (event.key !== "Enter" || event.shiftKey) return;
  event.preventDefault();
  onCommit(value);
}
