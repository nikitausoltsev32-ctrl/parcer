import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LeadSearchPanel } from "../components/LeadSearchPanel";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface Contact {
  id: string;
  full_name: string;
  company_name: string | null;
  status: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "active":    { bg: "#EBF8FF", text: "#2B6CB0", border: "#90CDF4" },
  "new":       { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "replied":   { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "paused":    { bg: "#FFFFF0", text: "#7B6000", border: "#ECC94B" },
  "rejected":  { bg: "#FFF5F5", text: "#C53030", border: "#FEB2B2" },
};

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "2gis":      { bg: "#EEF6FF", text: "#1D6FA4", border: "#BDD8F0" },
  "serpapi":   { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "csv":       { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "manual":    { bg: "#F7FAFC", text: "#4A5568", border: "#CBD5E0" },
};

function StatusBadge({ status }: { status: string | null }) {
  const key = (status ?? "new").toLowerCase();
  const c = STATUS_COLORS[key] ?? STATUS_COLORS["new"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: "4px", fontSize: "11.5px", fontWeight: 500, background: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
      {status ?? "Новый"}
    </span>
  );
}

function SourceBadge({ source }: { source: string | null }) {
  const key = (source ?? "manual").toLowerCase();
  const c = SOURCE_COLORS[key] ?? SOURCE_COLORS["manual"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "1px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
      {source ?? "manual"}
    </span>
  );
}

export default function ContactsPage() {
  const [search, setSearch] = useState("");

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: () => api.get("/contacts?limit=100").then((r) => r.data),
  });

  const filtered = search
    ? contacts.filter((c) =>
        (c.full_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
        (c.company_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : contacts;

  const cell: React.CSSProperties = {
    padding: "10px 14px", fontSize: "13px", color: "#333",
    borderBottom: "1px solid rgba(0,0,0,0.05)", whiteSpace: "nowrap",
  };
  const headCell: React.CSSProperties = {
    padding: "9px 14px", textAlign: "left",
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
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Контакты</span>
          <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{contacts.length} записей</span>
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
              style={{ border: "none", outline: "none", background: "transparent", fontSize: "13px", color: "#333", fontFamily: "inherit", width: "160px" }}
            />
          </div>
          <button style={{
            padding: "7px 14px", borderRadius: "6px", background: SAGE,
            color: "#FFF", border: "none", fontSize: "13px", fontWeight: 500,
            cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: "6px",
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            Добавить
          </button>
        </div>
      </div>

      <LeadSearchPanel />

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {isLoading ? (
          <div style={{ color: "#AAA", fontSize: "13px", padding: "32px 0", textAlign: "center" }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "64px", gap: "10px" }}>
            <div style={{ fontSize: "14.5px", fontWeight: 500, color: "#333" }}>Нет контактов</div>
            <div style={{ fontSize: "13px", color: "#999" }}>Добавьте контакты вручную или через чат с Лидой</div>
          </div>
        ) : (
          <div style={{ borderRadius: "8px", border: `1px solid ${BORDER}`, overflow: "hidden", background: "#FFF" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Имя", "Компания", "Статус", "Email", "Телефон", "Источник"].map((col) => (
                    <th key={col} style={headCell}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr
                    key={c.id}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.02)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <td style={{ ...cell, fontWeight: 500, color: "#111" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <div style={{
                          width: "26px", height: "26px", borderRadius: "50%",
                          background: "#EEE",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: "11px", fontWeight: 600, color: "#666", flexShrink: 0,
                        }}>
                          {(c.full_name ?? "?").split(" ").map((n) => n[0]).join("").slice(0, 2)}
                        </div>
                        {c.full_name ?? "—"}
                      </div>
                    </td>
                    <td style={cell}>{c.company_name ?? <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}><StatusBadge status={c.status} /></td>
                    <td style={cell}>{c.email ? <span style={{ color: SAGE }}>{c.email}</span> : <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}>{c.phone ?? <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}><SourceBadge source={c.source} /></td>
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
