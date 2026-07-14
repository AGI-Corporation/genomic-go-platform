"use client";

import { Calendar } from "@/components/ui/calendar";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { commitOnEnter, type FieldValueEditProps, type FieldValueViewProps } from "./shared";

const DATE_FORMAT_PRESETS: Record<string, Intl.DateTimeFormatOptions> = {
  "MM/DD/YYYY": { month: "2-digit", day: "2-digit", year: "numeric" },
  "DD/MM/YYYY": { day: "2-digit", month: "2-digit", year: "numeric" },
  "YYYY-MM-DD": { year: "numeric", month: "2-digit", day: "2-digit" },
  "MMM D, YYYY": { month: "short", day: "numeric", year: "numeric" },
};

function formatDate(value: unknown, field: FieldValueViewProps["field"]) {
  const date = value instanceof Date ? value : new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value ?? "");
  const includeTime = field.config?.include_time ?? false;
  const options = field.config?.date_format
    ? { ...DATE_FORMAT_PRESETS[field.config.date_format] }
    : { ...DATE_FORMAT_PRESETS["MM/DD/YYYY"] };
  if (includeTime) {
    options.hour = "numeric";
    options.minute = "2-digit";
    options.hour12 = true;
  } else {
    options.timeZone = "UTC";
  }
  return new Intl.DateTimeFormat("en-US", options).format(date);
}

function inputDateValue(value: unknown) {
  if (value == null || value === "") return "";
  const text = String(value);
  return text.length >= 10 ? text.slice(0, 10) : text;
}

function inputTimeValue(value: unknown) {
  if (value == null || value === "") return "";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "";
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function selectedDateValue(value: unknown) {
  const dateValue = inputDateValue(value);
  if (!dateValue) return undefined;
  const date = new Date(`${dateValue}T00:00:00`);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

function combineDateTime(dateValue: string, timeValue: string, includeTime: boolean) {
  if (!dateValue) return null;
  if (!includeTime) return dateValue;
  return `${dateValue}T${timeValue || "00:00"}:00`;
}

function dateInputFromDate(date: Date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

export function DateFieldView({ value, field, className }: FieldValueViewProps) {
  return <span className={className ?? "truncate text-sm tabular-nums"}>{formatDate(value, field)}</span>;
}

export function DateFieldEdit({ value, field, onChange, onCommit, autoFocus }: FieldValueEditProps) {
  const includeTime = field.config?.include_time ?? false;
  const dateValue = inputDateValue(value);
  const timeValue = inputTimeValue(value);
  const selectedDate = selectedDateValue(value);
  return (
    <div className="w-fit max-w-[calc(100vw-2rem)]">
      <Calendar
        mode="single"
        selected={selectedDate}
        defaultMonth={selectedDate}
        autoFocus={autoFocus && !includeTime}
        onSelect={(date) => {
          const nextDateValue = date ? dateInputFromDate(date) : "";
          const next = combineDateTime(nextDateValue, timeValue, includeTime);
          onChange(next);
          if (!includeTime) onCommit(next);
        }}
      />
      {includeTime ? (
        <div className="border-t border-border/60 p-2">
          <InputGroup className="h-9 w-full border-0 bg-transparent px-2 shadow-none has-[[data-slot=input-group-control]:focus-visible]:ring-0">
            <InputGroupAddon align="inline-start" className="pl-0 text-xs uppercase">
              Time
            </InputGroupAddon>
            <InputGroupInput
              autoFocus={autoFocus}
              type="time"
              name={field.key}
              value={timeValue}
              className="px-0 tabular-nums"
              onChange={(event) => {
                const next = combineDateTime(dateValue, event.target.value, true);
                onChange(next);
              }}
              onKeyDown={(event) => {
                const next = combineDateTime(dateValue, event.currentTarget.value, true);
                commitOnEnter(event, next, onCommit);
              }}
            />
          </InputGroup>
        </div>
      ) : null}
    </div>
  );
}
