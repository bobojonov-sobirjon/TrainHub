import axios from "axios";

export function apiError(err: unknown, fallback = "Не удалось выполнить действие"): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as
      | { error?: { message?: string }; detail?: string; message?: string }
      | string
      | undefined;
    if (data && typeof data === "object") {
      const message = data.error?.message ?? data.message ?? data.detail;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
    if (!err.response) {
      return "Сервер недоступен. Проверьте backend :8009";
    }
  }
  return fallback;
}
