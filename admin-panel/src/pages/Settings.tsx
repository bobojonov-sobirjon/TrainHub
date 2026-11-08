import { FormEvent, useState } from "react";
import { changePassword } from "../api/auth";
import { apiError } from "../lib/apiError";
import { Notice } from "../components/Notice";
import { useAuth } from "../hooks/useAuth";

export function SettingsPage() {
  const { user } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (newPassword.length < 8) {
      setError("Новый пароль — минимум 8 символов");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Пароли не совпадают");
      return;
    }
    setPending(true);
    try {
      await changePassword(oldPassword, newPassword);
      setSuccess("Пароль обновлён");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(apiError(err, "Не удалось сменить пароль"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <h1>Настройки</h1>
      <p className="muted">
        Аккаунт: {user?.first_name} {user?.last_name} · username <strong>admin</strong>
      </p>
      <form className="card" style={{ maxWidth: 420, display: "grid", gap: 12 }} onSubmit={onSubmit}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Сменить пароль</h2>
        <label>
          Текущий пароль
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <label>
          Новый пароль
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>
        <label>
          Повтор нового пароля
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>
        <Notice error={error} />
        {success ? <p style={{ color: "#0f766e", margin: 0 }}>{success}</p> : null}
        <button type="submit" disabled={pending}>
          {pending ? "Сохранение..." : "Обновить пароль"}
        </button>
      </form>
    </div>
  );
}
