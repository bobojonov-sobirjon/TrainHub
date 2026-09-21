import { CSSProperties, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type SelectOption = {
  value: string;
  label: string;
};

export function Select({
  value,
  onChange,
  options,
  placeholder = "Выберите",
  allowEmpty = false,
  emptyLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  allowEmpty?: boolean;
  emptyLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const selected = options.find((option) => option.value === value);
  const label = selected?.label ?? (allowEmpty ? emptyLabel ?? placeholder : placeholder);
  const items = allowEmpty
    ? [{ value: "", label: emptyLabel ?? placeholder }, ...options]
    : options;

  function placeMenu() {
    const trigger = rootRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const width = Math.max(rect.width, 180);
    const maxHeight = 260;
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const openUp = spaceBelow < Math.min(maxHeight, 160) && rect.top > spaceBelow;
    const left = Math.min(Math.max(8, rect.left), window.innerWidth - width - 8);
    const top = openUp ? undefined : rect.bottom + 8;
    const bottom = openUp ? window.innerHeight - rect.top + 8 : undefined;
    setMenuStyle({
      position: "fixed",
      top,
      bottom,
      left,
      width,
      maxHeight,
      zIndex: 120,
    });
  }

  useLayoutEffect(() => {
    if (!open) return;
    placeMenu();
    const onReposition = () => placeMenu();
    window.addEventListener("resize", onReposition);
    window.addEventListener("scroll", onReposition, true);
    return () => {
      window.removeEventListener("resize", onReposition);
      window.removeEventListener("scroll", onReposition, true);
    };
  }, [open, options.length]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target) && !menuRef.current?.contains(target)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  function pick(next: string) {
    onChange(next);
    setOpen(false);
  }

  return (
    <div className={`ui-select${open ? " is-open" : ""}`} ref={rootRef}>
      <button
        type="button"
        className="ui-select-trigger"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((current) => !current)}
      >
        <span className={selected || (allowEmpty && value === "") ? "" : "muted"}>{label}</span>
        <svg className="ui-select-caret" viewBox="0 0 16 16" width="16" height="16" aria-hidden>
          <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open
        ? createPortal(
            <ul className="ui-select-menu" ref={menuRef} style={menuStyle} role="listbox">
              {items.map((option) => {
                const active = option.value === value;
                return (
                  <li key={option.value || "empty"}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={active}
                      className={active ? "is-active" : ""}
                      onClick={() => pick(option.value)}
                    >
                      <span>{option.label}</span>
                      {active ? (
                        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden>
                          <path
                            d="M3.5 8.5l3 3 6-6"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ul>,
            document.body,
          )
        : null}
    </div>
  );
}
