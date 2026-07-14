"use client";

import { ChevronRight, Maximize2 } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DataTable } from "@/components/ui/data-table";
import { FieldList } from "@/components/ui/field-list";
import { useCompactOrTouchInput } from "@/components/ui/use-responsive-input";
import { cn } from "@/lib/utils";
import {
  dataValueFromRow,
  type DataColumn,
  type DataField,
  type DataRow,
  type DataValue,
} from "@/components/ui/data-types";

export interface DrilldownScope<TRow = DataRow> {
  id: string;
  label: string;
  description: string;
  rows: TRow[];
}

export interface DrilldownDialogProps<TRow = DataRow> {
  columns: DataColumn<TRow>[];
  detailFields?: DataField[];
  scope: DrilldownScope<TRow> | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  titleColumnKey?: string;
  initialRow?: TRow | null;
  initialRowOnly?: boolean;
  getRowId?: (row: TRow) => string;
  getRowTitle?: (row: TRow) => string;
  getRowValues?: (row: TRow) => Record<string, DataValue>;
  renderDetailActions?: (row: TRow) => ReactNode;
  onCellCommit?: (
    row: TRow,
    field: DataField,
    value: DataValue,
  ) => TRow | void | Promise<TRow | void>;
  emptyTitle?: string;
  emptyDescription?: string;
  detailDescription?: string;
}

function rowValues<TRow>(
  row: TRow,
  fields: DataField[],
  columns: DataColumn<TRow>[],
  getRowValues: ((row: TRow) => Record<string, DataValue>) | undefined,
) {
  if (getRowValues) return getRowValues(row);
  return Object.fromEntries(
    fields.map((field) => {
      const column = columns.find((candidate) => candidate.key === field.key) ?? field;
      return [field.key, dataValueFromRow(row, column as DataColumn<TRow>) ?? null];
    }),
  );
}

function fallbackRowTitle<TRow>(row: TRow, getRowTitle: ((row: TRow) => string) | undefined) {
  if (getRowTitle) return getRowTitle(row);
  if (row && typeof row === "object" && "id" in row) {
    const id = (row as { id?: unknown }).id;
    if (typeof id === "string" || typeof id === "number") return String(id);
  }
  return "Row";
}

function optimisticRowWithFieldValue<TRow>(row: TRow, field: DataField, value: DataValue): TRow {
  if (!row || typeof row !== "object" || Array.isArray(row)) return row;
  const record = row as Record<string, unknown>;
  const values = record.values;

  if (values && typeof values === "object" && !Array.isArray(values)) {
    return {
      ...record,
      values: {
        ...values,
        [field.key]: value,
      },
    } as TRow;
  }

  if (field.key in record) {
    return {
      ...record,
      [field.key]: value,
    } as TRow;
  }

  return row;
}

export function DrilldownDialog<TRow = DataRow>({
  columns,
  detailFields = columns,
  scope,
  open,
  onOpenChange,
  titleColumnKey,
  initialRow,
  initialRowOnly,
  getRowId,
  getRowTitle,
  getRowValues,
  renderDetailActions,
  onCellCommit,
  emptyTitle,
  emptyDescription,
  detailDescription = "Row details",
}: DrilldownDialogProps<TRow>) {
  const [item, setItem] = useState<TRow | null>(null);
  const compactOrTouchInput = useCompactOrTouchInput();

  useEffect(() => {
    setItem(open ? (initialRow ?? null) : null);
  }, [initialRow, scope?.id, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="grid-rows-[auto_minmax(0,1fr)_auto] gap-0 !overflow-hidden p-0 sm:max-w-[min(1120px,calc(100vw-2rem))]">
        <DialogHeader className="border-b border-border/70 px-5 pt-5 pb-4 text-left">
          <DialogTitle className="flex min-w-0 items-center gap-1.5 pr-8 text-headline-sm">
            {scope ? (
              item ? (
                initialRowOnly ? (
                  <span className="min-w-0 truncate">{fallbackRowTitle(item, getRowTitle)}</span>
                ) : (
                  <>
                  <button
                    type="button"
                    className="min-w-0 truncate rounded-sm text-left text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring-subtle"
                    onClick={() => setItem(null)}
                  >
                    {scope.label}
                  </button>
                  <ChevronRight className="icon-16 shrink-0 text-tertiary-foreground" />
                  <span className="min-w-0 truncate">{fallbackRowTitle(item, getRowTitle)}</span>
                </>
                )
              ) : (
                <span className="min-w-0 truncate">{scope.label}</span>
              )
            ) : (
              "Details"
            )}
          </DialogTitle>
          {!item && scope?.description ? (
            <DialogDescription>{scope.description}</DialogDescription>
          ) : (
            <DialogDescription className="sr-only">{detailDescription}</DialogDescription>
          )}
        </DialogHeader>

        <div
          className={cn("min-h-0 px-5 py-5", item || compactOrTouchInput ? "overflow-y-auto" : "overflow-hidden")}
          style={item ? { paddingBottom: "calc(var(--keyboard-safe-bottom) + 1.25rem)" } : undefined}
        >
          {scope && !item ? (
            <DataTable
              className={compactOrTouchInput ? "overflow-visible" : "h-full min-h-0"}
              columns={columns}
              rows={scope.rows}
              titleColumnKey={titleColumnKey}
              getRowId={getRowId}
              getRowTitle={getRowTitle}
              onRowActivate={setItem}
              onCellCommit={onCellCommit}
              titleAction={{
                icon: <Maximize2 className="size-2.5" />,
                label: "Open",
                ariaLabel: (row) => `Open ${fallbackRowTitle(row, getRowTitle)}`,
                tooltip: "Open in dialog",
                onClick: setItem,
                showLabel: true,
              }}
              emptyTitle={emptyTitle}
              emptyDescription={emptyDescription}
            />
          ) : null}

          {scope && item ? (
            <div className="pr-1">
              <FieldList
                fields={detailFields}
                values={rowValues(item, detailFields, columns, getRowValues)}
                onFieldCommit={
                  onCellCommit
                    ? async (field, value) => {
                        const previousItem = item;
                        const optimisticItem = optimisticRowWithFieldValue(previousItem, field, value);
                        if (optimisticItem !== previousItem) setItem(optimisticItem);

                        try {
                          const next = await onCellCommit(previousItem, field, value);
                          if (next) setItem(next);
                        } catch (error) {
                          setItem(previousItem);
                          throw error;
                        }
                      }
                    : undefined
                }
              />
            </div>
          ) : null}
        </div>
        {item && renderDetailActions ? (
          <DialogFooter
            className="h-fit shrink-0 !flex-row !items-start !justify-start border-t border-border/70 px-5 pt-3 pb-3"
            style={{ paddingBottom: "calc(var(--keyboard-safe-bottom) + 0.75rem)" }}
          >
            {renderDetailActions(item)}
          </DialogFooter>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
