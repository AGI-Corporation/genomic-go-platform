import type { AnchorHTMLAttributes, ReactNode } from 'react';
import {
  dataValueFromRow,
  type DataColumn,
  type DataRow,
} from '@/components/ui/data-types';

export type DataTableActionText<TRow = DataRow> = string | ((row: TRow) => string);

type DataTableTitleActionContent<TRow = DataRow> =
  | {
      label: DataTableActionText<TRow>;
      tooltip?: DataTableActionText<TRow>;
    }
  | {
      label?: undefined;
      tooltip: DataTableActionText<TRow>;
    };

export type DataTableTitleAction<TRow = DataRow> = DataTableTitleActionContent<TRow> & {
  key?: string;
  icon: ReactNode | ((row: TRow) => ReactNode);
  ariaLabel?: DataTableActionText<TRow>;
  href?: (row: TRow) => string | null | undefined;
  target?: AnchorHTMLAttributes<HTMLAnchorElement>['target'];
  onClick?: (row: TRow) => void;
  showLabel?: boolean;
};

export const rowHoverOverlayClass =
  'relative before:pointer-events-none before:absolute before:inset-0 before:opacity-0 hover:before:bg-hover-overlay hover:before:opacity-100';
export const rowSelectedOverlayClass = 'before:bg-primary-subtle before:opacity-100 hover:before:bg-primary-subtle';
export const stickyCellSurfaceClass =
  'isolate overflow-hidden bg-background before:pointer-events-none before:absolute before:inset-0 before:opacity-0';
export const stickyCellHoverSurfaceClass = 'group-hover:before:bg-hover-overlay group-hover:before:opacity-100';
export const stickyTitleCellHoverSurfaceClass = 'hover:before:bg-hover-overlay hover:before:opacity-100';
export const stickySelectedOverlayClass = 'before:bg-primary-subtle before:opacity-100';
export const stickySelectedHoverOverlayClass = 'group-hover:before:bg-primary-subtle';
export const stickyTitleDividerClass = 'shadow-[inset_-1px_0_0_color-mix(in_oklab,var(--border)_70%,transparent)]';
export const titleActionContainerClassName =
  'relative z-10 flex w-0 shrink-0 items-center gap-1 overflow-hidden opacity-0 transition-opacity group-hover/row:w-auto group-hover/row:opacity-100 group-hover/title-cell:w-auto group-hover/title-cell:opacity-100 group-focus-within/title-cell:w-auto group-focus-within/title-cell:opacity-100';
export const titleActionIconClassName =
  'inline-flex size-6 shrink-0 self-center items-center justify-center rounded-sm text-muted-foreground transition-[background-color,color] hover:bg-hover-overlay hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring-subtle [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=size-])]:size-3';
export const titleActionButtonClassName =
  'inline-flex h-6 shrink-0 self-center items-center gap-1 rounded-sm px-1.5 text-xs font-medium whitespace-nowrap text-muted-foreground transition-[background-color,color] hover:bg-hover-overlay hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring-subtle [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=size-])]:size-3';

export const MIN_COLUMN_WIDTH = 60;
export const MIN_TITLE_WIDTH = 160;
export const DEFAULT_COLUMN_WIDTH_BY_TYPE: Partial<Record<DataColumn['type'], number>> = {
  text: 200,
  number: 120,
  currency: 140,
  percent: 120,
  select: 150,
  multi_select: 200,
  date: 160,
  checkbox: 96,
  user: 160,
  multi_user: 200,
  url: 200,
  email: 180,
  attachment: 200,
  relation: 180,
};
export const DEFAULT_COLUMN_WIDTH = 160;

export function comparableValue<TRow>(row: TRow, column: DataColumn<TRow>) {
  if (column.compareValue) return column.compareValue(row);
  const value = dataValueFromRow(row, column);
  if (value == null) return '';
  if (column.type === 'number' || column.type === 'currency' || column.type === 'percent') return Number(value);
  if (column.type === 'date') return new Date(String(value)).getTime();
  if (Array.isArray(value)) return value.length;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value).toLowerCase();
}

export function rowIdFromValue<TRow>(row: TRow, getRowId: ((row: TRow) => string) | undefined, index: number) {
  if (getRowId) return getRowId(row);
  if (row && typeof row === 'object' && 'id' in row) {
    const id = (row as { id?: unknown }).id;
    if (typeof id === 'string' || typeof id === 'number') return String(id);
  }
  return String(index);
}

export function getTitle<TRow>(
  row: TRow,
  titleColumn: DataColumn<TRow> | undefined,
  getRowTitle: ((row: TRow) => string) | undefined,
  rowId: string
) {
  if (getRowTitle) return getRowTitle(row);
  const value = titleColumn ? dataValueFromRow(row, titleColumn) : undefined;
  return value == null ? rowId : String(value);
}

export function resolveActionText<TRow>(value: string | ((row: TRow) => string) | undefined, row: TRow) {
  return typeof value === 'function' ? value(row) : value;
}

export function resolveActionIcon<TRow>(value: ReactNode | ((row: TRow) => ReactNode), row: TRow) {
  return typeof value === 'function' ? value(row) : value;
}

export function defaultColumnWidth<TRow>(column: DataColumn<TRow>, title: boolean) {
  return Math.max(
    title ? MIN_TITLE_WIDTH : MIN_COLUMN_WIDTH,
    column.width ?? DEFAULT_COLUMN_WIDTH_BY_TYPE[column.type] ?? DEFAULT_COLUMN_WIDTH
  );
}

function coerceStoredWidth(value: unknown, minWidth: number): number | null {
  const parsed = typeof value === 'number' ? value : typeof value === 'string' ? Number(value) : NaN;
  return Number.isFinite(parsed) ? Math.max(minWidth, Math.round(parsed)) : null;
}

export function loadColumnWidths(storageKey: string, defaults: Record<string, number>, titleKey: string) {
  if (typeof window === 'undefined') return defaults;
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return defaults;
    return Object.fromEntries(
      Object.entries(defaults).map(([key, fallback]) => [
        key,
        coerceStoredWidth(parsed[key], key === titleKey ? MIN_TITLE_WIDTH : MIN_COLUMN_WIDTH) ?? fallback,
      ])
    );
  } catch {
    return defaults;
  }
}

export function saveColumnWidths(storageKey: string, widths: Record<string, number>) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(widths));
  } catch {
    // localStorage can be unavailable in private browsing or quota-limited contexts.
  }
}
