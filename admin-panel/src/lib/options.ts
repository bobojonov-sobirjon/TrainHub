import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import type { SelectOption } from "../components/Select";

export const ROLE_OPTIONS: SelectOption[] = [
  { value: "client", label: "Client" },
  { value: "trainer", label: "Coach" },
  { value: "admin", label: "админ" },
];

export const TICKET_STATUS_OPTIONS: SelectOption[] = [
  { value: "open", label: "открыто" },
  { value: "in_progress", label: "в работе" },
  { value: "answered", label: "отвечено" },
  { value: "closed", label: "закрыто" },
];

export const PROGRAM_STATUS_OPTIONS: SelectOption[] = [
  { value: "draft", label: "черновик" },
  { value: "published", label: "опубликована" },
  { value: "archived", label: "архив" },
];

export const FAQ_AUDIENCE_OPTIONS: SelectOption[] = [
  { value: "all", label: "все" },
  { value: "trainer", label: "Coach" },
  { value: "client", label: "Client" },
];

export const LEGAL_OPTIONS: SelectOption[] = [
  { value: "terms", label: "Пользовательское соглашение" },
  { value: "privacy", label: "Политика конфиденциальности" },
];

export const LEGAL_LABELS: Record<string, string> = {
  terms: "Пользовательское соглашение",
  privacy: "Политика конфиденциальности",
};

export const ROLE_LABELS: Record<string, string> = {
  client: "Client",
  trainer: "Coach",
  admin: "админ",
};

export const GENDER_LABELS: Record<string, string> = {
  male: "мужской",
  female: "женский",
  other: "другой",
};

export const SOURCE_LABELS: Record<string, string> = {
  catalog: "каталог",
  trainer: "тренер",
  user_copy: "копия",
};

export const CLIENT_STATUS_LABELS: Record<string, string> = {
  new: "новый",
  permanent: "постоянный",
  paused: "пауза",
  archived: "архив",
};

export const PAY_STATUS_LABELS: Record<string, string> = {
  pending: "ожидает",
  paid: "оплачен",
  refunded: "возврат",
  failed: "ошибка",
};

export const SUB_STATUS_LABELS: Record<string, string> = {
  active: "активна",
  expired: "истекла",
  cancelled: "отменена",
  pending: "ожидает",
};

export const PLAN_AUDIENCE_LABELS: Record<string, string> = {
  pro_client: "PRO клиент",
  pro_trainer: "PRO тренер",
};

export const PERIOD_LABELS: Record<string, string> = {
  month: "месяц",
  year: "год",
};

export const FAQ_AUDIENCE_LABELS: Record<string, string> = {
  all: "все",
  trainer: "Coach",
  client: "Client",
};

export const TICKET_STATUS_LABELS: Record<string, string> = {
  open: "открыто",
  in_progress: "в работе",
  answered: "отвечено",
  closed: "закрыто",
};

export const PROGRAM_STATUS_LABELS: Record<string, string> = {
  draft: "черновик",
  published: "опубликована",
  archived: "архив",
};

export function useDictionaries() {
  return useQuery({
    queryKey: ["admin-dictionaries"],
    queryFn: adminApi.dictionaries,
    staleTime: 5 * 60_000,
  });
}

export function useDictOptions(category: string): SelectOption[] {
  const { data } = useDictionaries();
  return (data?.items ?? [])
    .filter((item) => item.category === category)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((item) => ({ value: item.code, label: item.title_ru }));
}

export function useDictLabel(category: string) {
  const options = useDictOptions(category);
  const map = Object.fromEntries(options.map((item) => [item.value, item.label]));
  return (code: unknown) => map[String(code)] ?? (code == null || code === "" ? "—" : String(code));
}
