import {
  ATTACH_FONT,
  BADGE_FONT,
  BADGE_GAP,
  BADGE_H_PAD,
  CHIP_AVATAR_WIDTH,
  CHIP_FONT,
  CHIP_GAP,
  measureTextWidth,
  primitiveLabel,
  selectOption,
  textFromValue,
  toArray,
} from "@/components/ui/field-values/shared";
import type { DataField, DataValue } from "@/components/ui/data-types";

export type FieldLayoutSize = "normal" | "wide" | "full";

export interface FieldLayoutContext {
  columnCount: number;
  columnWidth: number;
  columnGap: number;
}

const FIELD_VALUE_FONT = '400 14px "Geist", ui-sans-serif, system-ui, sans-serif';
const MAX_ITEM_LABEL_WIDTH = 120;
const ATTACH_ITEM_FIXED_WIDTH = 14 + 6 + 16;
const RELATION_ITEM_FIXED_WIDTH = 12 + 4 + 16;

function maxTextLineCount(text: string) {
  return text.split(/\r?\n/).length;
}

function longestUnbrokenTextSegment(text: string) {
  return text
    .split(/[\s,;]+/)
    .reduce((longest, segment) => Math.max(longest, segment.length), 0);
}

function resolveTextLikeLayoutSize(text: string): FieldLayoutSize {
  const lineCount = maxTextLineCount(text);
  const longestSegment = longestUnbrokenTextSegment(text);
  if (text.length > 240 || lineCount >= 3 || longestSegment > 96) return "full";
  if (text.length > 80 || lineCount >= 2 || longestSegment > 24) return "wide";
  return "normal";
}

function usableLayoutContext(context: FieldLayoutContext | undefined): FieldLayoutContext | null {
  if (!context) return null;
  if (context.columnCount < 2 || context.columnWidth <= 0) return null;
  return context;
}

function spanWidth(context: FieldLayoutContext, span: number) {
  const columnSpan = Math.max(1, Math.min(context.columnCount, span));
  return context.columnWidth * columnSpan + context.columnGap * (columnSpan - 1);
}

function estimatedWrappedLineCount(text: string, availableWidth: number) {
  const width = Math.max(1, availableWidth);
  return text.split(/\r?\n/).reduce((count, line) => {
    const measuredWidth = measureTextWidth(line || " ", FIELD_VALUE_FONT);
    return count + Math.max(1, Math.ceil(measuredWidth / width));
  }, 0);
}

function resolveContainerTextLayoutSize(
  text: string,
  context: FieldLayoutContext | undefined,
): FieldLayoutSize {
  const fallback = resolveTextLikeLayoutSize(text);
  const layoutContext = usableLayoutContext(context);
  if (!layoutContext) return fallback;

  const normalLines = estimatedWrappedLineCount(text, spanWidth(layoutContext, 1));
  if (normalLines <= 1) return "normal";

  if (layoutContext.columnCount >= 3) {
    const wideLines = estimatedWrappedLineCount(text, spanWidth(layoutContext, 2));
    if (wideLines > 2 || normalLines > 4) return "full";
  }

  return "wide";
}

function resolveSingleLineLayoutSize(
  text: string,
  context: FieldLayoutContext | undefined,
): FieldLayoutSize {
  const fallback = resolveTextLikeLayoutSize(text);
  const layoutContext = usableLayoutContext(context);
  if (!layoutContext) return fallback;

  const textWidth = measureTextWidth(text, FIELD_VALUE_FONT);
  if (textWidth <= spanWidth(layoutContext, 1)) return "normal";
  if (layoutContext.columnCount >= 3 && textWidth > spanWidth(layoutContext, 2)) return "full";
  return "wide";
}

function userLabel(field: DataField, raw: unknown) {
  const rawLabel = primitiveLabel(raw);
  const user = field.config?.users?.find(
    (item) => item.id === rawLabel || item.email === rawLabel || item.name === rawLabel,
  );
  return user?.name ?? rawLabel;
}

