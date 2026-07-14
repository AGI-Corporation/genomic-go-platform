import type { RefObject } from 'react';
import { dataValueFromRow, type DataColumn, type DataRow } from '@/components/ui/data-types';
import { FieldValue } from '@/components/ui/field-value';
import { emptyValue } from '@/components/ui/field-values/shared';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { getTitle, rowIdFromValue } from './data-table-utils';

const CARD_LOADING_ROW_COUNT = 5;
const CARD_SUMMARY_FIELD_LIMIT = 6;

interface DataTableCardListProps<TRow> {
  className?: string;
  loading?: boolean;
  loadingMore?: boolean;
  hasMoreRows?: boolean;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  loadMoreRef: RefObject<HTMLDivElement | null>;
  rows: TRow[];
  titleColumn?: DataColumn<TRow>;
  visibleColumns: DataColumn<TRow>[];
  getRowId?: (row: TRow) => string;
  getRowTitle?: (row: TRow) => string;
  selectedRowId?: string | null;
  onLoadMoreRows?: () => void;
  onRowActivate?: (row: TRow) => void;
  rowAriaLabel?: (row: TRow) => string;
}

function shouldIgnoreCardActivation(target: EventTarget | null, currentTarget: HTMLElement) {
  if (!(target instanceof HTMLElement)) return false;
  const interactiveTarget = target.closest('a, button, input, textarea, select, [role="button"], [data-row-action]');
  return Boolean(interactiveTarget && interactiveTarget !== currentTarget);
}

function DataTableCardSkeletonRows() {
  return (
    <div className="flex min-w-0 flex-col gap-2" aria-busy="true">
      {Array.from({ length: CARD_LOADING_ROW_COUNT }).map((_, index) => (
        <div key={index} className="rounded-md border border-border bg-card p-4 shadow-xs">
          <Skeleton className="h-5 w-[72%] rounded-sm" />
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2">
            <Skeleton className="h-4 w-24 rounded-sm" />
            <Skeleton className="h-4 w-28 rounded-sm" />
            <Skeleton className="h-4 w-20 rounded-sm" />
          </div>
        </div>
      ))}
    </div>
  );
}

function DataTableCardSummary<TRow>({
  row,
  visibleColumns,
}: {
  row: TRow;
  visibleColumns: DataColumn<TRow>[];
}) {
  const visibleValues = visibleColumns
    .map((column) => ({ column, value: dataValueFromRow(row, column) }))
    .filter(({ value }) => !emptyValue(value));
  const summaryValues = visibleValues.slice(0, CARD_SUMMARY_FIELD_LIMIT);

  if (summaryValues.length === 0) return null;

  return (
    <div className="mt-3 flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 text-body-md text-muted-foreground">
      {summaryValues.map(({ column, value }) => (
        <div key={column.key} className="inline-flex min-w-0 max-w-full items-center gap-1.5">
          <p className="shrink-0 text-label-sm tracking-normal text-tertiary-foreground">{column.label}</p>
          <span className="min-w-0 max-w-full flex-1">
            <FieldValue
              value={value}
              field={column}
              displayCount={2}
              overflowBadgeTrigger="span"
              wrapText={false}
            />
          </span>
        </div>
      ))}
      {visibleValues.length > summaryValues.length ? (
        <span className="text-label-sm tracking-normal text-tertiary-foreground">
          +{visibleValues.length - summaryValues.length} more
        </span>
      ) : null}
    </div>
  );
}

export function DataTableCardList<TRow = DataRow>({
  className,
  loading,
  loadingMore,
  hasMoreRows,
  scrollContainerRef,
  loadMoreRef,
  rows,
  titleColumn,
  visibleColumns,
  getRowId,
  getRowTitle,
  selectedRowId,
  onLoadMoreRows,
  onRowActivate,
  rowAriaLabel,
}: DataTableCardListProps<TRow>) {
  if (loading) {
    return (
      <div ref={scrollContainerRef} className={cn('min-h-0 min-w-0 overflow-y-auto', className, '!mb-0')}>
        <div className="flex min-w-0 flex-col pb-[calc(env(safe-area-inset-bottom)+1rem)]">
          <DataTableCardSkeletonRows />
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollContainerRef} className={cn('min-h-0 min-w-0 overflow-y-auto', className, '!mb-0')}>
      <div className="flex min-w-0 flex-col gap-2 pb-[calc(env(safe-area-inset-bottom)+1rem)]">
        {rows.map((row, rowIndex) => {
          const rowId = rowIdFromValue(row, getRowId, rowIndex);
          const title = getTitle(row, titleColumn, getRowTitle, rowId);
          const selected = rowId === selectedRowId;
          const activates = !!onRowActivate;

          return (
            <div
              key={rowId}
              role={activates ? 'button' : undefined}
              tabIndex={activates ? 0 : undefined}
              aria-label={activates ? (rowAriaLabel?.(row) ?? `Open ${title}`) : undefined}
              data-selected={selected ? '' : undefined}
              className={cn(
                'relative isolate rounded-md border border-border bg-card p-4 text-left shadow-xs outline-none transition-[background-color,box-shadow]',
                activates && 'cursor-pointer hover:bg-accent/45 focus-visible:ring-[3px] focus-visible:ring-ring-subtle',
                selected && 'bg-primary-subtle shadow-active'
              )}
              onClick={
                activates
                  ? (event) => {
                      if (shouldIgnoreCardActivation(event.target, event.currentTarget)) return;
                      onRowActivate?.(row);
                    }
                  : undefined
              }
              onKeyDown={
                activates
                  ? (event) => {
                      if (shouldIgnoreCardActivation(event.target, event.currentTarget)) return;
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        onRowActivate?.(row);
                      }
                    }
                  : undefined
              }
            >
              <p className="min-w-0 text-label-lg tracking-normal text-foreground">{title}</p>
              <DataTableCardSummary row={row} visibleColumns={visibleColumns} />
            </div>
          );
        })}
        {loadingMore ? (
          <div ref={loadMoreRef}>
            <DataTableCardSkeletonRows />
          </div>
        ) : hasMoreRows ? (
          <div ref={loadMoreRef} className="flex h-12 items-center justify-center px-4 text-body-sm text-muted-foreground">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-sm px-2 py-1 transition-colors hover:bg-hover-overlay hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring-subtle"
              onClick={() => onLoadMoreRows?.()}
            >
              Load more rows
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
