import axios from "axios";

export function apiError(err: unknown, fallback = "Не удалось выполнить действие"): string {
  if (axios.isAxiosError(err)) {
    const message = err.response?.data?.error?.message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
    if (!err.response) {
      return "Сервер недоступен. Проверьте backend :8009";
    }
  }
  return fallback;
}
