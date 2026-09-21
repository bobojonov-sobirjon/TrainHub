import type { ReactNode } from "react";
import { formatValue, isDateLike } from "../lib/format";

type Column = {
  key: string;
  label: string;
  render?: (row: Record<string, unknown>) => ReactNode;
};

function cell(value: unknown) {
  if (isDateLike(value)) return formatValue(value);
  return formatValue(value);
}

function columnClass(key: string) {
  if (key === "actions") return "col-actions";
  if (key === "id") return "col-id";
  return undefined;
}

export function DataTable({
  columns,
  rows,
  empty = "Пока нет данных",
  emptyHint,
}: {
  columns: Column[];
  rows: Record<string, unknown>[];
  empty?: string;
  emptyHint?: string;
}) {
  if (!rows.length) {
    return (
      <div className="table-wrap">
        <div className="table-empty">
          <strong>{empty}</strong>
          {emptyHint ? <span>{emptyHint}</span> : null}
        </div>
      </div>
    );
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={columnClass(column.key)}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? row.type ?? index)}>
              {columns.map((column) => (
                <td key={column.key} className={columnClass(column.key)}>
                  {column.render ? column.render(row) : cell(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Toolbar({ children }: { children?: ReactNode }) {
  return <div className="toolbar">{children}</div>;
}
