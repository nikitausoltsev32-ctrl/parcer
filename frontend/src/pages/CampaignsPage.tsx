import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface Campaign {
  id: string;
  name: string;
  status: string;
  stats: Record<string, number> | null;
  created_at: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  generating: "Генерация",
  generated: "Готова",
  sending: "Отправка",
  sent: "Отправлена",
  paused: "Пауза",
};

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  draft:      { bg: "rgba(26,37,64,0.06)",  text: G.textMuted,  border: "rgba(26,37,64,0.12)" },
  generating: { bg: G.amberBg,              text: G.amber,      border: "rgba(176,125,42,0.25)" },
  generated:  { bg: G.blueBg,               text: G.blue,       border: "rgba(43,108,176,0.25)" },
  sending:    { bg: "rgba(192,84,43,0.10)",  text: "#c0542b",    border: "rgba(192,84,43,0.25)" },
  sent:       { bg: G.greenBg,              text: G.green,      border: "rgba(45,122,95,0.25)" },
  paused:     { bg: "rgba(26,37,64,0.06)",  text: G.textMuted,  border: "rgba(26,37,64,0.12)" },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

const thS: React.CSSProperties = {
  padding: "10px 16px", textAlign: "left",
  fontSize: "10.5px", fontWeight: 700, color: G.textMuted,
  textTransform: "uppercase", letterSpacing: "0.07em",
  background: "rgba(255,255,255,0.25)",
  borderBottom: G.borderSubtle, whiteSpace: "nowrap",
};
const tdS: React.CSSProperties = {
  padding: "12px 16px", fontSize: "13px",
  color: G.textPrimary, borderBottom: G.borderSubtle,
};
const mono: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace", fontSize: "12.5px",
};

export default function CampaignsPage() {
  const navigate = useNavigate();
  const { data: campaigns = [], isLoading } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: () => api.get("/campaigns").then((r) => r.data),
  });

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Кампании</span>
        <button style={{
          display: "flex", alignItems: "center", gap: "6px",
          padding: "0 14px", height: "34px", borderRadius: G.radiusSm,
          background: G.navy, color: "white",
          border: "none", fontSize: "13px", fontWeight: 600,
          cursor: "pointer", fontFamily: "inherit", boxShadow: G.shadowBtn,
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Новая кампания
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {isLoading ? (
          <div style={{ color: G.textMuted, fontSize: "13px", padding: "48px 0", textAlign: "center" }}>Загрузка…</div>
        ) : campaigns.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "80px", gap: "10px" }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4 }}>
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <div style={{ fontSize: "14.5px", fontWeight: 600, color: G.textPrimary }}>Нет кампаний</div>
            <div style={{ fontSize: "13px", color: G.textMuted }}>Создайте первую кампанию через чат с Лидой</div>
          </div>
        ) : (
          <div style={{
            borderRadius: G.radius, border: G.border, overflow: "hidden",
            background: "rgba(255,255,255,0.45)",
            backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
            boxShadow: G.shadowCard,
          }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Кампания", "Статус", "Сгенерировано", "Отправлено", "Ошибок", "Создана"].map((col) => (
                    <th key={col} style={thS}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => {
                  const stats = c.stats ?? {};
                  const generated = stats.generated ?? 0;
                  const sent = stats.sent ?? 0;
                  const failed = stats.failed ?? 0;
                  const cs = STATUS_COLORS[c.status] ?? STATUS_COLORS.draft;
                  return (
                    <tr
                      key={c.id}
                      onClick={() => navigate(`/app/campaigns/${c.id}`)}
                      style={{ cursor: "pointer", transition: "background 0.1s" }}
                      onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.55)"}
                      onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "transparent"}
                    >
                      <td style={{ ...tdS, fontWeight: 600 }}>{c.name || "—"}</td>
                      <td style={tdS}>
                        <span style={{
                          padding: "2px 9px", borderRadius: "6px",
                          fontSize: "11.5px", fontWeight: 500,
                          background: cs.bg, color: cs.text, border: `1px solid ${cs.border}`,
                        }}>
                          {STATUS_LABELS[c.status] ?? c.status}
                        </span>
                      </td>
                      <td style={{ ...tdS, ...mono }}>{generated > 0 ? generated : <span style={{ color: G.textMuted }}>—</span>}</td>
                      <td style={{ ...tdS, ...mono }}>
                        {sent > 0 ? (
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            {sent}
                            {generated > 0 && (
                              <div style={{ width: "60px", height: "4px", borderRadius: "2px", background: "rgba(26,37,64,0.10)", overflow: "hidden" }}>
                                <div style={{ width: `${(sent / generated) * 100}%`, height: "100%", background: G.navy, borderRadius: "2px" }} />
                              </div>
                            )}
                          </div>
                        ) : <span style={{ color: G.textMuted }}>—</span>}
                      </td>
                      <td style={{ ...tdS, ...mono }}>
                        {failed > 0
                          ? <span style={{ color: G.red }}>{failed}</span>
                          : <span style={{ color: G.textMuted }}>—</span>}
                      </td>
                      <td style={{ ...tdS, color: G.textMuted, fontSize: "12px" }}>{formatDate(c.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
