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
      <p className="muted">Пользователи, сессии и активные PRO-подписки.</p>
      <Notice error={error ? apiError(error, "Не удалось загрузить статистику") : ""} />
      <div className="stat-grid">
        <article className="card">
          <span className="muted">Пользователи</span>
          <strong>{isLoading ? "…" : data?.users ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Тренеры</span>
          <strong>{isLoading ? "…" : data?.trainers ?? 0}</strong>
        </article>
        <article className="card">
          <span className="muted">Клиенты</span>
          <strong>{isLoading ? "…" : data?.clients ?? 0}</strong>
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
