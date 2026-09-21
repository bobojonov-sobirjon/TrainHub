import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Badge, InfoGrid, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { dash, formatDate, formatDateTime, initials, labelOf, personName } from "../lib/format";
import { CLIENT_STATUS_LABELS, GENDER_LABELS } from "../lib/options";

export function ClientDetailPage() {
  const { id } = useParams();
  const linkId = Number(id);
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-client", linkId],
    queryFn: () => adminApi.client(linkId),
    enabled: Number.isFinite(linkId),
  });
  const notes = Array.isArray(data?.notes) ? (data.notes as Record<string, unknown>[]) : [];
  const limits = Array.isArray(data?.contraindications)
    ? (data.contraindications as Record<string, unknown>[])
    : [];
  const measurement = (data?.last_measurement ?? null) as Record<string, unknown> | null;
  const name = data ? personName(data.client_first, data.client_last) : "Клиент";

  return (
    <DetailLayout
      backTo="/clients"
      title={data ? name : "Клиент"}
      subtitle={data ? dash(data.client_email) : undefined}
      avatar={data ? initials(data.client_first, data.client_last) : "?"}
      meta={data ? `${dash(data.public_id)} · связь ${data.id}` : undefined}
      badges={
        data ? (
          <>
            <Badge tone="lime">{labelOf(CLIENT_STATUS_LABELS, data.status)}</Badge>
            {data.is_shadow ? <Badge tone="orange">теневой</Badge> : null}
          </>
        ) : null
      }
    >
      <Notice error={error ? apiError(error, "Не удалось загрузить клиента") : ""} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <>
          <Section title="Клиент">
            <InfoGrid
              items={[
                ["Email", dash(data.client_email)],
                ["Телефон", dash(data.client_phone)],
                ["Пол", labelOf(GENDER_LABELS, data.gender)],
                ["Дата рождения", formatDate(data.birth_date)],
                ["Рост, см", dash(data.height_cm)],
                ["Формат", dash(data.training_format)],
                ["Цели", dash(Array.isArray(data.goals) ? data.goals.join(", ") : data.goals)],
                ["Как добавлен", dash(data.invited_via)],
              ]}
            />
          </Section>
          <Section title="Тренер">
            <InfoGrid
              items={[
                ["Имя", personName(data.trainer_first, data.trainer_last)],
                ["Email", dash(data.trainer_email)],
                ["Связь создана", formatDateTime(data.created_at)],
              ]}
            />
          </Section>
        </>
      ) : null}
      {measurement ? (
        <Section title="Последние замеры">
          <InfoGrid
            items={[
              ["Дата", formatDateTime(measurement.recorded_at)],
              ["Вес, кг", dash(measurement.weight_kg)],
              ["Жир, %", dash(measurement.body_fat_pct)],
              ["Мышцы, кг", dash(measurement.muscle_mass_kg)],
              ["Вода, %", dash(measurement.water_pct)],
              ["Грудь", dash(measurement.chest_cm)],
              ["Талия", dash(measurement.waist_cm)],
              ["Бёдра", dash(measurement.hips_cm)],
            ]}
          />
        </Section>
      ) : null}
      <Section title="Заметки тренера">
        {notes.length ? (
          <div className="note-list">
            {notes.map((note) => (
              <div key={String(note.id)} className="note-item">
                <p>{dash(note.text)}</p>
                <p className="muted">{formatDateTime(note.created_at)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Заметок нет</p>
        )}
      </Section>
      <Section title="Противопоказания">
        {limits.length ? (
          <div className="note-list">
            {limits.map((item) => (
              <div key={String(item.id)} className="note-item">
                {dash(item.text)}
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Нет противопоказаний</p>
        )}
      </Section>
    </DetailLayout>
  );
}
