import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DataTable } from "../components/DataTable";
import { IconBtn, IconOpen } from "../components/IconBtn";
import { Notice } from "../components/Notice";
import { Badge, EntityCell, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { formatMoney, initials, labelOf } from "../lib/format";
import { PAY_STATUS_LABELS, PERIOD_LABELS, PLAN_AUDIENCE_LABELS, SUB_STATUS_LABELS } from "../lib/options";

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

export function PaymentsPage() {
  const payments = useQuery({
    queryKey: ["admin-payments"],
    queryFn: () => adminApi.payments({ page: 1, page_size: 50 }),
  });
  const subscriptions = useQuery({
    queryKey: ["admin-subscriptions"],
    queryFn: () => adminApi.subscriptions({ page: 1, page_size: 50 }),
  });
  const plans = useQuery({
    queryKey: ["admin-plans"],
    queryFn: adminApi.plans,
  });
  const loadError = payments.error || subscriptions.error || plans.error;

  return (
    <div>
      <div className="page-head">
        <h1>Платежи</h1>
      </div>
      <Notice error={loadError ? apiError(loadError, "Не удалось загрузить платежи") : ""} />
      <Section title="Тарифы">
        <DataTable
          rows={plans.data ?? []}
          columns={[
            {
              key: "code",
              label: "Тариф",
              render: (row) => (
                <EntityCell
                  avatar={initials(row.code)}
                  title={String(row.code ?? "—")}
                  subtitle={labelOf(PLAN_AUDIENCE_LABELS, row.audience)}
                />
              ),
            },
            {
              key: "period",
              label: "Период",
              render: (row) => <Badge tone="blue">{labelOf(PERIOD_LABELS, row.period)}</Badge>,
            },
            {
              key: "price_amount",
              label: "Цена",
              render: (row) => formatMoney(row.price_amount, String(row.currency ?? "RUB")),
            },
            { key: "discount_pct", label: "Скидка %" },
          ]}
        />
      </Section>
      <Section title="Подписки">
        <DataTable
          rows={subscriptions.data?.items ?? []}
          columns={[
            {
              key: "email",
              label: "Пользователь",
              render: (row) => (
                <EntityCell avatar={initials(row.email)} title={String(row.email ?? "—")} subtitle={String(row.code ?? "")} />
              ),
            },
            {
              key: "status",
              label: "Статус",
              render: (row) => <Badge tone={subTone(row.status)}>{labelOf(SUB_STATUS_LABELS, row.status)}</Badge>,
            },
            { key: "ends_at", label: "Действует до" },
            {
              key: "actions",
              label: "",
              render: (row) => (
                <IconBtn to={`/subscriptions/${row.id}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
              ),
            },
          ]}
        />
      </Section>
      <Section title="Платежи">
        <DataTable
          rows={payments.data?.items ?? []}
          columns={[
            {
              key: "email",
              label: "Платёж",
              render: (row) => (
                <EntityCell
                  avatar={initials(row.email)}
                  title={formatMoney(row.amount, String(row.currency ?? "RUB"))}
                  subtitle={String(row.email ?? "—")}
                />
              ),
            },
            {
              key: "status",
              label: "Статус",
              render: (row) => <Badge tone={payTone(row.status)}>{labelOf(PAY_STATUS_LABELS, row.status)}</Badge>,
            },
            { key: "paid_at", label: "Оплачен" },
            {
              key: "actions",
              label: "",
              render: (row) => (
                <IconBtn to={`/payments/${row.id}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
              ),
            },
          ]}
        />
      </Section>
    </div>
  );
}
