import type { DataColumn, DataValue } from '@/components/ui/data-types';
import { dataValueFromRow } from '@/components/ui/data-types';
import { FieldValuePopover } from '@/components/ui/field-value-popover';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  DEFAULT_COLUMN_WIDTH,
  getTitle,
  resolveActionIcon,
  resolveActionText,
  rowHoverOverlayClass,
  rowSelectedOverlayClass,
  stickyCellHoverSurfaceClass,
  stickyCellSurfaceClass,
  stickySelectedHoverOverlayClass,
  stickySelectedOverlayClass,
  stickyTitleCellHoverSurfaceClass,
  stickyTitleDividerClass,
  titleActionButtonClassName,
  titleActionContainerClassName,
  titleActionIconClassName,
  type DataTableTitleAction,
} from './data-table-utils';

interface DataTableRowProps<TRow> {
  columnWidths: Record<string, number>;
  columnWidthsReady: boolean;
  defaultWidths: Record<string, number>;
  getRowTitle?: (row: TRow) => string;
  gridTemplateColumns: string;
  onCellCommit?: (row: TRow, column: DataColumn<TRow>, value: DataValue) => unknown | Promise<unknown>;
  onRowActivate?: (row: TRow) => void;
  row: TRow;
  rowActivatesOnClick: boolean;
  rowAriaLabel?: (row: TRow) => string;
  rowId: string;
  rowIndex: number;
  selectedRowId?: string | null;
  showStickyTitleDivider: boolean;
  sortedRowsLength: number;
  titleActions?: DataTableTitleAction<TRow>[];
  titleColumn?: DataColumn<TRow>;
  visibleColumns: DataColumn<TRow>[];
}

export function DataTableRow<TRow>({
  columnWidths,
  columnWidthsReady,
  defaultWidths,
  getRowTitle,
  gridTemplateColumns,
  onCellCommit,
  onRowActivate,
  row,
  rowActivatesOnClick,
  rowAriaLabel,
  rowId,
  rowIndex,
  selectedRowId,
  showStickyTitleDivider,
  sortedRowsLength,
  titleActions = [],
  titleColumn,
  visibleColumns,
}: DataTableRowProps<TRow>) {
  const selected = rowId === selectedRowId;
  const title = getTitle(row, titleColumn, getRowTitle, rowId);
  const titleValue = titleColumn ? dataValueFromRow(row, titleColumn) : title;
  const resolvedTitleActions = titleActions
    .map((action, index) => {
      const href = action.href?.(row);
      const label = resolveActionText(action.label, row);
      const tooltip = resolveActionText(action.tooltip ?? action.label, row);
      const ariaLabel = resolveActionText(action.ariaLabel ?? action.label ?? action.tooltip, row);
      const icon = resolveActionIcon(action.icon, row);
      return {
        action,
        ariaLabel,
        href,
        icon,
        index,
        label,
        tooltip,
      };
    })
    .filter(({ action, ariaLabel, href, icon }) => Boolean(icon && ariaLabel && (href || action.onClick)));
  const hasTitleActions = resolvedTitleActions.length > 0;

  return (
    <div
      data-selected={selected ? '' : undefined}
      className={cn(
        'group/row group grid h-[42px] w-full text-left',
        rowActivatesOnClick && 'cursor-pointer',
        rowActivatesOnClick && rowHoverOverlayClass,
        rowIndex !== sortedRowsLength - 1 && 'border-b border-border/60',
        selected && rowSelectedOverlayClass
      )}
      style={{ gridTemplateColumns }}
      aria-label={rowAriaLabel?.(row) ?? `Open ${title}`}
      role={rowActivatesOnClick ? 'button' : undefined}
      tabIndex={rowActivatesOnClick ? 0 : undefined}
      onClick={rowActivatesOnClick ? () => onRowActivate?.(row) : undefined}
      onKeyDown={
        rowActivatesOnClick
          ? (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onRowActivate?.(row);
              }
            }
          : undefined
      }
    >
      <div
        className={cn(
          'group/title-cell sticky left-0 z-10 flex min-w-0 items-stretch',
          hasTitleActions && 'pr-2',
          showStickyTitleDivider && stickyTitleDividerClass,
          stickyCellSurfaceClass,
          stickyTitleCellHoverSurfaceClass,
          rowActivatesOnClick && stickyCellHoverSurfaceClass,
          selected && stickySelectedOverlayClass,
          selected && rowActivatesOnClick && stickySelectedHoverOverlayClass
        )}
      >
        <div className="relative z-10 flex min-w-0 flex-1 items-stretch">
          {titleColumn ? (
            <FieldValuePopover
              field={titleColumn}
              value={titleValue}
              onCommit={onCellCommit ? (nextValue) => onCellCommit(row, titleColumn, nextValue) : undefined}
              variant="table-cell"
              className="px-4 py-2.5 text-label-md tracking-normal hover:bg-transparent"
            />
          ) : (
            <p className="flex min-w-0 flex-1 items-center truncate px-4 py-2.5 text-label-md tracking-normal">
              {title}
            </p>
          )}
        </div>
        {hasTitleActions ? (
          <div className={titleActionContainerClassName}>
            {resolvedTitleActions.map(({ action, ariaLabel, href, icon, index, label, tooltip }) => {
              const resolvedTitleActionClassName = action.showLabel
                ? titleActionButtonClassName
                : titleActionIconClassName;

              return (
                <Tooltip key={action.key ?? index}>
                  <TooltipTrigger asChild>
                    {href ? (
                      <a
                        data-row-action="title-action"
                        href={href}
                        target={action.target}
                        rel={action.target === '_blank' ? 'noreferrer' : undefined}
                        aria-label={ariaLabel}
                        className={resolvedTitleActionClassName}
                        onClick={(event) => event.stopPropagation()}
                      >
                        {icon}
                        {action.showLabel && label ? <span>{label}</span> : null}
                      </a>
                    ) : (
                      <button
                        type="button"
                        data-row-action="title-action"
                        aria-label={ariaLabel}
                        className={resolvedTitleActionClassName}
                        onClick={(event) => {
                          event.stopPropagation();
                          action.onClick?.(row);
                        }}
                      >
                        {icon}
                        {action.showLabel && label ? <span>{label}</span> : null}
                      </button>
                    )}
                  </TooltipTrigger>
                  {tooltip ? <TooltipContent side="bottom">{tooltip}</TooltipContent> : null}
                </Tooltip>
              );
            })}
          </div>
        ) : null}
      </div>
      {visibleColumns.map((column) => (
        <div
          key={column.key}
          className={cn(
            'relative flex min-w-0 items-stretch overflow-hidden text-body-md text-muted-foreground',
            rowActivatesOnClick && 'group-hover:text-foreground/90'
          )}
        >
          <FieldValuePopover
            value={dataValueFromRow(row, column)}
            field={column}
            cellWidth={
              columnWidthsReady ? (columnWidths[column.key] ?? defaultWidths[column.key] ?? DEFAULT_COLUMN_WIDTH) : undefined
            }
            onCommit={onCellCommit ? (nextValue) => onCellCommit(row, column, nextValue) : undefined}
            variant="table-cell"
          />
        </div>
      ))}
    </div>
  );
}
