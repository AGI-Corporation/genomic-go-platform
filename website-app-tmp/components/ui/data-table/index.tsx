'use client';

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { useCompactOrTouchInput } from '@/components/ui/use-responsive-input';
import { cn } from '@/lib/utils';
import { type DataColumn, type DataRow, type DataSortState, type DataValue } from '@/components/ui/data-types';
import { DataTableCardList } from './data-table-card-list';
import { DataTableHeader } from './data-table-header';
import { DataTableRow } from './data-table-row';
import {
  comparableValue,
  getTitle,
  rowIdFromValue,
  type DataTableTitleAction,
} from './data-table-utils';
import { useDataTableColumnWidths } from './use-data-table-column-widths';

export type { DataTableTitleAction } from './data-table-utils';

export interface DataTableProps<TRow = DataRow> {
  className?: string;
  columns: DataColumn<TRow>[];
  rows: TRow[];
  titleColumnKey?: string;
  getRowId?: (row: TRow) => string;
  getRowTitle?: (row: TRow) => string;
  defaultSort?: DataSortState;
  loading?: boolean;
  hasMoreRows?: boolean;
  loadingMore?: boolean;
  onLoadMoreRows?: () => void;
  selectedRowId?: string | null;
  onRowActivate?: (row: TRow) => void;
  onCellCommit?: (row: TRow, column: DataColumn<TRow>, value: DataValue) => unknown | Promise<unknown>;
  rowAriaLabel?: (row: TRow) => string;
  titleAction?: DataTableTitleAction<TRow>;
  titleActions?: DataTableTitleAction<TRow>[];
  columnWidthStorageKey?: string;
  emptyTitle?: string;
  emptyDescription?: string;
}

const useBrowserLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;
const INITIAL_LOADING_ROW_COUNT = 8;
const MORE_LOADING_ROW_COUNT = 3;

function skeletonWidthClass<TRow>(column: DataColumn<TRow>, index: number) {
  if (column.type === 'checkbox') return 'size-4';
  if (index === 0) return 'w-[68%]';
  if (column.type === 'number' || column.type === 'currency' || column.type === 'percent') return 'w-[46%]';
  if (column.type === 'date') return 'w-[56%]';
  return 'w-[62%]';
}

function DataTableSkeletonRows<TRow>({
  columns,
  gridTemplateColumns,
  rowCount,
}: {
  columns: DataColumn<TRow>[];
  gridTemplateColumns: string;
  rowCount: number;
}) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="grid h-[42px] w-full border-b border-border/60 last:border-b-0"
          style={{ gridTemplateColumns }}
        >
          {columns.map((column, columnIndex) => (
            <div
              key={column.key}
              className={cn(
                'flex min-w-0 items-center px-3',
                columnIndex === 0 && 'sticky left-0 z-10 bg-background px-4'
              )}
            >
              <Skeleton className={cn('h-4 rounded-sm', skeletonWidthClass(column, columnIndex))} />
            </div>
          ))}
        </div>
      ))}
    </>
  );
}

function DataTableLoadingSkeleton<TRow>({
  className,
  columns,
  gridTemplateColumns,
  tableWidth,
}: {
  className?: string;
  columns: DataColumn<TRow>[];
  gridTemplateColumns: string;
  tableWidth: number;
}) {
  return (
    <div className={cn('min-w-0', className)} aria-busy="true">
      <div className="overflow-hidden rounded-md border border-border bg-background">
        <div className="overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <div className="w-full" style={{ minWidth: tableWidth }}>
            <div className="grid h-10 border-b border-border/70" style={{ gridTemplateColumns }}>
              {columns.map((column, index) => (
                <div
                  key={column.key}
                  className={cn('flex min-w-0 items-center px-3', index === 0 && 'sticky left-0 z-10 bg-background px-4')}
                >
                  <Skeleton className={cn('h-3 rounded-sm', index === 0 ? 'w-24' : 'w-16')} />
                </div>
              ))}
            </div>
            <DataTableSkeletonRows columns={columns} gridTemplateColumns={gridTemplateColumns} rowCount={INITIAL_LOADING_ROW_COUNT} />
          </div>
        </div>
      </div>
    </div>
  );
}

