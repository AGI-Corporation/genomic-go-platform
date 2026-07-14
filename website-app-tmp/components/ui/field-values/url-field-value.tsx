"use client";

import { ExternalLink, Mail } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { commitOnEnter, primitiveLabel, type FieldValueEditProps, type FieldValueViewProps } from "./shared";

export function UrlFieldView({ value, field, className }: FieldValueViewProps) {
  const text = primitiveLabel(value);
  const href = field.type === "email" ? `mailto:${text}` : text;
  return (
    <a
      href={href}
      target={field.type === "email" ? undefined : "_blank"}
      rel={field.type === "email" ? undefined : "noopener noreferrer"}
      onClick={(event) => event.stopPropagation()}
      className={cn(
        "inline-flex max-w-full min-w-0 items-center gap-1 text-sm leading-5 text-primary underline-offset-4 hover:underline",
        className,
      )}
    >
      {field.type === "email" ? <Mail className="icon-12 shrink-0" /> : <ExternalLink className="icon-12 shrink-0" />}
      <span className="min-w-0 truncate">{field.type === "email" ? text : text.replace(/^https?:\/\//i, "")}</span>
    </a>
  );
}

export function UrlFieldEdit({ value, field, onChange, onCommit, autoFocus }: FieldValueEditProps) {
  const text = primitiveLabel(value);
  return (
    <Input
      autoFocus={autoFocus}
      type={field.type === "email" ? "email" : "url"}
      name={field.key}
      value={text}
      placeholder="Press enter to submit"
      className="border-0 bg-transparent px-3 shadow-none focus-visible:ring-0"
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={(event) => commitOnEnter(event, event.currentTarget.value, onCommit)}
    />
  );
}
