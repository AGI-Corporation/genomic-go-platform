"use client";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { commitOnEnter, type FieldValueEditProps, type FieldValueViewProps } from "./shared";

function formatNumber(value: unknown) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return String(value ?? "");
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(parsed);
}

function formatCurrency(value: unknown, currency = "USD") {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return String(value ?? "");
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: parsed % 1 === 0 ? 0 : 2,
  }).format(parsed);
}

function formatPercent(value: unknown) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return String(value ?? "");
  const normalized = Math.abs(parsed) <= 1 ? parsed : parsed / 100;
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(normalized);
}

export function NumberFieldView({ value, className }: FieldValueViewProps) {
  return <span className={className ?? "truncate text-sm tabular-nums"}>{formatNumber(value)}</span>;
}

export function CurrencyFieldView({ value, field, className }: FieldValueViewProps) {
  return <span className={className ?? "truncate text-sm tabular-nums"}>{formatCurrency(value, field.config?.currency)}</span>;
}

export function PercentFieldView({ value, className }: FieldValueViewProps) {
  return <span className={className ?? "truncate text-sm tabular-nums"}>{formatPercent(value)}</span>;
}

export function NumberFieldEdit({
  value,
  field,
  onChange,
  onCommit,
  autoFocus,
}: FieldValueEditProps) {
  const parsed = Number(value ?? 0);
  const displayValue =
    field.type === "percent" && Number.isFinite(parsed) && Math.abs(parsed) <= 1
      ? parsed * 100
      : parsed;
  const unit =
    field.type === "percent"
      ? "%"
      : field.type === "currency"
        ? field.config?.currency ?? "USD"
        : null;
  const unitAlign = field.type === "currency" ? "inline-start" : "inline-end";
  return (
    <InputGroup className="h-9 w-full border-0 bg-transparent px-3 shadow-none has-[[data-slot=input-group-control]:focus-visible]:ring-0">
      {unit && unitAlign === "inline-start" ? (
        <InputGroupAddon align="inline-start" className="pl-0 text-xs uppercase">
          {unit}
        </InputGroupAddon>
      ) : null}
      <InputGroupInput
        autoFocus={autoFocus}
        type="number"
        name={field.key}
        value={Number.isFinite(displayValue) ? String(displayValue) : ""}
        className="px-0 tabular-nums [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        onChange={(event) => {
          const next = event.target.value === "" ? null : Number(event.target.value);
          onChange(field.type === "percent" && typeof next === "number" ? next / 100 : next);
        }}
        onKeyDown={(event) => {
          const numeric = event.currentTarget.value === "" ? null : Number(event.currentTarget.value);
          const next = field.type === "percent" && typeof numeric === "number" ? numeric / 100 : numeric;
          commitOnEnter(event, next, onCommit);
        }}
      />
      {unit && unitAlign === "inline-end" ? (
        <InputGroupAddon align="inline-end" className="pr-0 text-xs uppercase">
          {unit}
        </InputGroupAddon>
      ) : null}
    </InputGroup>
  );
}
