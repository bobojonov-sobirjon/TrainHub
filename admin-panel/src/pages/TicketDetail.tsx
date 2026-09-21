import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, InfoGrid, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { dash, formatDateTime, initials, labelOf } from "../lib/format";
import { TICKET_STATUS_LABELS, TICKET_STATUS_OPTIONS } from "../lib/options";

function ticketTone(status: unknown) {
  if (status === "closed") return "muted" as const;
  if (status === "answered") return "lime" as const;
  if (status === "in_progress") return "blue" as const;
  return "orange" as const;
}

export function TicketDetailPage() {
  const { id } = useParams();
  const ticketId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-ticket", ticketId],
    queryFn: () => adminApi.ticket(ticketId),
    enabled: Number.isFinite(ticketId),
  });

  async function onStatus(status: string) {
    setError("");
    try {
      await adminApi.setTicketStatus(ticketId, status);
      await queryClient.invalidateQueries({ queryKey: ["admin-tickets"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-ticket", ticketId] });
      navigate("/tickets", { state: { success: "Статус обновлён" } });
    } catch (err) {
      setError(apiError(err, "Не удалось обновить статус"));
    }
  }

  return (
    <DetailLayout
      backTo="/tickets"
      title={data ? String(data.subject) : "Обращение"}
      subtitle={data ? `${dash(data.first_name)} ${dash(data.last_name)}` : undefined}
      avatar={data ? initials(data.first_name, data.last_name) : "?"}
      meta={data ? `${dash(data.email)} · ID ${data.id}` : undefined}
      badges={data ? <Badge tone={ticketTone(data.status)}>{labelOf(TICKET_STATUS_LABELS, data.status)}</Badge> : null}
    >
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить обращение") : "")} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <>
          <Section
            title="Статус"
            actions={
              <div className="section-select">
                <Select value={String(data.status)} onChange={(status) => void onStatus(status)} options={TICKET_STATUS_OPTIONS} />
              </div>
            }
          >
            <InfoGrid
              items={[
                ["Пользователь", `${dash(data.first_name)} ${dash(data.last_name)}`],
                ["Email", dash(data.email)],
                ["Публичный ID", dash(data.public_id)],
                ["Создано", formatDateTime(data.created_at)],
              ]}
            />
          </Section>
          <Section title="Сообщение">
            <p className="message-box">{dash(data.message)}</p>
          </Section>
        </>
      ) : null}
    </DetailLayout>
  );
}
