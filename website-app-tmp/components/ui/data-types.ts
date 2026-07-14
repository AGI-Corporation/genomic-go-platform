import type {
  CanonicalFieldValue,
  FieldConfig,
  FieldType,
  SelectOption,
  UserOption,
} from "@/lib/app-definition/types";

export type DataValue = CanonicalFieldValue;
export type DataFieldType = FieldType;
export type DataFieldConfig = FieldConfig;
export type DataOption = SelectOption;
export type DataUserOption = UserOption;

export interface DataField {
  key: string;
  label: string;
  type: DataFieldType;
  required?: boolean;
  sortable?: boolean;
  width?: number;
  editable?: boolean;
  system?: boolean;
  config?: DataFieldConfig;
}

export interface DataRow {
  id: string;
  values: Record<string, DataValue>;
  updatedAt?: string;
}

export interface DataColumn<TRow = DataRow> extends DataField {
  getValue?: (row: TRow) => DataValue | undefined;
  compareValue?: (row: TRow) => string | number;
}

export interface DataSortState {
  column: string;
  direction: "asc" | "desc";
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function dataValueFromRow<TRow>(row: TRow, column: DataColumn<TRow>): DataValue | undefined {
  if (column.getValue) return column.getValue(row);
  if (!isObjectRecord(row)) return undefined;

  const nestedValues = row.values;
  if (isObjectRecord(nestedValues)) {
    return nestedValues[column.key] as DataValue | undefined;
  }

  return row[column.key] as DataValue | undefined;
}
