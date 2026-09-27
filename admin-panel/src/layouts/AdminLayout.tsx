import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const links = [
  { to: "/", label: "Дашборд" },
  { to: "/coaches", label: "Coach" },
  { to: "/app-clients", label: "Client" },
  { to: "/clients", label: "Связи" },
  { to: "/programs", label: "Программы" },
  { to: "/exercises", label: "Упражнения" },
  { to: "/payments", label: "Платежи" },
  { to: "/faq", label: "FAQ" },
  { to: "/tickets", label: "Обращения" },
  { to: "/legal", label: "Документы" },
];

export function AdminLayout() {
  const { user, signOut } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-dot" />
          TrainHub
        </div>
        <nav>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"}>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <strong>Админ-панель</strong>
          <div className="topbar-right">
            <span>
              {user?.first_name} {user?.last_name}
            </span>
            <button type="button" className="ghost" onClick={() => void signOut()}>
              Выйти
            </button>
          </div>
        </header>
        <section className="content">
          <Outlet />
        </section>
      </div>
    </div>
  );
}
