import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DataTable } from "../components/DataTable";
import { IconBtn, IconOpen } from "../components/IconBtn";
import { Notice } from "../components/Notice";
import { Badge, EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { dash, formatDateTime } from "../lib/format";
import { LEGAL_LABELS, LEGAL_OPTIONS } from "../lib/options";

export function LegalPage() {
  const { success } = useFlashSuccess();
  const { data, error: loadError } = useQuery({
    queryKey: ["admin-legal-list"],
    queryFn: async () =>
      Promise.all(
        LEGAL_OPTIONS.map(async (option) => {
          const doc = await adminApi.legal(option.value);
          return { ...doc, type: option.value };
        }),
      ),
  });

  return (
    <div>
      <div className="page-head">
        <h1>Документы</h1>
      </div>
      <Notice error={loadError ? apiError(loadError, "Не удалось загрузить документы") : ""} success={success} />
      <DataTable
        rows={data ?? []}
        columns={[
          {
            key: "type",
            label: "Документ",
            render: (row) => (
              <EntityCell
                avatar={String(LEGAL_LABELS[String(row.type)] ?? "Д").slice(0, 1)}
                title={LEGAL_LABELS[String(row.type)] ?? String(row.type)}
                subtitle={`версия ${dash(row.version)}`}
              />
            ),
          },
          {
            key: "kind",
            label: "Содержимое",
            render: (row) =>
              row.file_url ? <Badge tone="lime">файл</Badge> : <Badge tone="blue">текст</Badge>,
          },
          {
            key: "file_name",
            label: "Файл",
            render: (row) => dash(row.file_name),
          },
          {
            key: "published_at",
            label: "Обновлён",
            render: (row) => formatDateTime(row.published_at),
          },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <div className="row-actions">
                <IconBtn to={`/legal/${row.type}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
