import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { Notice } from "../components/Notice";
import { apiError } from "../lib/apiError";

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: adminApi.dashboard,
  });

  return (
    <div>
      <h1>Дашборд</h1>
      <p className="muted">Две роли приложения: Coach и Client. Сессии и активные PRO.</p>
      <Notice error={error ? apiError(error, "Не удалось загрузить статистику") : ""} />
      <div className="stat-grid">
        <article className="card">
          <span className="muted">Пользователи</span>
          <strong>{isLoading ? "…" : data?.users ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Coach</span>
          <strong>{isLoading ? "…" : data?.coaches ?? data?.trainers ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Client</span>
          <strong>{isLoading ? "…" : data?.clients ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Coach PRO</span>
          <strong>{isLoading ? "…" : data?.coach_pro ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Client PRO</span>
          <strong>{isLoading ? "…" : data?.client_pro ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Активные тренировки</span>
          <strong>{isLoading ? "…" : data?.active_sessions ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Подписки</span>
          <strong>{isLoading ? "…" : data?.active_subscriptions ?? 0}</strong>
        </article>
      </div>
    </div>
  );
}
