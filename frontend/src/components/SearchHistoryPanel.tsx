import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface SearchLog {
  id: string;
  search_query_original: string;
  city: string | null;
  urls_after_filter: number;
  outcome: string;
  created_at: string;
}

function fmt(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function SearchHistoryPanel() {
  const { data: logs = [] } = useQuery<SearchLog[]>({
    queryKey: ["lead-logs"],
    queryFn: () => api.get("/lead-search/logs?limit=5").then((r) => r.data),
    retry: false,
  });

  if (logs.length === 0) return null;

  return (
    <div style={{
      margin: "10px 24px 0",
      borderRadius: G.radiusSm,
      border: G.border,
      background: "rgba(255,255,255,0.35)",
      flexShrink: 0,
      overflow: "hidden",
    }}>
      <div style={{
        padding: "8px 14px",
        borderBottom: G.borderSubtle,
        fontSize: "10.5px", fontWeight: 700,
        color: G.textMuted, textTransform: "uppercase", letterSpacing: "0.07em",
      }}>
        Последние поиски
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {logs.map((log, i) => (
          <div
            key={log.id}
            style={{
              display: "flex", alignItems: "center", gap: "12px",
              padding: "7px 14px",
              borderBottom: i < logs.length - 1 ? G.borderSubtle : "none",
              fontSize: "12.5px",
            }}
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <span style={{ color: G.textPrimary, fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {log.search_query_original}
              {log.city ? <span style={{ color: G.textMuted, fontWeight: 400 }}> · {log.city}</span> : null}
            </span>
            <span style={{
              fontSize: "11.5px", fontWeight: 600,
              color: log.outcome === "success" ? G.green : G.red,
              flexShrink: 0,
            }}>
              {log.urls_after_filter} лидов
            </span>
            <span style={{ color: G.textMuted, fontSize: "11.5px", flexShrink: 0 }}>{fmt(log.created_at)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
