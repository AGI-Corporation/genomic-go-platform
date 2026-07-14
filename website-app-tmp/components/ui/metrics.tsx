"use client";

import { dataValueFromRow, type DataRow, type DataValue } from "@/components/ui/data-types";

export interface SummaryMetric<TRow = DataRow> {
  id: string;
  label: string;
  column: string;
  aggregate: "count" | "sum" | "avg" | "percent_true";
  format?: "number" | "currency" | "percent";
  getValue?: (row: TRow) => DataValue | undefined;
}

export interface MetricsSummaryProps<TRow = DataRow> {
  ariaLabel?: string;
  rows: TRow[];
  metrics: SummaryMetric<TRow>[];
}

function metricValue<TRow>(metric: SummaryMetric<TRow>, rows: TRow[]) {
  const values = rows
    .map((row) => metric.getValue?.(row) ?? dataValueFromRow(row, { key: metric.column, label: metric.label, type: "text" }))
    .filter((value) => value != null && value !== "");
  const numbers = values.map((value) => Number(value)).filter((value) => Number.isFinite(value));
  switch (metric.aggregate) {
    case "count":
      return values.length;
    case "sum":
      return numbers.reduce((sum, value) => sum + value, 0);
    case "avg":
      return numbers.length === 0 ? 0 : numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
    case "percent_true": {
      const trueCount = values.filter((value) => value === true || value === "true" || value === 1).length;
      return values.length === 0 ? 0 : trueCount / values.length;
    }
  }
}

function formatMetric<TRow>(metric: SummaryMetric<TRow>, value: number) {
  if (metric.format === "currency") {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  }
  if (metric.format === "percent") {
    const normalized = Math.abs(value) <= 1 ? value : value / 100;
    return new Intl.NumberFormat("en-US", {
      style: "percent",
      maximumFractionDigits: 0,
    }).format(normalized);
  }
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(value);
}

export function MetricsSummary<TRow = DataRow>({
  ariaLabel = "Data summary",
  rows,
  metrics,
}: MetricsSummaryProps<TRow>) {
  return (
    <section aria-label={ariaLabel} className="grid gap-px overflow-hidden rounded-md border border-border bg-border sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => {
        const value = metricValue(metric, rows);
        return (
          <div key={metric.id} className="bg-background px-5 py-3">
            <p className="text-label-sm text-tertiary-foreground">{metric.label}</p>
            <p className="mt-1 truncate text-headline-sm tabular-nums">{formatMetric(metric, value)}</p>
          </div>
        );
      })}
    </section>
  );
}
