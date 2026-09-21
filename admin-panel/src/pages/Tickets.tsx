import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { adminApi } from "../api/resources";
import { DataTable } from "../components/DataTable";
import { IconBtn, IconOpen } from "../components/IconBtn";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { initials } from "../lib/format";
import { TICKET_STATUS_OPTIONS } from "../lib/options";

export function TicketsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();
  const { data, error: loadError } = useQuery({ queryKey: ["admin-tickets"], queryFn: adminApi.tickets });

  async function onStatus(id: number, status: string) {
    setError("");
    setSuccess("");
    try {
      await adminApi.setTicketStatus(id, status);
      await queryClient.invalidateQueries({ queryKey: ["admin-tickets"] });
      setSuccess("Статус обращения обновлён");
    } catch (err) {
      setError(apiError(err, "Не удалось обновить статус"));
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>Обращения</h1>
      </div>
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить обращения") : "")} success={success} />
      <DataTable
        rows={data ?? []}
        columns={[
          {
            key: "subject",
            label: "Обращение",
            render: (row) => (
              <EntityCell
                avatar={initials(row.subject)}
                title={String(row.subject ?? "—")}
                subtitle={String(row.email ?? "—")}
              />
            ),
          },
          {
            key: "status",
            label: "Статус",
            render: (row) => (
              <Select
                value={String(row.status)}
                onChange={(status) => void onStatus(Number(row.id), status)}
                options={TICKET_STATUS_OPTIONS}
              />
            ),
          },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <IconBtn to={`/tickets/${row.id}`} title="Открыть">
                <IconOpen />
              </IconBtn>
            ),
          },
        ]}
      />
    </div>
  );
}
