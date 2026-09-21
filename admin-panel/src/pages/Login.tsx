import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { apiError } from "../lib/apiError";
import { Notice } from "../components/Notice";

export function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [loginValue, setLoginValue] = useState("admin@trainhub.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      await signIn(loginValue, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(apiError(err, "Неверный логин или пароль"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <p className="eyebrow">TrainHub</p>
        <h1>Админ-панель</h1>
        <p className="muted">Войдите отдельной учётной записью администратора. Токены тренера и клиента сюда не подходят.</p>
        <label>
          Email или телефон
          <input value={loginValue} onChange={(e) => setLoginValue(e.target.value)} required />
        </label>
        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <Notice error={error} />
        <button type="submit" disabled={pending}>
          {pending ? "Вход..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
