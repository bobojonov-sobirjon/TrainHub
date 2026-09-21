import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { formatValue } from "../lib/format";
import { Avatar, InfoGrid } from "./Ui";

export { formatValue };

export function FieldList({ items }: { items: Array<[string, unknown]> }) {
  return <InfoGrid items={items.map(([label, value]) => [label, formatValue(value)])} />;
}

export function DetailLayout({
  backTo,
  backLabel = "Назад к списку",
  title,
  subtitle,
  meta,
  badges,
  actions,
  avatar,
  children,
}: {
  backTo: string;
  backLabel?: string;
  title: string;
  subtitle?: ReactNode;
  meta?: ReactNode;
  badges?: ReactNode;
  actions?: ReactNode;
  avatar?: string;
  children: ReactNode;
}) {
  return (
    <div className="detail-page">
      <Link to={backTo} className="back-link">
        ← {backLabel}
      </Link>
      <header className="profile-head card">
        <div className="profile-head-main">
          {avatar ? <Avatar text={avatar} /> : null}
          <div>
            <h1>{title}</h1>
            {subtitle ? <p className="profile-sub">{subtitle}</p> : null}
            {badges ? <div className="badge-row">{badges}</div> : null}
            {meta ? <p className="profile-meta">{meta}</p> : null}
          </div>
        </div>
        {actions ? <div className="profile-actions">{actions}</div> : null}
      </header>
      {children}
    </div>
  );
}
