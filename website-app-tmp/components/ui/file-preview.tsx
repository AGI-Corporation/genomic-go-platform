"use client";

import { Download, ExternalLink, FileText, ImageIcon, X } from "lucide-react";
import Image from "next/image";
import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface FilePreviewProps {
  workspaceId?: string | null;
  fileId?: string | null;
  name: string;
  contentType?: string | null;
  previewUrl?: string | null;
  directUrl?: string | null;
  downloadUrl?: string | null;
  productBaseUrl?: string | null;
  onClose?: () => void;
  className?: string;
}

export interface FilePreviewDialogProps extends FilePreviewProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function productBase(input?: string | null): string | null {
  const value = input ?? process.env.NEXT_PUBLIC_KYLON_PRODUCT_APP_URL;
  if (!value) return null;
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function workspacePreviewUrl({
  workspaceId,
  fileId,
  productBaseUrl,
}: {
  workspaceId?: string | null;
  fileId?: string | null;
  productBaseUrl?: string | null;
}) {
  if (!workspaceId || !fileId) return null;
  const base = productBase(productBaseUrl);
  if (!base) return null;
  return new URL(`/preview/workspaces/${workspaceId}/files/${fileId}`, base).href;
}

function isImage(contentType: string | null | undefined, name: string) {
  if (contentType?.startsWith("image/")) return true;
  return /\.(png|jpe?g|gif|svg|webp|avif)$/i.test(name);
}

export function FilePreview({
  workspaceId,
  fileId,
  name,
  contentType,
  previewUrl,
  directUrl,
  downloadUrl,
  productBaseUrl,
  onClose,
  className,
}: FilePreviewProps) {
  const resolvedPreviewUrl = useMemo(
    () => previewUrl ?? workspacePreviewUrl({ workspaceId, fileId, productBaseUrl }),
    [fileId, previewUrl, productBaseUrl, workspaceId],
  );
  const resolvedDownloadUrl = downloadUrl ?? directUrl ?? resolvedPreviewUrl;
  const image = isImage(contentType, name);

  return (
    <section
      className={cn(
        "flex min-h-[320px] min-w-0 flex-col overflow-hidden rounded-md border border-border bg-card",
        className,
      )}
    >
      <header className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-3">
        <div className="flex min-w-0 items-center gap-2">
          {image ? (
            <ImageIcon className="icon-16 shrink-0 text-muted-foreground" />
          ) : (
            <FileText className="icon-16 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate text-sm font-medium">{name}</span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {resolvedPreviewUrl ? (
            <Button variant="ghost" size="icon" asChild aria-label="Open file in Kylon">
              <a href={resolvedPreviewUrl} target="_blank" rel="noreferrer">
                <ExternalLink className="icon-14" />
              </a>
            </Button>
          ) : null}
          {resolvedDownloadUrl ? (
            <Button variant="ghost" size="icon" asChild aria-label="Download file">
              <a href={resolvedDownloadUrl} download>
                <Download className="icon-14" />
              </a>
            </Button>
          ) : null}
          {onClose ? (
            <Button type="button" variant="ghost" size="icon" aria-label="Close file preview" onClick={onClose}>
              <X className="icon-14" />
            </Button>
          ) : null}
        </div>
      </header>
      <div className="min-h-0 flex-1 bg-background">
        {image && directUrl ? (
          <div className="relative h-full min-h-[280px]">
            <Image src={directUrl} alt={name} fill unoptimized className="object-contain p-3" />
          </div>
        ) : resolvedPreviewUrl ? (
          <iframe
            title={name}
            src={resolvedPreviewUrl}
            className="h-full min-h-[280px] w-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
          />
        ) : (
          <div className="flex h-full min-h-[280px] items-center justify-center px-4 text-center text-sm text-muted-foreground">
            File preview needs a workspace id and file id, or an explicit preview URL.
          </div>
        )}
      </div>
    </section>
  );
}

export function FilePreviewDialog({
  open,
  onOpenChange,
  className,
  ...file
}: FilePreviewDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="flex h-[85dvh] max-h-[calc(var(--visual-viewport-height)-2rem)] w-[calc(100vw-2rem)] max-w-[calc(100vw-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-4xl"
      >
        <DialogTitle className="sr-only">{file.name}</DialogTitle>
        <DialogDescription className="sr-only">File preview</DialogDescription>
        <FilePreview
          {...file}
          onClose={() => onOpenChange(false)}
          className={cn("h-full min-h-0 rounded-none border-0", className)}
        />
      </DialogContent>
    </Dialog>
  );
}
