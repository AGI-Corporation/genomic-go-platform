import type { MouseEvent } from 'react';
import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react';
import type { DataColumn } from '@/components/ui/data-types';
import {
  DEFAULT_COLUMN_WIDTH,
  MIN_COLUMN_WIDTH,
  MIN_TITLE_WIDTH,
  defaultColumnWidth,
  loadColumnWidths,
  saveColumnWidths,
} from './data-table-utils';

const useBrowserLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;

interface UseDataTableColumnWidthsInput<TRow> {
  columns: DataColumn<TRow>[];
  titleColumnWidthKey: string;
  columnWidthStorageKey?: string;
}

export function useDataTableColumnWidths<TRow>({
  columns,
  titleColumnWidthKey,
  columnWidthStorageKey,
}: UseDataTableColumnWidthsInput<TRow>) {
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const storageKey =
    columnWidthStorageKey ?? `kylon:data-table:${columns.map((column) => column.key).join('|')}:column-widths`;
  const defaultWidths = useMemo(
    () =>
      Object.fromEntries(
        columns.map((column) => [column.key, defaultColumnWidth(column, column.key === titleColumnWidthKey)])
      ),
    [columns, titleColumnWidthKey]
  );
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => defaultWidths);
  const columnWidthSignature = useMemo(
    () => `${storageKey}:${columns.map((column) => `${column.key}:${defaultWidths[column.key]}`).join('|')}`,
    [columns, defaultWidths, storageKey]
  );
  const [loadedColumnWidthSignature, setLoadedColumnWidthSignature] = useState<string | null>(null);
  const columnWidthsReady = loadedColumnWidthSignature === columnWidthSignature;

  useBrowserLayoutEffect(() => {
    setColumnWidths(loadColumnWidths(storageKey, defaultWidths, titleColumnWidthKey));
    setLoadedColumnWidthSignature(columnWidthSignature);
  }, [columnWidthSignature, defaultWidths, storageKey, titleColumnWidthKey]);

  const setColumnWidth = useCallback(
    (key: string, width: number) => {
      const minWidth = key === titleColumnWidthKey ? MIN_TITLE_WIDTH : MIN_COLUMN_WIDTH;
      setColumnWidths((current) => {
        const next = { ...current, [key]: Math.max(minWidth, Math.round(width)) };
        saveColumnWidths(storageKey, next);
        return next;
      });
    },
    [storageKey, titleColumnWidthKey]
  );

  const startColumnResize = useCallback(
    (event: MouseEvent<HTMLElement>, column: DataColumn<TRow>) => {
      event.preventDefault();
      event.stopPropagation();
      const key = column.key;
      setResizingColumn(key);
      const startX = event.clientX;
      const startWidth = columnWidths[key] ?? defaultColumnWidth(column, key === titleColumnWidthKey);
      const previousCursor = document.body.style.cursor;
      const previousUserSelect = document.body.style.userSelect;

      const handleMouseMove = (moveEvent: globalThis.MouseEvent) => {
        setColumnWidth(key, startWidth + moveEvent.clientX - startX);
      };

      const handleMouseUp = () => {
        setResizingColumn(null);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = previousCursor;
        document.body.style.userSelect = previousUserSelect;
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [columnWidths, setColumnWidth, titleColumnWidthKey]
  );

  const gridTemplateColumns = columns.map((column) => `${columnWidths[column.key] ?? defaultWidths[column.key]}px`).join(' ');
  const tableWidth = columns.reduce(
    (sum, column) => sum + (columnWidths[column.key] ?? defaultWidths[column.key] ?? DEFAULT_COLUMN_WIDTH),
    0
  );

  return {
    columnWidths,
    columnWidthsReady,
    defaultWidths,
    gridTemplateColumns,
    resizingColumn,
    startColumnResize,
    tableWidth,
  };
}
