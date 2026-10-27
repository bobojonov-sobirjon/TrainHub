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

export const PROGRAM_STATUS_FILTER_OPTIONS: SelectOption[] = [
  { value: "", label: "все статусы" },
  ...PROGRAM_STATUS_OPTIONS,
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
  // legacy (moderation removed)
  pending_review: "черновик",
  rejected: "черновик",
};

export function useDictionaries() {
  return useQuery({
    queryKey: ["admin-dictionaries"],
    queryFn: adminApi.dictionaries,
    staleTime: 5 * 60_000,
  });
}

/** Fallback RU titles when API dict is stale or seed used extra codes. */
const DICT_FALLBACKS: Record<string, Record<string, string>> = {
  muscle_group: {
    neck: "Шея",
    shoulders: "Плечи",
    chest: "Грудь",
    back: "Спина",
    waist: "Талия",
    glutes: "Ягодицы",
    thighs: "Бёдра",
    calves: "Икры",
    biceps: "Бицепс",
    triceps: "Трицепс",
    forearms: "Предплечья",
    arms: "Руки",
    legs: "Ноги",
    traps: "Трапеции",
    abs: "Пресс",
    press: "Пресс",
    full_body: "Всё тело",
    other: "Другое",
  },
  equipment: {
    none: "Нет",
    bodyweight: "Свой вес",
    dumbbells: "Гантели",
    dumbbell: "Гантель",
    barbell: "Штанга",
    kettlebell: "Гиря",
    plate: "Диск",
    bench: "Скамья для жима",
    cable: "Блок",
    machine: "Тренажёр",
    gym: "Тренажёрный зал",
    other: "Другое",
  },
  workout_kind: {
    strength: "Силовая",
    functional: "Функциональный",
    cardio: "Кардио",
    stretching: "Растяжка",
    circuit: "Круговая",
    interval: "Интервальная",
    rehab: "Реабилитация",
    endurance: "Выносливость",
  },
};

export function useDictOptions(category: string): SelectOption[] {
  const { data } = useDictionaries();
  const fromApi = (data?.items ?? [])
    .filter((item) => item.category === category)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((item) => ({ value: item.code, label: item.title_ru }));
  const seen = new Set(fromApi.map((item) => item.value));
  const fallback = DICT_FALLBACKS[category] ?? {};
  const extras = Object.entries(fallback)
    .filter(([code]) => !seen.has(code))
    .map(([value, label]) => ({ value, label }));
  return [...fromApi, ...extras];
}

export function useDictLabel(category: string) {
  const options = useDictOptions(category);
  const map = Object.fromEntries(options.map((item) => [item.value, item.label]));
  const fallback = DICT_FALLBACKS[category] ?? {};
  return (code: unknown) => {
    if (code == null || code === "") return "—";
    const key = String(code);
    return map[key] ?? fallback[key] ?? key;
  };
}
