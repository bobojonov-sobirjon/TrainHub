import type { ReactNode } from "react";
import { formatValue, isDateLike } from "../lib/format";

type Column = {
  key: string;
  label: string;
  /** Extra class names (e.g. col-hide-sm for responsive). */
  className?: string;
  render?: (row: Record<string, unknown>, index: number) => ReactNode;
};

function cell(value: unknown) {
  if (isDateLike(value)) return formatValue(value);
  return formatValue(value);
}

function columnClass(column: Column) {
  const parts: string[] = [];
  if (column.key === "actions") parts.push("col-actions");
  if (column.key === "id" || column.key === "n") parts.push("col-id");
  if (column.className) parts.push(column.className);
  return parts.length ? parts.join(" ") : undefined;
}

export function DataTable({
  columns,
  rows,
  empty = "Пока нет данных",
  emptyHint,
  className,
}: {
  columns: Column[];
  rows: Record<string, unknown>[];
  empty?: string;
  emptyHint?: string;
  className?: string;
}) {
  const wrapClass = ["table-wrap", className].filter(Boolean).join(" ");
  if (!rows.length) {
    return (
      <div className={wrapClass}>
        <div className="table-empty">
          <strong>{empty}</strong>
          {emptyHint ? <span>{emptyHint}</span> : null}
        </div>
      </div>
    );
  }
  return (
    <div className={wrapClass}>
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={columnClass(column)}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? row.type ?? index)}>
              {columns.map((column) => (
                <td key={column.key} className={columnClass(column)}>
                  {column.render
                    ? column.render(row, index)
                    : column.key === "n"
                      ? index + 1
                      : cell(row[column.key])}
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
