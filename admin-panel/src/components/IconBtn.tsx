import type { ReactNode, SVGProps } from "react";
import { Link } from "react-router-dom";

function Svg(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden {...props} />
  );
}

export function IconOpen() {
  return (
    <Svg>
      <path d="M9 5H5v14h14v-4" />
      <path d="M14 5h5v5" />
      <path d="M10 14 19 5" />
    </Svg>
  );
}

export function IconBlock() {
  return (
    <Svg>
      <circle cx="12" cy="12" r="9" />
      <path d="M7 7l10 10" />
    </Svg>
  );
}

export function IconUnlock() {
  return (
    <Svg>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 7.5-2" />
    </Svg>
  );
}

export function IconArchive() {
  return (
    <Svg>
      <rect x="3" y="4" width="18" height="5" rx="1" />
      <path d="M5 9v10h14V9" />
      <path d="M10 13h4" />
    </Svg>
  );
}

export function IconTrash() {
  return (
    <Svg>
      <path d="M4 7h16" />
      <path d="M9 7V5h6v2" />
      <path d="M6 7l1 14h10l1-14" />
    </Svg>
  );
}

export function IconEye() {
  return (
    <Svg>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  );
}

export function IconEyeOff() {
  return (
    <Svg>
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6a3 3 0 0 0 4.2 4.2" />
      <path d="M9.9 5.1A11 11 0 0 1 12 5c6 0 10 7 10 7a18 18 0 0 1-3.2 3.8" />
      <path d="M6.1 6.1A18 18 0 0 0 2 12s4 7 10 7c1.3 0 2.5-.3 3.6-.8" />
    </Svg>
  );
}

export function IconCheck() {
  return (
    <Svg>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5 11 15.5 16 9" />
    </Svg>
  );
}

export function IconPlus() {
  return (
    <Svg>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </Svg>
  );
}

export function IconPencil() {
  return (
    <Svg>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
    </Svg>
  );
}

export function IconBtn({
  to,
  onClick,
  title,
  tone = "lime",
  children,
}: {
  to?: string;
  onClick?: () => void;
  title: string;
  tone?: "lime" | "red" | "muted";
  children: ReactNode;
}) {
  const className = `icon-btn icon-btn-${tone}`;
  if (to) {
    return (
      <Link to={to} className={className} title={title} aria-label={title}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" className={className} title={title} aria-label={title} onClick={onClick}>
      {children}
    </button>
  );
}
