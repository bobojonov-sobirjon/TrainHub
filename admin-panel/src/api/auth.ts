import { api } from "./client";
import type { SuccessResponse, TokenPair, UserPublic } from "../types/api";

export async function login(login: string, password: string) {
  const { data } = await api.post<SuccessResponse<TokenPair>>("/auth/login", {
    login,
    password,
  });
  return data.data;
}

export async function logout(refreshToken: string) {
  await api.post("/auth/logout", { refresh_token: refreshToken });
}

export async function getMe() {
  const { data } = await api.get<SuccessResponse<UserPublic>>("/me");
  return data.data;
}
