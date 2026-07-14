"use client";

import { useEffect, useRef } from "react";
import { FileText } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  commitOnEnter,
  primitiveLabel,
  type FieldValueEditProps,
  type FieldValueViewProps,
} from "./shared";

export function TextFieldView({ value, wrapText, className }: FieldValueViewProps) {
  const text = primitiveLabel(value);
  const textNode = (
    <span
      className={cn(
        "block min-w-0 max-w-full",
        wrapText ? "whitespace-pre-wrap break-words [overflow-wrap:anywhere]" : "truncate",
        className,
      )}
    >
      {text}
    </span>
  );

  if (value && typeof value === "object") {
    return (
      <span className={cn("inline-flex max-w-full items-center gap-1", className)}>
        <FileText className="icon-12 shrink-0 text-muted-foreground" />
        {textNode}
      </span>
    );
  }
  return textNode;
}

export function TextFieldEdit({
  value,
  field,
  onChange,
  onCommit,
  autoFocus,
}: FieldValueEditProps) {
  const text = primitiveLabel(value);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!autoFocus) return;
    const textarea = textareaRef.current;
    if (!textarea) return;
    const frame = window.requestAnimationFrame(() => {
      textarea.focus();
      const end = textarea.value.length;
      textarea.setSelectionRange(end, end);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [autoFocus, text]);

  return (
    <Textarea
      ref={textareaRef}
      autoFocus={autoFocus}
      name={field.key}
      value={text}
      placeholder="Press enter to submit"
      className="max-h-72 min-h-24 resize-y border-0 bg-transparent p-3 shadow-none focus-visible:ring-0"
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={(event) => commitOnEnter(event, event.currentTarget.value, onCommit)}
    />
  );
}
