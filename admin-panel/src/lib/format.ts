const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;
const DATE_TIME = /^\d{4}-\d{2}-\d{2}T/;

export function isDateLike(value: unknown): value is string {
  return typeof value === "string" && (DATE_ONLY.test(value) || DATE_TIME.test(value));
}

export function formatDate(value: unknown): string {
  if (value == null || value === "") return "—";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("ru-RU");
}

export function formatDateTime(value: unknown): string {
  if (value == null || value === "") return "—";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMoney(amount: unknown, currency = "RUB"): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) return "—";
  try {
    return new Intl.NumberFormat("ru-RU", { style: "currency", currency }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}

export function dash(value: unknown): string {
  if (value == null || value === "") return "—";
  return String(value);
}

export function personName(first?: unknown, last?: unknown): string {
  return [first, last].map((part) => String(part ?? "").trim()).filter(Boolean).join(" ") || "Без имени";
}

export function initials(...parts: unknown[]): string {
  const letters = parts
    .map((part) => String(part ?? "").trim())
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return letters || "?";
}

export function formatValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "да" : "нет";
  if (Array.isArray(value)) return value.length ? value.map(String).join(", ") : "—";
  if (typeof value === "string" && DATE_ONLY.test(value)) return formatDate(value);
  if (typeof value === "string" && DATE_TIME.test(value)) return formatDateTime(value);
  return String(value);
}

export function labelOf(map: Record<string, string>, value: unknown): string {
  if (value == null || value === "") return "—";
  return map[String(value)] ?? String(value);
}