function multiLabelStats(
  value: unknown,
  itemWidth: (item: unknown) => number,
  label: (item: unknown) => string = primitiveLabel,
) {
  const values = toArray(value);
  const labels = values.map(label);
  const itemWidths = values.map(itemWidth);
  return {
    count: labels.length,
    totalLength: labels.reduce((sum, label) => sum + label.length, 0),
    itemWidths,
  };
}

function totalItemWidth(itemWidths: number[], gap: number) {
  if (itemWidths.length === 0) return 0;
  return itemWidths.reduce((sum, width) => sum + width, 0) + gap * (itemWidths.length - 1);
}

function resolveItemListLayoutSize({
  itemWidths,
  gap,
  fallback,
  context,
}: {
  itemWidths: number[];
  gap: number;
  fallback: FieldLayoutSize;
  context?: FieldLayoutContext;
}) {
  const layoutContext = usableLayoutContext(context);
  if (!layoutContext) return fallback;

  const width = totalItemWidth(itemWidths, gap);
  if (width <= spanWidth(layoutContext, 1)) return "normal";
  if (layoutContext.columnCount >= 3 && width > spanWidth(layoutContext, 2)) return "full";
  return "wide";
}

export function resolveFieldLayoutSize(
  field: DataField,
  value: DataValue | undefined,
  context?: FieldLayoutContext,
): FieldLayoutSize {
  if (value == null || value === "") return "normal";

  if (field.type === "text") {
    return resolveContainerTextLayoutSize(textFromValue(value), context);
  }

  if (field.type === "url" || field.type === "email") {
    const text =
      field.type === "url"
        ? textFromValue(value).replace(/^https?:\/\//i, "")
        : textFromValue(value);
    return resolveSingleLineLayoutSize(text, context);
  }

  if (field.type === "multi_select" || field.type === "multi_user") {
    const stats =
      field.type === "multi_select"
        ? multiLabelStats(
            value,
            (item) => measureTextWidth(selectOption(field, item).label, BADGE_FONT) + BADGE_H_PAD,
            (item) => selectOption(field, item).label,
          )
        : multiLabelStats(
            value,
            (item) => CHIP_AVATAR_WIDTH + measureTextWidth(userLabel(field, item), CHIP_FONT),
            (item) => userLabel(field, item),
          );
    const fallback =
      stats.count > 8 || stats.totalLength > 120
        ? "full"
        : stats.count > 2 || stats.totalLength > 40
          ? "wide"
          : "normal";
    return resolveItemListLayoutSize({
      itemWidths: stats.itemWidths,
      gap: field.type === "multi_user" ? CHIP_GAP : BADGE_GAP,
      fallback,
      context,
    });
  }

  if (field.type === "attachment") {
    const labelField = field.config?.attachment?.label_field;
    const stats = multiLabelStats(
      value,
      (item) =>
        ATTACH_ITEM_FIXED_WIDTH +
        Math.min(
          measureTextWidth(primitiveLabel(item, labelField), ATTACH_FONT),
          MAX_ITEM_LABEL_WIDTH,
        ),
      (item) => primitiveLabel(item, labelField),
    );
    const fallback = stats.count > 5 ? "full" : stats.count > 2 ? "wide" : "normal";
    return resolveItemListLayoutSize({
      itemWidths: stats.itemWidths,
      gap: BADGE_GAP,
      fallback,
      context,
    });
  }

  if (field.type === "relation") {
    const labelField = field.config?.relation_label_field;
    const stats = multiLabelStats(
      value,
      (item) =>
        RELATION_ITEM_FIXED_WIDTH +
        Math.min(
          measureTextWidth(primitiveLabel(item, labelField), ATTACH_FONT),
          MAX_ITEM_LABEL_WIDTH,
        ),
      (item) => primitiveLabel(item, labelField),
    );
    const fallback = stats.count > 5 ? "full" : stats.count > 2 ? "wide" : "normal";
    return resolveItemListLayoutSize({
      itemWidths: stats.itemWidths,
      gap: BADGE_GAP,
      fallback,
      context,
    });
  }

  return "normal";
}

export function fieldLayoutClassName(size: FieldLayoutSize) {
  if (size === "full") return "sm:col-span-2 xl:col-span-3";
  if (size === "wide") return "sm:col-span-2";
  return undefined;
}
