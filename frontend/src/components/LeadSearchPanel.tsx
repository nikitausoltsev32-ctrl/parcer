import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LeadSearchProgress, type LeadSearchEvent, type LeadSearchProgressData } from "./LeadSearchProgress";

const UI = {
  radius: "8px",
  radiusSm: "6px",
  border: "1px solid rgba(0,0,0,0.08)",
  navy: "#1a2540",
  red: "#c0392b",
  green: "#2d7a5f",
  textPrimary: "#1a1a1a",
  textMuted: "#999",
  shadowBtn: "0 2px 8px rgba(26,37,64,0.16)",
  shadowCard: "0 2px 12px rgba(0,0,0,0.06)",
};

type SearchStatus = "idle" | "pending" | "success" | "failed" | "partial";

interface ChatModel {
  id: string;
  label: string;
  sub: string;
}

const DEFAULT_MODELS: ChatModel[] = [
  { id: "nvidia/z-ai/glm-5.1", label: "GLM 5.1", sub: "NVIDIA" },
  { id: "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", label: "Nemotron 3 Nano Omni 30B", sub: "NVIDIA reasoning" },
];

export function LeadSearchPanel() {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [models, setModels] = useState<ChatModel[]>(DEFAULT_MODELS);
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_MODELS[0].id);
  const [logId, setLogId] = useState<string | null>(null);
  const [searchStatus, setSearchStatus] = useState<SearchStatus>("idle");
  const [resultMsg, setResultMsg] = useState<string | null>(null);
  const [progress, setProgress] = useState<LeadSearchProgressData | null>(null);
  const [events, setEvents] = useState<LeadSearchEvent[]>([]);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.get<ChatModel[]>("/chat/models")
      .then(({ data }) => {
        if (cancelled || !Array.isArray(data)) return;
        if (data.length === 0) {
          setModels([]);
          setSelectedModelId("");
          return;
        }
        setModels(data);
        setSelectedModelId((current) => data.some((model) => model.id === current) ? current : data[0].id);
      })
      .catch(() => {
        // keep defaults for local dev while backend is starting
      });
    return () => { cancelled = true; };
  }, []);

  const startMutation = useMutation({
    mutationFn: async () => {
      const listName = [query.trim(), city.trim()].filter(Boolean).join(" · ");
      const { data } = await api.post("/lead-search", {
        query: query.trim(),
        city: city.trim() || null,
        limit: 5,
        list_name: listName || null,
        fast_mode: true,
        ai_model: selectedModelId,
      });
      return data as { log_id: string; status: string };
    },
    onSuccess: (data) => {
      setLogId(data.log_id);
      setSearchStatus("pending");
      setResultMsg(null);
      setProgress({
        stage: "queued",
        label: "Поиск поставлен в очередь",
        percent: 1,
        found: 0,
        filtered: 0,
        crawled: 0,
        saved: 0,
        target: 5,
        pages_crawled: 0,
        llm_calls: 0,
        current_domain: null,
      });
      setEvents([]);
    },
    onError: () => {
      setSearchStatus("failed");
      setResultMsg("Поиск не удался. Проверьте ключи или попробуйте другой запрос.");
    },
  });

  useEffect(() => {
    if (searchStatus !== "pending" || !logId) return;

    const poll = async () => {
      try {
        const { data } = await api.get(`/lead-search/${logId}`);
        if (data.progress && typeof data.progress === "object") {
          setProgress(data.progress as LeadSearchProgressData);
        }
        if (Array.isArray(data.events)) {
          setEvents(data.events as LeadSearchEvent[]);
        }
        if (data.status !== "pending") {
          setSearchStatus(data.status as SearchStatus);
          if (data.status === "success" || data.status === "partial") {
            const saved = data.saved ?? 0;
            const name = data.list_name ?? "список";
            setResultMsg(`Готово — ${saved} лидов сохранено в "${name}"`);
          } else {
            setResultMsg(data.failure_reason ?? "Поиск завершился с ошибкой");
          }
          return;
        }
      } catch {
        // ignore poll errors
      }
      pollRef.current = setTimeout(poll, 2500);
    };

    pollRef.current = setTimeout(poll, 2500);
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [searchStatus, logId]);

  const isRunning = startMutation.isPending || searchStatus === "pending";
  const disabled = !query.trim() || !selectedModelId || isRunning;
  const isError = searchStatus === "failed";

  function handleStart() {
    setSearchStatus("idle");
    setResultMsg(null);
    setLogId(null);
    setProgress(null);
    setEvents([]);
    startMutation.mutate();
  }

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
          onKeyDown={(e) => e.key === "Enter" && !disabled && handleStart()}
          placeholder="Кого ищем: стоматологии, студии, клиники"
          style={{
            height: "34px", minWidth: "280px", flex: "1 1 280px",
            borderRadius: UI.radiusSm, border: UI.border,
            background: "rgba(255,255,255,0.65)", color: UI.textPrimary,
            fontSize: "13px", fontFamily: "inherit", outline: "none", padding: "0 12px",
          }}
        />
        <input
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Город"
          style={{
            height: "34px", width: "150px",
            borderRadius: UI.radiusSm, border: UI.border,
            background: "rgba(255,255,255,0.65)", color: UI.textPrimary,
            fontSize: "13px", fontFamily: "inherit", outline: "none", padding: "0 12px",
          }}
        />
        <select
          value={selectedModelId}
          disabled={isRunning || models.length === 0}
          onChange={(e) => setSelectedModelId(e.target.value)}
          title="AI model"
          style={{
            height: "34px", width: "230px",
            borderRadius: UI.radiusSm, border: UI.border,
            background: "rgba(255,255,255,0.65)", color: UI.textPrimary,
            fontSize: "13px", fontFamily: "inherit", outline: "none", padding: "0 10px",
            cursor: isRunning || models.length === 0 ? "not-allowed" : "pointer",
          }}
        >
          {models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label} · {model.sub}
            </option>
          ))}
        </select>
        <button
          disabled={disabled}
          onClick={handleStart}
          style={{
            height: "34px", padding: "0 14px", borderRadius: UI.radiusSm,
            border: "none",
            background: disabled ? "rgba(26,37,64,0.10)" : UI.navy,
            color: disabled ? UI.textMuted : "white",
            fontSize: "13px", fontWeight: 600, fontFamily: "inherit",
            cursor: disabled ? "not-allowed" : "pointer",
            boxShadow: disabled ? "none" : UI.shadowBtn,
          }}
        >
          {isRunning ? "Ищем..." : "Найти лиды"}
        </button>
      </div>
      {(resultMsg || searchStatus === "pending") && (
        <>
          {progress && <div style={{ marginTop: "10px" }}><LeadSearchProgress progress={progress} events={events} /></div>}
          <div style={{ marginTop: "8px", fontSize: "13px", color: isError ? UI.red : searchStatus === "success" || searchStatus === "partial" ? UI.green : UI.textMuted }}>
            {searchStatus === "pending" ? progress?.label || "Идет поиск, результаты появятся в Контактах..." : resultMsg}
          </div>
        </>
      )}
    </div>
  );
}
