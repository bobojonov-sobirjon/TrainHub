import { api } from "./client";
import type { DashboardStats, DictionariesData, Page, SuccessResponse } from "../types/api";

type Query = Record<string, string | number | undefined>;

function params(query: Query = {}) {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => value !== undefined && value !== ""),
  );
}

async function getData<T>(url: string, query?: Query) {
  const { data } = await api.get<SuccessResponse<T>>(url, { params: params(query) });
  return data.data;
}

export const adminApi = {
  dashboard: () => getData<DashboardStats>("/dashboard"),
  dictionaries: () => getData<DictionariesData>("/dictionaries"),
  users: (query: Query) => getData<Page<Record<string, unknown>>>("/users", query),
  coaches: (query: Query) => getData<Page<Record<string, unknown>>>("/coaches", query),
  appClients: (query: Query) => getData<Page<Record<string, unknown>>>("/app-clients", query),
  user: (id: number) => getData<Record<string, unknown>>(`/users/${id}`),
  blockUser: (id: number, is_blocked: boolean, reason?: string) =>
    api.post(`/users/${id}/block`, { is_blocked, reason }),
  verifyTrainer: (id: number, is_verified: boolean) =>
    api.post(`/users/${id}/verify`, { is_verified }),
  clients: (query: Query) => getData<Page<Record<string, unknown>>>("/clients", query),
  client: (id: number) => getData<Record<string, unknown>>(`/clients/${id}`),
  programs: (query: Query) => getData<Page<Record<string, unknown>>>("/programs", query),
  program: (id: number) => getData<Record<string, unknown>>(`/programs/${id}`),
  createProgram: (payload: Record<string, unknown>) =>
    api.post("/programs", payload),
  updateProgram: (id: number, payload: Record<string, unknown>) =>
    api.patch(`/programs/${id}`, payload),
  uploadProgramCover: (id: number, file?: File, clear = false) => {
    const form = new FormData();
    form.append("clear", clear ? "true" : "false");
    if (file) form.append("file", file);
    return api.post(`/programs/${id}/cover`, form);
  },
  archiveProgram: (id: number) => api.delete(`/programs/${id}`),
  createProgramDay: (programId: number, payload: Record<string, unknown>) =>
    api.post(`/programs/${programId}/days`, payload),
  updateProgramDay: (programId: number, dayId: number, payload: Record<string, unknown>) =>
    api.patch(`/programs/${programId}/days/${dayId}`, payload),
  deleteProgramDay: (programId: number, dayId: number) =>
    api.delete(`/programs/${programId}/days/${dayId}`),
  addProgramDayExercise: (programId: number, dayId: number, payload: Record<string, unknown>) =>
    api.post(`/programs/${programId}/days/${dayId}/exercises`, payload),
  updateProgramDayExercise: (programId: number, dayId: number, itemId: number, payload: Record<string, unknown>) =>
    api.patch(`/programs/${programId}/days/${dayId}/exercises/${itemId}`, payload),
  deleteProgramDayExercise: (programId: number, dayId: number, itemId: number) =>
    api.delete(`/programs/${programId}/days/${dayId}/exercises/${itemId}`),
  exercises: (query: Query) => getData<Record<string, unknown>[]>("/exercises", query),
  exercise: (id: number) => getData<Record<string, unknown>>(`/exercises/${id}`),
  createExercise: (form: FormData) => api.post("/exercises", form),
  updateExercise: (id: number, form: FormData) => api.patch(`/exercises/${id}`, form),
  deleteExercise: (id: number) => api.delete(`/exercises/${id}`),
  payments: (query: Query) => getData<Page<Record<string, unknown>>>("/payments", query),
  payment: (id: number) => getData<Record<string, unknown>>(`/payments/${id}`),
  subscriptions: (query: Query) => getData<Page<Record<string, unknown>>>("/subscriptions", query),
  subscription: (id: number) => getData<Record<string, unknown>>(`/subscriptions/${id}`),
  plans: () => getData<Record<string, unknown>[]>("/plans"),
  faq: () => getData<Record<string, unknown>[]>("/faq"),
  faqItem: (id: number) => getData<Record<string, unknown>>(`/faq/${id}`),
  createFaq: (payload: Record<string, unknown>) => api.post("/faq", payload),
  updateFaq: (id: number, payload: Record<string, unknown>) => api.patch(`/faq/${id}`, payload),
  publishFaq: (id: number, is_published: boolean) =>
    api.post(`/faq/${id}/publish`, { is_published }),
  tickets: () => getData<Record<string, unknown>[]>("/tickets"),
  ticket: (id: number) => getData<Record<string, unknown>>(`/tickets/${id}`),
  setTicketStatus: (id: number, status: string) => api.patch(`/tickets/${id}`, { status }),
  legal: (docType: string) => getData<Record<string, unknown>>(`/legal/${docType}`),
  updateLegal: (docType: string, payload: { body_md: string; version: string }) =>
    api.patch(`/legal/${docType}`, payload),
  uploadLegalFile: (docType: string, version: string, file?: File) => {
    const form = new FormData();
    form.append("version", version);
    if (file) {
      form.append("file", file);
    }
    return api.post(`/legal/${docType}/file`, form);
  },
};