export function DataTable<TRow = DataRow>({
  className,
  columns,
  rows,
  titleColumnKey,
  getRowId,
  getRowTitle,
  defaultSort,
  loading,
  hasMoreRows,
  loadingMore,
  onLoadMoreRows,
  selectedRowId,
  onRowActivate,
  onCellCommit,
  rowAriaLabel,
  titleAction,
  titleActions,
  columnWidthStorageKey,
  emptyTitle = 'No rows',
  emptyDescription = 'There is no data yet.',
}: DataTableProps<TRow>) {
  const titleColumn = useMemo(
    () => columns.find((column) => column.key === titleColumnKey) ?? columns[0],
    [columns, titleColumnKey]
  );
  const visibleColumns = useMemo(
    () => (titleColumn ? columns.filter((column) => column.key !== titleColumn.key) : []),
    [columns, titleColumn]
  );
  const orderedColumns = useMemo(
    () => (titleColumn ? [titleColumn, ...visibleColumns] : columns),
    [columns, titleColumn, visibleColumns]
  );
  const fallbackSortColumn = defaultSort?.column ?? titleColumn?.key ?? orderedColumns[0]?.key ?? '';
  const [sort, setSort] = useState<DataSortState>(() => ({
    column: fallbackSortColumn,
    direction: defaultSort?.direction ?? 'asc',
  }));
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const [showStickyTitleDivider, setShowStickyTitleDivider] = useState(false);
  const showStickyTitleDividerRef = useRef(false);
  const compactOrTouchInput = useCompactOrTouchInput();
  const titleColumnWidthKey = titleColumn?.key ?? '';
  const {
    columnWidths,
    columnWidthsReady,
    defaultWidths,
    gridTemplateColumns,
    resizingColumn,
    startColumnResize,
    tableWidth,
  } = useDataTableColumnWidths({
    columns: orderedColumns,
    titleColumnWidthKey,
    columnWidthStorageKey,
  });

  useEffect(() => {
    if (!orderedColumns.length) return;
    if (orderedColumns.some((column) => column.key === sort.column)) return;
    setSort({
      column: fallbackSortColumn || orderedColumns[0].key,
      direction: defaultSort?.direction ?? 'asc',
    });
  }, [defaultSort?.direction, fallbackSortColumn, orderedColumns, sort.column]);

  const sortedRows = useMemo(() => {
    const sortColumn = orderedColumns.find((column) => column.key === sort.column) ?? titleColumn;
    if (!sortColumn) return rows;
    return [...rows].sort((a, b) => {
      const av = comparableValue(a, sortColumn);
      const bv = comparableValue(b, sortColumn);
      if (av < bv) return sort.direction === 'asc' ? -1 : 1;
      if (av > bv) return sort.direction === 'asc' ? 1 : -1;
      return getTitle(a, titleColumn, getRowTitle, rowIdFromValue(a, getRowId, 0)).localeCompare(
        getTitle(b, titleColumn, getRowTitle, rowIdFromValue(b, getRowId, 0))
      );
    });
  }, [getRowId, getRowTitle, orderedColumns, rows, sort, titleColumn]);

  const setSortColumn = (column: DataColumn<TRow>) => {
    if (!column.sortable) return;
    setSort((current) => ({
      column: column.key,
      direction: current.column === column.key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const rowActivatesOnClick = !!onRowActivate && !onCellCommit;
  const resolvedTitleActions = titleActions ?? (titleAction ? [titleAction] : []);
  const updateStickyTitleDivider = useCallback(() => {
    const nextShowStickyTitleDivider = (scrollContainerRef.current?.scrollLeft ?? 0) > 0;
    if (showStickyTitleDividerRef.current === nextShowStickyTitleDivider) return;
    showStickyTitleDividerRef.current = nextShowStickyTitleDivider;
    setShowStickyTitleDivider(nextShowStickyTitleDivider);
  }, []);

  useBrowserLayoutEffect(() => {
    updateStickyTitleDivider();
    const scrollContainer = scrollContainerRef.current;
    let secondFrame = 0;
    const frame = window.requestAnimationFrame(() => {
      updateStickyTitleDivider();
      secondFrame = window.requestAnimationFrame(updateStickyTitleDivider);
    });
    const timeout = window.setTimeout(updateStickyTitleDivider, 0);
    if (!scrollContainer) {
      return () => {
        window.cancelAnimationFrame(frame);
        window.cancelAnimationFrame(secondFrame);
        window.clearTimeout(timeout);
      };
    }
    scrollContainer.addEventListener('scroll', updateStickyTitleDivider, { passive: true });
    return () => {
      window.cancelAnimationFrame(frame);
      window.cancelAnimationFrame(secondFrame);
      window.clearTimeout(timeout);
      scrollContainer.removeEventListener('scroll', updateStickyTitleDivider);
    };
  }, [columnWidthsReady, rows.length, updateStickyTitleDivider]);

  useEffect(() => {
    if (!hasMoreRows || loadingMore || !onLoadMoreRows) return;
    const node = loadMoreRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          onLoadMoreRows();
        }
      },
      { root: scrollContainerRef.current, rootMargin: '240px 0px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMoreRows, loadingMore, onLoadMoreRows]);

  if (loading) {
    if (compactOrTouchInput) {
      return (
        <DataTableCardList
          className={className}
          loading
          scrollContainerRef={scrollContainerRef}
          loadMoreRef={loadMoreRef}
          rows={[]}
          titleColumn={titleColumn}
          visibleColumns={visibleColumns}
        />
      );
    }

    return (
      <DataTableLoadingSkeleton
        className={className}
        columns={orderedColumns}
        gridTemplateColumns={gridTemplateColumns}
        tableWidth={tableWidth}
      />
    );
  }

  if (rows.length === 0) {
    return (
      <div className={cn('min-w-0', className)}>
        <div className="flex min-h-[260px] items-center justify-center rounded-md border border-border bg-background px-6">
          <div className="flex max-w-sm flex-col items-center gap-2 text-center">
            <p className="text-label-md">{emptyTitle}</p>
            <p className="text-body-sm text-muted-foreground">{emptyDescription}</p>
          </div>
        </div>
      </div>
    );
  }

  if (compactOrTouchInput) {
    return (
      <DataTableCardList
        className={className}
        loadingMore={loadingMore}
        hasMoreRows={hasMoreRows}
        scrollContainerRef={scrollContainerRef}
        loadMoreRef={loadMoreRef}
        rows={sortedRows}
        titleColumn={titleColumn}
        visibleColumns={visibleColumns}
        getRowId={getRowId}
        getRowTitle={getRowTitle}
        selectedRowId={selectedRowId}
        onLoadMoreRows={onLoadMoreRows}
        onRowActivate={onRowActivate}
        rowAriaLabel={rowAriaLabel}
      />
    );
  }

  return (
    <div className={cn('group/table flex min-w-0 flex-col', className, !columnWidthsReady && 'invisible')}>
      <div
        ref={scrollContainerRef}
        className="min-h-0 overflow-auto rounded-md border border-border bg-background"
      >
        <div className="w-full" style={{ minWidth: tableWidth }}>
          <DataTableHeader
            columns={orderedColumns}
            gridTemplateColumns={gridTemplateColumns}
            resizingColumn={resizingColumn}
            showStickyTitleDivider={showStickyTitleDivider}
            sort={sort}
            tableWidth={tableWidth}
            onColumnResizeStart={startColumnResize}
            onSortColumn={setSortColumn}
          />

          <div className="relative">
            {sortedRows.map((row, rowIndex) => {
              const rowId = rowIdFromValue(row, getRowId, rowIndex);
              return (
                <DataTableRow
                  key={rowId}
                  columnWidths={columnWidths}
                  columnWidthsReady={columnWidthsReady}
                  defaultWidths={defaultWidths}
                  getRowTitle={getRowTitle}
                  gridTemplateColumns={gridTemplateColumns}
                  onCellCommit={onCellCommit}
                  onRowActivate={onRowActivate}
                  row={row}
                  rowActivatesOnClick={rowActivatesOnClick}
                  rowAriaLabel={rowAriaLabel}
                  rowId={rowId}
                  rowIndex={rowIndex}
                  selectedRowId={selectedRowId}
                  showStickyTitleDivider={showStickyTitleDivider}
                  sortedRowsLength={sortedRows.length}
                  titleActions={resolvedTitleActions}
                  titleColumn={titleColumn}
                  visibleColumns={visibleColumns}
                />
              );
            })}
            {loadingMore ? (
              <div
                ref={loadMoreRef}
                className="w-full border-t border-border/60"
                aria-busy="true"
              >
                <DataTableSkeletonRows
                  columns={orderedColumns}
                  gridTemplateColumns={gridTemplateColumns}
                  rowCount={MORE_LOADING_ROW_COUNT}
                />
              </div>
            ) : hasMoreRows ? (
              <div
                ref={loadMoreRef}
                className="flex h-12 w-full items-center justify-center border-t border-border/60 px-4 text-body-sm text-muted-foreground"
              >
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
      </div>
    </div>
  );
}
