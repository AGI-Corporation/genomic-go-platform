"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useWorkspaceMemberProfiles } from "@/components/providers/kylon-workspace-provider";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { FieldValue, isEditableField } from "@/components/ui/field-value";
import {
  FIELD_OPTION_SEARCH_THRESHOLD,
  primitiveLabel,
  textFromValue,
} from "@/components/ui/field-values/shared";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useCompactOrTouchInput } from "@/components/ui/use-responsive-input";
import { cn } from "@/lib/utils";
import type { DataField, DataValue } from "@/components/ui/data-types";

function stableJson(value: unknown) {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function fieldValueSignature(value: DataValue | undefined) {
  return stableJson(value ?? null);
}

export type FieldValuePopoverVariant = "field-list" | "table-cell";

function canOfferFullView(field: DataField, value: DataValue | undefined) {
  if (value == null || value === "") return false;
  if (field.type === "attachment" || field.type === "relation") return true;
  if (field.type === "multi_select" || field.type === "multi_user") return Array.isArray(value) && value.length > 2;
  if (field.type === "url" || field.type === "email") return textFromValue(value).length > 36;
  if (field.type === "text") {
    const text = textFromValue(value);
    return text.length > 80 || text.includes("\n");
  }
  return false;
}

function compactListText(labels: string[], displayCount: number | undefined) {
  if (labels.length === 0) return "";
  const visibleCount = Math.max(1, Math.min(displayCount ?? 3, labels.length));
  const visible = labels.slice(0, visibleCount).join(", ");
  const hiddenCount = labels.length - visibleCount;
  return hiddenCount > 0 ? `${visible}, +${hiddenCount}` : visible;
}

function userLabel(field: DataField, raw: unknown) {
  const rawLabel = primitiveLabel(raw);
  const user = field.config?.users?.find(
    (item) => item.id === rawLabel || item.email === rawLabel || item.name === rawLabel,
  );
  return user?.name ?? rawLabel;
}

function compactPreviewText(field: DataField, value: DataValue | undefined, displayCount: number | undefined) {
  if (value == null || value === "") return "";
  const values = Array.isArray(value) ? value : [value];
  if (field.type === "select" || field.type === "multi_select") {
    const labels = values.map((item) => {
      const rawLabel = primitiveLabel(item);
      const option = field.config?.options?.find((candidate) => candidate.id === rawLabel || candidate.label === rawLabel);
      return option?.label ?? rawLabel;
    });
    return compactListText(labels, displayCount ?? field.config?.max_visible);
  }
  if (field.type === "user" || field.type === "multi_user") {
    return compactListText(
      values.map((item) => userLabel(field, item)),
      displayCount ?? field.config?.max_visible,
    );
  }
  if (field.type === "attachment") {
    return compactListText(
      values.map((item) => primitiveLabel(item, field.config?.attachment?.label_field)),
      displayCount ?? field.config?.max_visible,
    );
  }
  if (field.type === "relation") {
    return compactListText(
      values.map((item) => primitiveLabel(item, field.config?.relation_label_field)),
      displayCount ?? field.config?.max_visible,
    );
  }
  if (field.type === "url") return textFromValue(value).replace(/^https?:\/\//i, "");
  return textFromValue(value);
}

function canUseRenderedButtonPreview(field: DataField, variant: FieldValuePopoverVariant) {
  if (variant === "table-cell") {
    if (field.type === "url" || field.type === "email" || field.type === "attachment") return false;
  }
  if (field.type === "url" || field.type === "email" || field.type === "attachment") return false;
  return true;
}

function popoverContentClassName(field: DataField, editable: boolean) {
  if (!editable) return "w-[min(560px,calc(100vw-2rem))] p-3";
  switch (field.type) {
    case "text":
      return "w-[min(380px,calc(100vw-2rem))] p-0";
    case "url":
    case "email":
      return "w-[min(360px,calc(100vw-2rem))] p-0";
    case "number":
    case "currency":
    case "percent":
      return "w-[min(220px,calc(100vw-2rem))] p-0";
    case "date":
      return "w-auto p-0";
    case "select":
    case "multi_select":
    case "user":
    case "multi_user":
    case "checkbox":
      return "w-auto min-w-56 !overflow-visible border-0 bg-transparent p-0 shadow-none";
    default:
      return "w-[min(420px,calc(100vw-2rem))] p-2";
  }
}

function editorFrameClassName(field: DataField) {
  if (
    field.type === "select" ||
    field.type === "multi_select" ||
    field.type === "user" ||
    field.type === "multi_user" ||
    field.type === "checkbox"
  ) {
    return "mt-2 min-w-0";
  }
  return "mt-2 min-w-0 overflow-hidden rounded-md border border-input bg-background shadow-xs";
}

function MobileFieldEditor({
  field,
  open,
  onOpenChange,
  editor,
  onCancel,
  onSave,
}: {
  field: DataField;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editor: ReactNode;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="bottom"
        showCloseButton={false}
        className="inset-x-4 bottom-[calc(var(--keyboard-safe-bottom)+env(safe-area-inset-bottom)+1rem)] h-auto max-h-[min(540px,calc(var(--visual-viewport-height)-2rem))] gap-0 overflow-hidden rounded-lg border p-0 sm:inset-x-6 sm:mx-auto sm:max-w-lg"
      >
        <SheetHeader className="border-b border-border/70 px-4 pt-4 pb-3 text-left">
          <SheetTitle className="text-base leading-6">{field.label}</SheetTitle>
          <SheetDescription className="sr-only">Edit field value</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 overflow-y-auto px-4 py-3">
          <div className={editorFrameClassName(field)}>{editor}</div>
        </div>
        <SheetFooter className="mt-0 flex-row justify-end border-t border-border/70 px-4 py-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" onClick={onSave}>
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function MobileFieldPicker({
  field,
  open,
  onOpenChange,
  editor,
  onCancel,
  onSave,
}: {
  field: DataField;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editor: ReactNode;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="bottom"
        showCloseButton={false}
        className="h-auto max-h-[min(620px,calc(var(--visual-viewport-height)-2rem))] gap-0 overflow-hidden rounded-xl border p-0 shadow-overlay"
        style={{
          right: "1rem",
          bottom: "calc(var(--keyboard-safe-bottom) + env(safe-area-inset-bottom) + 0.75rem)",
          left: "1rem",
        }}
      >
        <SheetHeader className="border-b border-border/70 px-4 pt-4 pb-3 text-left">
          <SheetTitle className="text-base leading-6">{field.label}</SheetTitle>
          <SheetDescription className="sr-only">Choose field value</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 overflow-y-auto px-4 py-3">
          <div className={editorFrameClassName(field)}>{editor}</div>
        </div>
        <SheetFooter className="mt-0 flex-row justify-end border-t border-border/70 px-4 pt-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)]">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" onClick={onSave}>
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function shouldUseMobileFieldEditor(field: DataField) {
  if (field.type === "date") return field.config?.include_time === true;
  return (
    field.type === "text" ||
    field.type === "url" ||
    field.type === "email" ||
    field.type === "number" ||
    field.type === "currency" ||
    field.type === "percent"
  );
}

function shouldUseMobilePicker(field: DataField) {
  return (
    field.type === "select" ||
    field.type === "multi_select" ||
    field.type === "user" ||
    field.type === "multi_user"
  );
}

function pickerOptionCount(field: DataField, workspaceMemberCount: number) {
  if (field.type === "select" || field.type === "multi_select") {
    return field.config?.options?.length ?? 0;
  }
  if (field.type === "user" || field.type === "multi_user") {
    return field.config?.users?.length ? field.config.users.length : workspaceMemberCount;
  }
  return 0;
}

function shouldUseMobileSearchPicker(field: DataField, workspaceMemberCount: number) {
  return shouldUseMobilePicker(field) && pickerOptionCount(field, workspaceMemberCount) > FIELD_OPTION_SEARCH_THRESHOLD;
}

function fieldListTriggerClassName(interactive: boolean, open = false) {
  return cn(
    "inline-flex max-w-full min-w-0 rounded-sm text-left outline-none transition-colors",
    interactive &&
      "-my-0.5 cursor-pointer px-1 py-0.5 hover:bg-hover-overlay focus-visible:ring-[3px] focus-visible:ring-ring-subtle",
    open && "bg-hover-overlay text-foreground",
  );
}

function tableCellTriggerClassName(interactive: boolean, open = false) {
  return cn(
    "flex h-full w-full min-w-0 items-center overflow-hidden px-2 py-2.5 text-left outline-none transition-colors",
    interactive && "cursor-pointer hover:bg-hover-overlay focus-visible:ring-[3px] focus-visible:ring-ring-subtle",
    open && "bg-hover-overlay text-foreground",
  );
}

export function FieldValuePopover({
  field,
  value,
  displayCount,
  cellWidth,
  availableWidth,
  className,
  onCommit,
  variant = "field-list",
}: {
  field: DataField;
  value: DataValue | undefined;
  displayCount?: number;
  cellWidth?: number;
  availableWidth?: number;
  className?: string;
  onCommit?: (value: DataValue) => unknown | Promise<unknown>;
  variant?: FieldValuePopoverVariant;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<DataValue | undefined>(value);
  const [optimisticValue, setOptimisticValue] = useState<DataValue | undefined>(value);
  const [truncated, setTruncated] = useState(false);
  const previewRef = useRef<HTMLSpanElement | null>(null);
  const compactOrTouchInput = useCompactOrTouchInput();
  const workspaceMemberProfiles = useWorkspaceMemberProfiles();
  const editable = !!onCommit && isEditableField(field);
  const fullViewCandidate = !editable && canOfferFullView(field, optimisticValue);
  const fullView = fullViewCandidate && truncated;
  const interactive = editable || fullView;
  const valueSignature = useMemo(() => fieldValueSignature(value), [value]);
  const optimisticSignature = useMemo(() => fieldValueSignature(optimisticValue), [optimisticValue]);
  const committedSignatureRef = useRef(valueSignature);
  const tableCell = variant === "table-cell";
  const mobileFieldListEdit =
    editable && variant === "field-list" && compactOrTouchInput && shouldUseMobileFieldEditor(field);
  const mobileFieldListPicker =
    editable &&
    variant === "field-list" &&
    compactOrTouchInput &&
    shouldUseMobileSearchPicker(field, workspaceMemberProfiles.size);

  useEffect(() => {
    committedSignatureRef.current = valueSignature;
    setOptimisticValue(value);
  }, [valueSignature]);

  useEffect(() => {
    if (!open) setDraft(optimisticValue);
  }, [open, optimisticSignature, optimisticValue]);

  useEffect(() => {
    if (!fullViewCandidate) {
      setTruncated(false);
      return;
    }
    const node = previewRef.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const measure = () => {
      const next =
        node.scrollWidth > node.clientWidth + 2 || node.scrollHeight > node.clientHeight + 2;
      setTruncated((current) => (current === next ? current : next));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [displayCount, fullViewCandidate, optimisticSignature, variant]);

  const commitDraft = (nextValue: DataValue | undefined = draft) => {
    if (!editable || !onCommit) return;
    const committedValue = (nextValue ?? null) as DataValue;
    const nextSignature = fieldValueSignature(committedValue);
    if (nextSignature === committedSignatureRef.current) return;

    const previousValue = optimisticValue;
    const previousSignature = committedSignatureRef.current;
    const rollback = () => {
      if (committedSignatureRef.current !== nextSignature) return;
      committedSignatureRef.current = previousSignature;
      setDraft(previousValue);
      setOptimisticValue(previousValue);
    };

    committedSignatureRef.current = nextSignature;
    setDraft(committedValue);
    setOptimisticValue(committedValue);

    try {
      const result = onCommit(committedValue);
      if (result && typeof (result as Promise<unknown>).then === "function") {
        void Promise.resolve(result).catch(rollback);
      }
    } catch {
      rollback();
    }
  };

  const preview = (insideButton: boolean) => {
    const useRenderedPreview = insideButton
      ? canUseRenderedButtonPreview(field, variant)
      : true;
    if (!useRenderedPreview) {
      const singleLine = tableCell || field.type === "url" || field.type === "email";
      return (
        <span
          ref={previewRef}
          data-field-value-preview
          className={cn(
            "block min-w-0 overflow-hidden text-sm leading-5",
            singleLine ? "truncate whitespace-nowrap" : "whitespace-pre-wrap [overflow-wrap:anywhere]",
          )}
        >
          {compactPreviewText(field, optimisticValue, displayCount)}
        </span>
      );
    }
    return (
      <span
        ref={previewRef}
        data-field-value-preview
        className={cn("block min-w-0 max-w-full", tableCell && "truncate whitespace-nowrap")}
      >
        <FieldValue
          value={optimisticValue}
          field={field}
          displayCount={tableCell ? displayCount : 999}
          cellWidth={cellWidth}
          availableWidth={availableWidth}
          overflowBadgeTrigger={insideButton ? "span" : "button"}
          wrapText={!tableCell}
        />
      </span>
    );
  };

  if (!interactive) {
    return (
      <span
        className={cn(
          tableCell ? tableCellTriggerClassName(false) : fieldListTriggerClassName(false),
          className,
        )}
      >
        {preview(false)}
      </span>
    );
  }

  const renderEditor = (autoFocus = true, presentation: "popover" | "sheet" = "popover") => (
    <FieldValue
      mode="edit"
      value={draft}
      field={field}
      autoFocus={autoFocus}
      presentation={presentation}
      onChange={setDraft}
      onCommit={(nextValue) => {
        setDraft(nextValue);
        commitDraft(nextValue);
        setOpen(false);
      }}
    />
  );
  const editor = renderEditor();

  if (mobileFieldListEdit) {
    return (
      <div className={cn("min-w-0", className)} onClick={(event) => event.stopPropagation()}>
        <button
          type="button"
          className={fieldListTriggerClassName(true, open)}
          onClick={() => setOpen((current) => !current)}
        >
          {preview(true)}
        </button>
        <MobileFieldEditor
          field={field}
          open={open}
          onOpenChange={(nextOpen) => setOpen(nextOpen)}
          editor={editor}
          onCancel={() => setOpen(false)}
          onSave={() => {
            commitDraft();
            setOpen(false);
          }}
        />
      </div>
    );
  }

  if (mobileFieldListPicker) {
    return (
      <div className={cn("min-w-0", className)} onClick={(event) => event.stopPropagation()}>
        <button
          type="button"
          className={fieldListTriggerClassName(true, open)}
          onClick={() => setOpen((current) => !current)}
        >
          {preview(true)}
        </button>
        <MobileFieldPicker
          field={field}
          open={open}
          onOpenChange={(nextOpen) => setOpen(nextOpen)}
          editor={renderEditor(false, "sheet")}
          onCancel={() => setOpen(false)}
          onSave={() => {
            commitDraft();
            setOpen(false);
          }}
        />
      </div>
    );
  }

  return (
    <Popover
      modal={editable}
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && open) commitDraft();
        setOpen(nextOpen);
      }}
    >
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            tableCell ? tableCellTriggerClassName(true, open) : fieldListTriggerClassName(true, open),
            className,
          )}
          onClick={(event) => event.stopPropagation()}
        >
          {preview(true)}
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        side="bottom"
        className={popoverContentClassName(field, editable)}
        onClick={(event) => event.stopPropagation()}
      >
        {editable ? (
          editor
        ) : (
          <div className="max-h-80 overflow-auto text-sm leading-5">
            {field.type === "url" || field.type === "email" ? (
              <div className="overflow-x-auto whitespace-nowrap">{primitiveLabel(optimisticValue)}</div>
            ) : field.type === "text" ? (
              <div className="whitespace-pre-wrap [overflow-wrap:anywhere]">{primitiveLabel(optimisticValue)}</div>
            ) : (
              <FieldValue value={optimisticValue} field={field} displayCount={999} wrapText />
            )}
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
