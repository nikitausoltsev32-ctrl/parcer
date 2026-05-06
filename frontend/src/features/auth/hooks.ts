import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { clearToken, setToken } from "../../lib/auth";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get("/me").then((r) => r.data),
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (data: { email: string; password: string }) =>
      api.post("/auth/login", data).then((r) => r.data),
    onSuccess: (data) => {
      setToken(data.access_token);
      qc.invalidateQueries({ queryKey: ["me"] });
      navigate("/app");
    },
  });
}

export function useRegister() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (data: { email: string; password: string; full_name?: string; llm_consent: boolean }) =>
      api.post("/auth/register", data).then((r) => r.data),
    onSuccess: () => {
      navigate("/login?registered=1");
    },
  });
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: (token: string) =>
      api.post(`/auth/verify-email?token=${token}`).then((r) => r.data),
  });
}

export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { full_name?: string; business_profile?: { business?: string; offer?: string; city?: string; tone_default?: string } }) =>
      api.patch("/me", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: () => api.post("/auth/logout"),
    onSettled: () => {
      clearToken();
      qc.clear();
      navigate("/login");
    },
  });
}
