import { ReactNode, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

export function Modal({
  open,
  title,
  subtitle,
  className,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  subtitle?: string;
  className?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onCloseRef.current();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!open) return null;

  const cardClass = ["modal-card", className].filter(Boolean).join(" ");

  return createPortal(
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={cardClass} role="dialog" aria-modal="true" aria-label={title}>
        <header className="modal-head">
          <div className="modal-head-copy">
            <h2>{title}</h2>
            {subtitle ? <p className="modal-subtitle">{subtitle}</p> : null}
          </div>
          <button type="button" className="ghost modal-close" onClick={onClose} aria-label="Закрыть">
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden>
              <path
                d="M7 7l10 10M17 7 7 17"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </header>
        {children}
      </div>
    </div>,
    document.body,
  );
}
