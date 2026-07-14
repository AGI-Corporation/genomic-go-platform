import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react';
import type { MouseEvent } from 'react';
import type { DataColumn, DataSortState } from '@/components/ui/data-types';
import { cn } from '@/lib/utils';
import { stickyTitleDividerClass } from './data-table-utils';

interface SortIconProps {
  active: boolean;
  direction: 'asc' | 'desc';
}

function SortIcon({ active, direction }: SortIconProps) {
  if (!active) return <ChevronsUpDown className="icon-14 opacity-45" />;
  return direction === 'asc' ? <ArrowUp className="icon-14" /> : <ArrowDown className="icon-14" />;
}

interface DataTableHeaderProps<TRow> {
  columns: DataColumn<TRow>[];
  gridTemplateColumns: string;
  resizingColumn: string | null;
  showStickyTitleDivider: boolean;
  sort: DataSortState;
  tableWidth: number;
  onColumnResizeStart: (event: MouseEvent<HTMLElement>, column: DataColumn<TRow>) => void;
  onSortColumn: (column: DataColumn<TRow>) => void;
}

export function DataTableHeader<TRow>({
  columns,
  gridTemplateColumns,
  resizingColumn,
  showStickyTitleDivider,
  sort,
  tableWidth,
  onColumnResizeStart,
  onSortColumn,
}: DataTableHeaderProps<TRow>) {
  return (
    <div className="sticky top-0 z-40 bg-background">
      <div
        className="group/header grid w-full border-b border-border/70 bg-background"
        style={{ gridTemplateColumns, minWidth: tableWidth }}
      >
        {columns.map((column, index) => {
          const active = sort.column === column.key;
          return (
            <div
              key={column.key}
              className={cn(
                'group/header-cell relative flex h-10 min-w-0 items-center overflow-hidden font-sans transition-colors',
                index === 0 && 'sticky left-0 z-50 bg-background pl-4',
                index === 0 && showStickyTitleDivider && stickyTitleDividerClass,
                column.sortable && index === 0 && 'hover:bg-surface-soft hover:text-foreground',
                column.sortable && index !== 0 && 'hover:bg-hover-overlay hover:text-foreground'
              )}
            >
              <button
                type="button"
                disabled={!column.sortable}
                className={cn(
                  'flex h-full min-w-0 flex-1 items-center gap-1.5 px-2 py-3 text-left',
                  index === 0 && 'pl-0',
                  !column.sortable && 'cursor-default'
                )}
                onClick={() => onSortColumn(column)}
              >
                <span className="truncate text-[12px] leading-4 font-semibold tracking-normal text-tertiary-foreground uppercase group-hover/header-cell:text-foreground">
                  {column.label}
                </span>
                {column.sortable && <SortIcon active={active} direction={sort.direction} />}
              </button>
              <span
                aria-hidden="true"
                className={cn(
                  'absolute top-1 right-0 bottom-1 w-1 cursor-col-resize rounded-full transition-colors',
                  resizingColumn === column.key
                    ? 'bg-primary/40'
                    : 'opacity-0 group-hover/header:opacity-100 group-hover/header:bg-border'
                )}
                onMouseDown={(event) => onColumnResizeStart(event, column)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
