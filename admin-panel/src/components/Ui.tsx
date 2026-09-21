import type { ReactNode } from "react";

export function Badge({
  tone = "muted",
  children,
}: {
  tone?: "lime" | "red" | "muted" | "orange" | "blue";
  children: ReactNode;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Avatar({ text }: { text: string }) {
  return <div className="avatar">{text}</div>;
}

export function Section({
  title,
  actions,
  children,
}: {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="card section-card">
      <header className="section-head">
        <h2>{title}</h2>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}

export function InfoGrid({ items }: { items: Array<[string, ReactNode]> }) {
  return (
    <div className="info-grid">
      {items.map(([label, value]) => (
        <div key={label} className="info-tile">
          <span className="info-label">{label}</span>
          <strong className="info-value">{value == null || value === "" ? "—" : value}</strong>
        </div>
      ))}
    </div>
  );
}

export function BoolBadge({ value, yes = "да", no = "нет" }: { value: unknown; yes?: string; no?: string }) {
  return value ? <Badge tone="lime">{yes}</Badge> : <Badge>{no}</Badge>;
}

export function EntityCell({
  title,
  subtitle,
  avatar,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  avatar?: string;
}) {
  return (
    <div className="entity-cell">
      {avatar ? <div className="entity-cell-mini">{avatar}</div> : null}
      <div className="entity-cell-copy">
        <strong>{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
    </div>
  );
}
