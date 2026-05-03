import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface Template {
  id: string;
  name: string;
  subject: string | null;
  category: string | null;
}

export default function TemplatesPage() {
  const [search, setSearch] = useState("");

  const { data: templates = [], isLoading } = useQuery<Template[]>({
    queryKey: ["templates"],
    queryFn: () => api.get("/templates").then((r) => r.data),
  });

  const filtered = search
    ? templates.filter((t) => (t.name ?? "").toLowerCase().includes(search.toLowerCase()))
    : templates;

  const cell: React.CSSProperties = {
    padding: "12px 16px", fontSize: "13px", color: "#333",
    borderBottom: "1px solid rgba(0,0,0,0.05)",
  };
  const headCell: React.CSSProperties = {
    padding: "9px 16px", textAlign: "left",
    fontSize: "11px", fontWeight: 600, color: "#AAA",
    textTransform: "uppercase", letterSpacing: "0.06em",
    background: "rgba(0,0,0,0.025)",
    borderBottom: "1px solid rgba(0,0,0,0.07)",
    whiteSpace: "nowrap",
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9", flexShrink: 0,
      }}>
        <div>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Шаблоны</span>
          <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{templates.length} шаблонов</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "0 12px", borderRadius: "6px", height: "32px",
            border: `1px solid rgba(0,0,0,0.1)`, background: "#FAFAF9",
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#BBB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск..."
              style={{ border: "none", outline: "none", background: "transparent", fontSize: "13px", color: "#333", fontFamily: "inherit", width: "140px" }}
            />
          </div>
          <button style={{
            padding: "7px 14px", borderRadius: "6px", background: SAGE,
            color: "#FFF", border: "none", fontSize: "13px", fontWeight: 500,
            cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: "6px",
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            Новый шаблон
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {isLoading ? (
          <div style={{ color: "#AAA", fontSize: "13px", padding: "32px 0", textAlign: "center" }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "64px", gap: "10px" }}>
            <div style={{ fontSize: "14.5px", fontWeight: 500, color: "#333" }}>Нет шаблонов</div>
            <div style={{ fontSize: "13px", color: "#999" }}>Создайте первый шаблон через чат с Лидой</div>
          </div>
        ) : (
          <div style={{ borderRadius: "8px", border: `1px solid ${BORDER}`, overflow: "hidden", background: "#FFF" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Название", "Тема письма", "Категория"].map((col) => (
                    <th key={col} style={headCell}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr
                    key={t.id}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.02)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <td style={{ ...cell, fontWeight: 500, color: "#111" }}>{t.name}</td>
                    <td style={{ ...cell, color: "#666" }}>{t.subject ?? <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}>
                      {t.category ? (
                        <span style={{ padding: "2px 8px", borderRadius: "4px", fontSize: "11.5px", fontWeight: 500, background: "#F0FFF4", color: "#276749", border: "1px solid #9AE6B4" }}>
                          {t.category}
                        </span>
                      ) : <span style={{ color: "#CCC" }}>—</span>}
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
