import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface Template {
  id: string;
  name: string;
  subject: string | null;
  category: string | null;
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

export default function TemplatesPage() {
  const [search, setSearch] = useState("");

  const { data: templates = [], isLoading } = useQuery<Template[]>({
    queryKey: ["templates"],
    queryFn: () => api.get("/templates").then((r) => r.data),
  });

  // ⚡ Bolt: Memoize the filtered array and hoist lowerSearch outside the loop
  // This changes the search string allocation from O(N) to O(1) and prevents re-filtering on other state changes
  const filtered = useMemo(() => {
    if (!search) return templates;
    const lowerSearch = search.toLowerCase();
    return templates.filter((t) => (t.name ?? "").toLowerCase().includes(lowerSearch));
  }, [templates, search]);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Шаблоны</span>
          <span style={{ fontSize: "13px", color: G.textMuted }}>{templates.length} шаблонов</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "0 12px", borderRadius: G.radiusSm, height: "34px",
            background: "rgba(255,255,255,0.60)", backdropFilter: "blur(8px)", border: G.border,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск..."
              style={{ border: "none", outline: "none", background: "transparent", fontSize: "13px", color: G.textPrimary, fontFamily: "inherit", width: "140px" }}
            />
          </div>
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
            Новый шаблон
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {isLoading ? (
          <div style={{ color: G.textMuted, fontSize: "13px", padding: "48px 0", textAlign: "center" }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "80px", gap: "10px" }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4 }}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <div style={{ fontSize: "14.5px", fontWeight: 600, color: G.textPrimary }}>Нет шаблонов</div>
            <div style={{ fontSize: "13px", color: G.textMuted }}>Создайте первый шаблон через чат с Лидой</div>
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
                  {["Название", "Тема письма", "Категория"].map((col) => (
                    <th key={col} style={thS}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr
                    key={t.id}
                    style={{ cursor: "pointer", transition: "background 0.1s" }}
                    onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.55)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "transparent"}
                  >
                    <td style={{ ...tdS, fontWeight: 600 }}>{t.name}</td>
                    <td style={{ ...tdS, color: G.textSecondary }}>{t.subject ?? <span style={{ color: G.textMuted }}>—</span>}</td>
                    <td style={tdS}>
                      {t.category ? (
                        <span style={{ padding: "2px 9px", borderRadius: "6px", fontSize: "11.5px", fontWeight: 600, background: G.greenBg, color: G.green, border: "1px solid rgba(45,122,95,0.25)" }}>
                          {t.category}
                        </span>
                      ) : <span style={{ color: G.textMuted }}>—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
