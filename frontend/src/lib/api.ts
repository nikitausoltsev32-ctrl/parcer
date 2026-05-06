import axios from "axios";
import { clearToken, getToken, setToken } from "./auth";

export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const url: string = err.config?.url ?? "";
    if (url.includes("/auth/refresh")) {
      return Promise.reject(err);
    }
    if (err.response?.status === 401 && !err.config._retry) {
      err.config._retry = true;
      try {
        refreshPromise ??= axios
          .post("/api/v1/auth/refresh", {}, { withCredentials: true })
          .then((r) => r.data.access_token)
          .finally(() => { refreshPromise = null; });
        const token = await refreshPromise;
        setToken(token);
        err.config.headers.Authorization = `Bearer ${token}`;
        return api.request(err.config);
      } catch {
        clearToken();
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);
