import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Badge, BoolBadge, InfoGrid, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { dash, formatDateTime, formatMoney, initials, labelOf } from "../lib/format";
import { PAY_STATUS_LABELS, PLAN_AUDIENCE_LABELS, SUB_STATUS_LABELS } from "../lib/options";

function payTone(status: unknown) {
  if (status === "paid") return "lime" as const;
  if (status === "failed") return "red" as const;
  if (status === "refunded") return "orange" as const;
  return "muted" as const;
}

function subTone(status: unknown) {
  if (status === "active") return "lime" as const;
  if (status === "expired" || status === "cancelled") return "red" as const;
  return "orange" as const;
}

export function PaymentDetailPage() {
  const { id } = useParams();
  const paymentId = Number(id);
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-payment", paymentId],
    queryFn: () => adminApi.payment(paymentId),
    enabled: Number.isFinite(paymentId),
  });

  return (
    <DetailLayout
      backTo="/payments"
      title={data ? formatMoney(data.amount, String(data.currency ?? "RUB")) : "Платёж"}
      subtitle={data ? `${dash(data.first_name)} ${dash(data.last_name)}` : undefined}
      avatar={data ? initials(data.first_name, data.last_name) : "₽"}
      meta={data ? `${dash(data.email)} · ID ${data.id}` : undefined}
      badges={data ? <Badge tone={payTone(data.status)}>{labelOf(PAY_STATUS_LABELS, data.status)}</Badge> : null}
    >
      <Notice error={error ? apiError(error, "Не удалось загрузить платёж") : ""} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <Section title="Детали платежа">
          <InfoGrid
            items={[
              ["Пользователь", `${dash(data.first_name)} ${dash(data.last_name)}`],
              ["Email", dash(data.email)],
              ["Публичный ID", dash(data.public_id)],
              ["Подписка", dash(data.subscription_id)],
              ["ID провайдера", dash(data.provider_event_id)],
              ["Оплачен", formatDateTime(data.paid_at)],
              ["Создан", formatDateTime(data.created_at)],
            ]}
          />
        </Section>
      ) : null}
    </DetailLayout>
  );
}

export function SubscriptionDetailPage() {
  const { id } = useParams();
  const subscriptionId = Number(id);
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-subscription", subscriptionId],
    queryFn: () => adminApi.subscription(subscriptionId),
    enabled: Number.isFinite(subscriptionId),
  });

  return (
    <DetailLayout
      backTo="/payments"
      backLabel="Назад к платежам"
      title={data ? `Подписка ${dash(data.code)}` : "Подписка"}
      subtitle={data ? `${dash(data.first_name)} ${dash(data.last_name)}` : undefined}
      avatar={data ? initials(data.first_name, data.last_name) : "P"}
      meta={data ? `${dash(data.email)} · ID ${data.id}` : undefined}
      badges={data ? <Badge tone={subTone(data.status)}>{labelOf(SUB_STATUS_LABELS, data.status)}</Badge> : null}
    >
      <Notice error={error ? apiError(error, "Не удалось загрузить подписку") : ""} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <Section title="Условия">
          <InfoGrid
            items={[
              ["Тариф", dash(data.code)],
              ["Цена", formatMoney(data.price_amount, String(data.currency ?? "RUB"))],
              ["Аудитория", labelOf(PLAN_AUDIENCE_LABELS, data.audience)],
              ["Начало", formatDateTime(data.starts_at)],
              ["Окончание", formatDateTime(data.ends_at)],
              ["Автопродление", <BoolBadge key="renew" value={data.auto_renew} />],
              ["Отмена в конце периода", <BoolBadge key="cancel" value={data.cancel_at_period_end} />],
            ]}
          />
        </Section>
      ) : null}
    </DetailLayout>
  );
}
