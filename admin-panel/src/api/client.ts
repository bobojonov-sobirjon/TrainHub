import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8009";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1/admin`,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("th_access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data instanceof FormData) {
    if (typeof config.headers.delete === "function") {
      config.headers.delete("Content-Type");
    } else {
      delete config.headers["Content-Type"];
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isAuthRoute = String(original?.url ?? "").includes("/auth/");
    if (error.response?.status === 401 && !original._retry && !isAuthRoute) {
      original._retry = true;
      const refresh = sessionStorage.getItem("th_refresh");
      if (!refresh) {
        sessionStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }
      try {
        const { data } = await axios.post(`${API_URL}/api/v1/admin/auth/refresh`, {
          refresh_token: refresh,
        });
        sessionStorage.setItem("th_access", data.data.access_token);
        sessionStorage.setItem("th_refresh", data.data.refresh_token);
        original.headers.Authorization = `Bearer ${data.data.access_token}`;
        return api(original);
      } catch {
        sessionStorage.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);
