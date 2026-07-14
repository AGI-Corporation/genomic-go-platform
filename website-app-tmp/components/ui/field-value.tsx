"use client";

import type { DataField, DataValue } from "@/components/ui/data-types";
import { AttachmentFieldView } from "@/components/ui/field-values/attachment-field-value";
import { CheckboxFieldEdit, CheckboxFieldView } from "@/components/ui/field-values/checkbox-field-value";
import { DateFieldEdit, DateFieldView } from "@/components/ui/field-values/date-field-value";
import {
  CurrencyFieldView,
  NumberFieldEdit,
  NumberFieldView,
  PercentFieldView,
} from "@/components/ui/field-values/number-field-value";
import { RelationFieldView } from "@/components/ui/field-values/relation-field-value";
import {
  MultiSelectFieldEdit,
  MultiSelectFieldView,
  SelectFieldEdit,
  SelectFieldView,
} from "@/components/ui/field-values/select-field-value";
import { EmptyValue, emptyValue, type FieldValueEditProps, type FieldValueViewProps } from "@/components/ui/field-values/shared";
import { TextFieldEdit, TextFieldView } from "@/components/ui/field-values/text-field-value";
import { UrlFieldEdit, UrlFieldView } from "@/components/ui/field-values/url-field-value";
import {
  MultiUserFieldEdit,
  MultiUserFieldView,
  UserFieldEdit,
  UserFieldView,
} from "@/components/ui/field-values/user-field-value";

export type FieldValueMode = "view" | "edit";

export interface FieldValueProps extends FieldValueViewProps {
  mode?: FieldValueMode;
  onChange?: (value: DataValue) => void;
  onCommit?: (value: DataValue) => void;
  autoFocus?: boolean;
  presentation?: "popover" | "sheet";
}

export function isEditableFieldType(type: string) {
  return new Set([
    "text",
    "number",
    "currency",
    "percent",
    "select",
    "multi_select",
    "date",
    "checkbox",
    "user",
    "multi_user",
    "url",
    "email",
  ]).has(type);
}

export function isEditableField(field: Pick<DataField, "type" | "editable" | "system">) {
  return field.editable === true && isEditableFieldType(field.type);
}

function editProps(props: FieldValueProps): FieldValueEditProps {
  return {
    value: props.value,
    field: props.field,
    onChange: props.onChange ?? (() => undefined),
    onCommit: props.onCommit ?? (() => undefined),
    autoFocus: props.autoFocus,
    presentation: props.presentation,
  };
}

function ViewValue(props: FieldValueViewProps) {
  if (emptyValue(props.value)) return <EmptyValue />;

  switch (props.field.type) {
    case "number":
      return <NumberFieldView {...props} />;
    case "currency":
      return <CurrencyFieldView {...props} />;
    case "percent":
      return <PercentFieldView {...props} />;
    case "select":
      return <SelectFieldView {...props} />;
    case "multi_select":
      return <MultiSelectFieldView {...props} />;
    case "date":
      return <DateFieldView {...props} />;
    case "checkbox":
      return <CheckboxFieldView {...props} />;
    case "user":
      return <UserFieldView {...props} />;
    case "multi_user":
      return <MultiUserFieldView {...props} />;
    case "url":
    case "email":
      return <UrlFieldView {...props} />;
    case "attachment":
      return <AttachmentFieldView {...props} />;
    case "relation":
      return <RelationFieldView {...props} />;
    case "text":
    default:
      return <TextFieldView {...props} />;
  }
}

function EditValue(props: FieldValueProps) {
  switch (props.field.type) {
    case "number":
    case "currency":
    case "percent":
      return <NumberFieldEdit {...editProps(props)} />;
    case "select":
      return <SelectFieldEdit {...editProps(props)} />;
    case "multi_select":
      return <MultiSelectFieldEdit {...editProps(props)} />;
    case "date":
      return <DateFieldEdit {...editProps(props)} />;
    case "checkbox":
      return <CheckboxFieldEdit {...editProps(props)} />;
    case "user":
      return <UserFieldEdit {...editProps(props)} />;
    case "multi_user":
      return <MultiUserFieldEdit {...editProps(props)} />;
    case "url":
    case "email":
      return <UrlFieldEdit {...editProps(props)} />;
    case "text":
      return <TextFieldEdit {...editProps(props)} />;
    default:
      return <ViewValue {...props} wrapText />;
  }
}

export function FieldValue(props: FieldValueProps) {
  return props.mode === "edit" ? <EditValue {...props} /> : <ViewValue {...props} />;
}
