import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { adminApi } from "../api/resources";
import { DataTable, Toolbar } from "../components/DataTable";
import { IconBtn, IconOpen } from "../components/IconBtn";
import { Notice } from "../components/Notice";
import { Badge, EntityCell } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { initials, labelOf, personName } from "../lib/format";
import { CLIENT_STATUS_LABELS } from "../lib/options";

export function ClientsPage() {
  const [q, setQ] = useState("");
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-clients", q],
    queryFn: () => adminApi.clients({ q, page: 1, page_size: 50 }),
  });

  return (
    <div>
      <div className="page-head">
        <h1>Клиенты</h1>
      </div>
      <Notice error={error ? apiError(error, "Не удалось загрузить клиентов") : ""} />
      <Toolbar>
        <input placeholder="Тренер или клиент" value={q} onChange={(e) => setQ(e.target.value)} />
      </Toolbar>
      {isLoading ? <p className="muted">Загрузка...</p> : (
        <DataTable
          rows={data?.items ?? []}
          empty={q ? "Ничего не найдено" : "Пока нет клиентов"}
          emptyHint={q ? "Попробуйте изменить запрос." : "Связи тренер–клиент появятся здесь, когда тренер добавит клиента."}
          columns={[
          { key: "id", label: "Связь" },
          {
            key: "trainer",
            label: "Тренер",
            render: (row) => (
              <EntityCell
                avatar={initials(row.trainer_first, row.trainer_last)}
                title={personName(row.trainer_first, row.trainer_last)}
              />
            ),
          },
          {
            key: "client",
            label: "Клиент",
            render: (row) => (
              <EntityCell
                avatar={initials(row.client_first, row.client_last)}
                title={personName(row.client_first, row.client_last)}
              />
            ),
          },
          {
            key: "status",
            label: "Статус",
            render: (row) => <Badge tone={row.status === "permanent" ? "lime" : "muted"}>{labelOf(CLIENT_STATUS_LABELS, row.status)}</Badge>,
          },
          { key: "created_at", label: "Создан" },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <IconBtn to={`/clients/${row.id}`} title="Открыть">
                <IconOpen />
              </IconBtn>
            ),
          },
        ]}
        />
      )}
    </div>
  );
}
