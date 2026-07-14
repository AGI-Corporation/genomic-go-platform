"use client";

import { cn } from "@/lib/utils";
import { FieldEditOptionList } from "./edit-option-list";
import type { FieldValueEditProps, FieldValueViewProps } from "./shared";

function checkedValue(value: unknown) {
  return value === true || value === "true" || value === 1;
}

export function CheckboxFieldView({ value, className }: FieldValueViewProps) {
  const checked = checkedValue(value);
  return (
    <span className={cn("text-sm font-medium", checked ? "text-success" : "text-muted-foreground", className)}>
      {checked ? "Yes" : "No"}
    </span>
  );
}

export function CheckboxFieldEdit({ value, onChange, onCommit }: FieldValueEditProps) {
  const checked = checkedValue(value);
  return (
    <FieldEditOptionList
      items={[
        {
          id: "true",
          label: "Yes",
          selected: checked,
          content: <span className="font-medium text-success">Yes</span>,
          onSelect: () => {
            onChange(true);
            onCommit(true);
          },
        },
        {
          id: "false",
          label: "No",
          selected: !checked,
          content: <span className="font-medium text-muted-foreground">No</span>,
          onSelect: () => {
            onChange(false);
            onCommit(false);
          },
        },
      ]}
    />
  );
}
