import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { IconBlock, IconBtn, IconCheck, IconUnlock } from "../components/IconBtn";
import { Notice } from "../components/Notice";
import { Badge, BoolBadge, InfoGrid, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { dash, formatDate, formatDateTime, formatMoney, initials, labelOf, personName } from "../lib/format";
import { GENDER_LABELS, ROLE_LABELS, SUB_STATUS_LABELS } from "../lib/options";

export function UserDetailPage() {
  const { id } = useParams();
  const userId = Number(id);
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-user", userId],
    queryFn: () => adminApi.user(userId),
    enabled: Number.isFinite(userId),
  });

  const profile = (data?.trainer_profile ?? null) as Record<string, unknown> | null;
  const subscription = (data?.subscription ?? null) as Record<string, unknown> | null;
  const roles = Array.isArray(data?.roles) ? data.roles.map((item) => String(item)) : [];
  const isTrainer = roles.includes("trainer");
  const fullName = data ? personName(data.first_name, data.last_name) : "Пользователь";

  async function toggleBlock() {
    if (!data) return;
    setError("");
    setSuccess("");
    try {
      const blocked = Boolean(data.is_blocked);
      await adminApi.blockUser(userId, !blocked, blocked ? undefined : "Заблокирован администратором");
      await queryClient.invalidateQueries({ queryKey: ["admin-user", userId] });
      setSuccess(blocked ? "Пользователь разблокирован" : "Пользователь заблокирован");
    } catch (err) {
      setError(apiError(err, "Не удалось изменить статус"));
    }
  }

  async function toggleVerify() {
    setError("");
    setSuccess("");
    try {
      await adminApi.verifyTrainer(userId, !profile?.is_verified);
      await queryClient.invalidateQueries({ queryKey: ["admin-user", userId] });
      setSuccess(profile?.is_verified ? "Верификация снята" : "Тренер верифицирован");
    } catch (err) {
      setError(apiError(err, "Не удалось изменить верификацию"));
    }
  }

  return (
    <DetailLayout
      backTo="/users"
      title={data ? fullName : "Пользователь"}
      subtitle={data ? dash(data.email) : undefined}
      avatar={data ? initials(data.first_name, data.last_name) : "?"}
      meta={data ? `${dash(data.public_id)} · ID ${data.id}` : undefined}
      badges={
        data ? (
          <>
            {roles.map((role) => (
              <Badge key={role} tone={role === "admin" ? "lime" : "blue"}>
                {labelOf(ROLE_LABELS, role)}
              </Badge>
            ))}
            {data.is_blocked ? <Badge tone="red">заблокирован</Badge> : <Badge tone="lime">активен</Badge>}
            {data.is_shadow ? <Badge tone="orange">теневой</Badge> : null}
          </>
        ) : null
      }
      actions={
        data ? (
          <>
            <IconBtn
              tone={data.is_blocked ? "lime" : "red"}
              title={data.is_blocked ? "Разблокировать" : "Заблокировать"}
              onClick={() => void toggleBlock()}
            >
              {data.is_blocked ? <IconUnlock /> : <IconBlock />}
            </IconBtn>
            {isTrainer ? (
              <IconBtn
                tone={profile?.is_verified ? "muted" : "lime"}
                title={profile?.is_verified ? "Снять верификацию" : "Верифицировать"}
                onClick={() => void toggleVerify()}
              >
                <IconCheck />
              </IconBtn>
            ) : null}
          </>
        ) : null
      }
    >
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить пользователя") : "")} success={success} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <>
          <Section title="Контакты">
            <InfoGrid
              items={[
                ["Email", dash(data.email)],
                ["Телефон", dash(data.phone)],
              ]}
            />
          </Section>
          <Section title="Профиль">
            <InfoGrid
              items={[
                ["Пол", labelOf(GENDER_LABELS, data.gender)],
                ["Дата рождения", formatDate(data.birth_date)],
                ["Рост, см", dash(data.height_cm)],
                ["Клиентов", dash(data.clients_count)],
              ]}
            />
          </Section>
          <Section title="Аккаунт">
            <InfoGrid
              items={[
                ["Создан", formatDateTime(data.created_at)],
                ["Последний вход", formatDateTime(data.last_login_at)],
                ["Причина блокировки", dash(data.blocked_reason)],
                ["Активен", <BoolBadge key="active" value={data.is_active} yes="да" no="нет" />],
              ]}
            />
          </Section>
        </>
      ) : null}
      {profile ? (
        <Section title="Профиль тренера">
          <InfoGrid
            items={[
              ["Верификация", profile.is_verified ? <Badge tone="lime">верифицирован</Badge> : <Badge>нет</Badge>],
              ["Категория", dash(profile.category)],
              ["Опыт, лет", dash(profile.experience_years)],
              ["О себе", dash(profile.bio)],
              ["Специализации", dash(Array.isArray(profile.specializations) ? profile.specializations.join(", ") : profile.specializations)],
              ["Форматы", dash(Array.isArray(profile.work_formats) ? profile.work_formats.join(", ") : profile.work_formats)],
              ["Цена сессии", formatMoney(profile.session_price_amount)],
              ["Длительность, мин", dash(profile.session_duration_min)],
              ["Бесплатная консультация", <BoolBadge key="free" value={profile.free_first_consult} />],
              ["Рейтинг", dash(profile.rating_avg)],
              ["Отзывы", dash(profile.reviews_count)],
            ]}
          />
        </Section>
      ) : null}
      {subscription ? (
        <Section title="Подписка">
          <InfoGrid
            items={[
              ["Тариф", dash(subscription.code)],
              ["Аудитория", dash(subscription.audience)],
              ["Статус", labelOf(SUB_STATUS_LABELS, subscription.status)],
              ["Начало", formatDateTime(subscription.starts_at)],
              ["Окончание", formatDateTime(subscription.ends_at)],
              ["Автопродление", <BoolBadge key="renew" value={subscription.auto_renew} />],
            ]}
          />
        </Section>
      ) : null}
    </DetailLayout>
  );
}
