import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const UI = {
  radius: "8px",
  radiusSm: "6px",
  border: "1px solid rgba(0,0,0,0.08)",
  navy: "#1a2540",
  red: "#c0392b",
  textPrimary: "#1a1a1a",
  textMuted: "#999",
  shadowBtn: "0 2px 8px rgba(26,37,64,0.16)",
  shadowCard: "0 2px 12px rgba(0,0,0,0.06)",
};

interface LeadSearchResponse {
  list_id: string;
  list_name: string;
  saved: number;
  log_id: string;
}

export function LeadSearchPanel() {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const listName = [query.trim(), city.trim()].filter(Boolean).join(" · ");
      const { data } = await api.post("/lead-search", {
        query: query.trim(),
        city: city.trim() || null,
        limit: 20,
        list_name: listName || null,
      });
      return data as LeadSearchResponse;
    },
    onSuccess: (data) => {
      setIsError(false);
      setStatus(`Сохранено ${data.saved} лидов в список "${data.list_name}"`);
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
    onError: () => {
      setIsError(true);
      setStatus("Поиск не удался. Проверьте ключи поиска или попробуйте другой запрос.");
    },
  });

  const disabled = !query.trim() || mutation.isPending;

  return (
    <div
      style={{
        margin: "14px 24px 0",
        padding: "14px",
        borderRadius: UI.radius,
        border: UI.border,
        background: "rgba(255,255,255,0.50)",
        boxShadow: UI.shadowCard,
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Кого ищем: стоматологии, студии, клиники"
          style={{
            height: "34px",
            minWidth: "280px",
            flex: "1 1 280px",
            borderRadius: UI.radiusSm,
            border: UI.border,
            background: "rgba(255,255,255,0.65)",
            color: UI.textPrimary,
            fontSize: "13px",
            fontFamily: "inherit",
            outline: "none",
            padding: "0 12px",
          }}
        />
        <input
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Город"
          style={{
            height: "34px",
            width: "150px",
            borderRadius: UI.radiusSm,
            border: UI.border,
            background: "rgba(255,255,255,0.65)",
            color: UI.textPrimary,
            fontSize: "13px",
            fontFamily: "inherit",
            outline: "none",
            padding: "0 12px",
          }}
        />
        <button
          disabled={disabled}
          onClick={() => mutation.mutate()}
          style={{
            height: "34px",
            padding: "0 14px",
            borderRadius: UI.radiusSm,
            border: "none",
            background: disabled ? "rgba(26,37,64,0.10)" : UI.navy,
            color: disabled ? UI.textMuted : "white",
            fontSize: "13px",
            fontWeight: 600,
            fontFamily: "inherit",
            cursor: disabled ? "not-allowed" : "pointer",
            boxShadow: disabled ? "none" : UI.shadowBtn,
          }}
        >
          {mutation.isPending ? "Ищем..." : "Найти лиды"}
        </button>
      </div>
      {status && (
        <div style={{ marginTop: "8px", fontSize: "13px", color: isError ? UI.red : UI.textMuted }}>
          {status}
        </div>
      )}
    </div>
  );
}
