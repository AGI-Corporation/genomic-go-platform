"use client";

import { Paperclip } from "lucide-react";
import { Fragment, useState } from "react";
import { FilePreviewDialog } from "@/components/ui/file-preview";
import { type OverflowItem, OverflowList } from "@/components/ui/overflow-list";
import { previewKylonFile, type KylonPreviewFile } from "@/lib/kylon/bridge";
import { cn } from "@/lib/utils";
import {
  ATTACH_FONT,
  BADGE_GAP,
  fieldAvailableWidth,
  isObjectValue,
  measureTextWidth,
  primitiveLabel,
  toArray,
  visibleItemCount,
  type FieldValueViewProps,
} from "./shared";

interface AttachmentPreviewFile extends KylonPreviewFile {
  name: string;
  contentType?: string | null;
  previewUrl?: string | null;
  directUrl?: string | null;
  downloadUrl?: string | null;
}

const ATTACH_FIXED_WIDTH = 14 + 6 + 16;

function textValue(value: unknown): string | null {
  if (typeof value === "string") return value.length > 0 ? value : null;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return null;
}

function objectStringValue(objectValue: Record<string, unknown>, key: string | undefined): string | null {
  if (!key) return null;
  return textValue(objectValue[key]);
}

function firstObjectStringValue(objectValue: Record<string, unknown>, keys: Array<string | undefined>): string | null {
  for (const key of keys) {
    const value = objectStringValue(objectValue, key);
    if (value) return value;
  }
  return null;
}

function attachmentLabel(field: FieldValueViewProps["field"], value: unknown): string {
  const objectValue = isObjectValue(value) ? value : null;
  const config = field.config?.attachment;
  if (objectValue) {
    const configuredLabel = firstObjectStringValue(objectValue, [
      config?.label_field,
      "fileName",
      "filename",
      "name",
      "label",
      config?.file_id_field,
      "workspaceFileId",
      "id",
      "url",
    ]);
    return configuredLabel ?? "Untitled file";
  }
  return primitiveLabel(value) || "Untitled file";
}

function attachmentPreviewFile(field: FieldValueViewProps["field"], value: unknown): AttachmentPreviewFile {
  const objectValue = isObjectValue(value) ? value : {};
  const config = field.config?.attachment;
  const label = attachmentLabel(field, value);
  const source = config?.source;
  const primitiveFileId = isObjectValue(value) ? null : textValue(value);
  const id = firstObjectStringValue(objectValue, ["id"]) ?? primitiveFileId;
  const configuredFileId = firstObjectStringValue(objectValue, [
    config?.file_id_field,
    "workspaceFileId",
    "fileId",
    "workspace_file_id",
  ]);
  const previewUrl = firstObjectStringValue(objectValue, [
    config?.preview_url_field,
    config?.url_field,
    "previewUrl",
    "url",
  ]);
  const directUrl = firstObjectStringValue(objectValue, [
    config?.direct_url_field,
    config?.url_field,
    "directUrl",
    "url",
  ]);
  const downloadUrl = firstObjectStringValue(objectValue, [
    config?.download_url_field,
    config?.url_field,
    "downloadUrl",
    "url",
  ]);
  const contentType = firstObjectStringValue(objectValue, [config?.content_type_field, "contentType"]);

  return {
    id,
    source,
    workspaceId: firstObjectStringValue(objectValue, ["workspaceId"]),
    workspaceFileId: configuredFileId ?? (source === "workspace_file" || primitiveFileId ? id : null),
    name: label,
    contentType,
    previewUrl,
    directUrl,
    downloadUrl,
  };
}

export function AttachmentFieldView({
  value,
  field,
  cellWidth,
  availableWidth,
  displayCount,
  className,
}: FieldValueViewProps) {
  const [previewFile, setPreviewFile] = useState<AttachmentPreviewFile | null>(null);
  const values = toArray(value);
  const resolvedAvailableWidth = fieldAvailableWidth(cellWidth, availableWidth);
  const items: OverflowItem[] = values.map((item, index) => {
    const label = attachmentLabel(field, item);
    const file = attachmentPreviewFile(field, item);
    return {
      key: `${file.workspaceFileId ?? file.id ?? label}-${index}`,
      element: (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            const handled = previewKylonFile(file, () => setPreviewFile(file));
            if (!handled) setPreviewFile(file);
          }}
          className="inline-flex max-w-[148px] items-center gap-1.5 rounded-sm border border-border/60 bg-muted/40 px-2 py-1 text-left text-xs font-normal hover:bg-muted"
        >
          <Paperclip className="icon-12 shrink-0 text-muted-foreground" />
          <span className="truncate">{label}</span>
        </button>
      ),
    };
  });
  const visibleCount = visibleItemCount({
    itemWidths: values.map((item) => {
      const textWidth = Math.min(measureTextWidth(attachmentLabel(field, item), ATTACH_FONT), 120);
      return ATTACH_FIXED_WIDTH + textWidth;
    }),
    availableWidth: resolvedAvailableWidth,
    gap: BADGE_GAP,
    displayCount: displayCount ?? (resolvedAvailableWidth == null ? field.config?.max_visible ?? 2 : undefined),
  });

  return (
    <>
      {visibleCount >= items.length ? (
        <span className={cn("flex min-w-0 flex-wrap items-center gap-1 overflow-hidden", className)}>
          {items.map((item) => (
            <Fragment key={item.key}>{item.element}</Fragment>
          ))}
        </span>
      ) : (
        <OverflowList
          items={items}
          visibleCount={visibleCount}
          className={className}
          renderPopoverContent={(hidden) => (
            <div className="flex flex-wrap items-center gap-1">
              {hidden.map((item) => (
                <span key={item.key} className="inline-flex items-center leading-none">
                  {item.element}
                </span>
              ))}
            </div>
          )}
        />
      )}
      {previewFile ? (
        <FilePreviewDialog
          open={!!previewFile}
          onOpenChange={(open) => {
            if (!open) setPreviewFile(null);
          }}
          workspaceId={previewFile.workspaceId}
          fileId={previewFile.workspaceFileId}
          name={previewFile.name}
          contentType={previewFile.contentType}
          previewUrl={previewFile.previewUrl}
          directUrl={previewFile.directUrl}
          downloadUrl={previewFile.downloadUrl}
        />
      ) : null}
    </>
  );
}
