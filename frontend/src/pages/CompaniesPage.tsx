import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface Contact {
  id: string;
  full_name: string | null;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  website: string | null;
  city: string | null;
  industry: string | null;
  enrichment_status: string | null;
  enrichment_summary: string | null;
}

interface Company {
  name: string;
  website: string | null;
  city: string | null;
  industry: string | null;
  source: string | null;
  email: string | null;
  phone: string | null;
  summary: string | null;
  confidence: string;
}

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "2gis":      { bg: "#EEF6FF", text: "#1D6FA4", border: "#BDD8F0" },
  "serpapi":   { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "firecrawl": { bg: "#FFF8F0", text: "#9B4D0F", border: "#FBD38D" },
  "csv":       { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "manual":    { bg: "#F7FAFC", text: "#4A5568", border: "#CBD5E0" },
};

const CONFIDENCE_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
  verified: { label: "Проверено",     color: "#276749", bg: "#F0FFF4", border: "#9AE6B4" },
  inferred: { label: "Предположение", color: "#7B6000", bg: "#FFFFF0", border: "#ECC94B" },
  missing:  { label: "Нет данных",    color: "#718096", bg: "#F7FAFC", border: "#CBD5E0" },
  failed:   { label: "Ошибка",        color: "#C53030", bg: "#FFF5F5", border: "#FEB2B2" },
};

function SourceBadge({ source }: { source: string | null }) {
  const key = (source ?? "manual").toLowerCase();
  const c = SOURCE_COLORS[key] ?? SOURCE_COLORS["manual"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "1px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: c.bg, color: c.text, border: `1px solid ${c.border}`, letterSpacing: "0.01em" }}>
      {source ?? "manual"}
    </span>
  );
}

function ConfidenceBadge({ state }: { state: string }) {
  const m = CONFIDENCE_MAP[state] ?? CONFIDENCE_MAP["missing"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "1px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: m.bg, color: m.color, border: `1px solid ${m.border}` }}>
      <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: m.color, display: "inline-block" }} />
      {m.label}
    </span>
  );
}

function HoverCard({ company }: { company: Company }) {
  return (
    <div style={{
      width: "260px", background: "#FFF",
      border: `1px solid rgba(0,0,0,0.1)`, borderRadius: "8px",
      padding: "14px", boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
      pointerEvents: "none",
    }}>
      <div style={{ fontWeight: 600, fontSize: "13.5px", color: "#111", marginBottom: "4px" }}>{company.name}</div>
      <div style={{ fontSize: "12px", color: "#999", marginBottom: "10px" }}>{[company.city, company.industry].filter(Boolean).join(" · ")}</div>
      {company.summary && (
        <div style={{ fontSize: "12px", color: "#666", lineHeight: "1.5", marginBottom: "10px" }}>{company.summary}</div>
      )}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "10px" }}>
        <SourceBadge source={company.source} />
        <ConfidenceBadge state={company.confidence} />
      </div>
      {company.email && (
        <div style={{ fontSize: "12px", color: SAGE, display: "flex", alignItems: "center", gap: "5px", marginBottom: "3px" }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>
          {company.email}
        </div>
      )}
      {company.phone && (
        <div style={{ fontSize: "12px", color: "#666", display: "flex", alignItems: "center", gap: "5px" }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.18 6.18l1.8-1.8a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" /></svg>
          {company.phone}
        </div>
      )}
    </div>
  );
}

function contactsToCompanies(contacts: Contact[]): Company[] {
  const map = new Map<string, Company>();
  for (const c of contacts) {
    const name = c.company_name?.trim();
    if (!name) continue;
    if (!map.has(name)) {
      map.set(name, {
        name,
        website: c.website ?? null,
        city: c.city ?? null,
        industry: c.industry ?? null,
        source: c.source ?? null,
        email: c.email ?? null,
        phone: c.phone ?? null,
        summary: c.enrichment_summary ?? null,
        confidence: c.enrichment_status === "done" ? "verified" : c.enrichment_status === "failed" ? "failed" : c.email ? "inferred" : "missing",
      });
    }
  }
  return Array.from(map.values());
}

export default function CompaniesPage() {
  const [search, setSearch] = useState("");
  const [hoveredName, setHoveredName] = useState<string | null>(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const tableRef = useRef<HTMLDivElement>(null);

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: () => api.get("/contacts?limit=100").then((r) => r.data),
  });

  const companies = contactsToCompanies(contacts);

  const filtered = search
    ? companies.filter((c) =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        (c.industry ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : companies;

  const hoveredCompany = companies.find((c) => c.name === hoveredName);

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
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Компании</span>
          <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{companies.length} записей</span>
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

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {isLoading ? (
          <div style={{ color: "#AAA", fontSize: "13px", padding: "32px 0", textAlign: "center" }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "64px", gap: "10px" }}>
            <div style={{ fontSize: "14.5px", fontWeight: 500, color: "#333" }}>Нет компаний</div>
            <div style={{ fontSize: "13px", color: "#999" }}>Добавьте контакты с названием компании через чат с Лидой</div>
          </div>
        ) : (
          <div
            ref={tableRef}
            onMouseMove={(e) => { setHoverPos({ x: e.clientX, y: e.clientY }); }}
            style={{ position: "relative", borderRadius: "8px", border: `1px solid ${BORDER}`, overflow: "hidden", background: "#FFF" }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Компания", "Сайт", "Город", "Отрасль", "Email", "Источник", "Статус"].map((col) => (
                    <th key={col} style={headCell}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr
                    key={c.name}
                    onMouseEnter={() => setHoveredName(c.name)}
                    onMouseLeave={() => setHoveredName(null)}
                    onClick={() => setSelectedName(c.name === selectedName ? null : c.name)}
                    style={{
                      cursor: "pointer",
                      background: selectedName === c.name ? `color-mix(in oklch, ${SAGE} 6%, transparent)` :
                        hoveredName === c.name ? "rgba(0,0,0,0.02)" : "transparent",
                      transition: "background 0.1s",
                    }}
                  >
                    <td style={{ ...cell, fontWeight: 500, color: "#111" }}>{c.name}</td>
                    <td style={cell}>{c.website ? <span style={{ color: SAGE }}>{c.website}</span> : <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}>{c.city ?? <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}>{c.industry ?? <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}>{c.email ? <span style={{ color: SAGE }}>{c.email}</span> : <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={cell}><SourceBadge source={c.source} /></td>
                    <td style={cell}><ConfidenceBadge state={c.confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>

            {hoveredName && hoveredCompany && (
              <div style={{
                position: "fixed",
                left: Math.min(hoverPos.x + 16, window.innerWidth - 280),
                top: hoverPos.y + 16 + 220 > window.innerHeight ? hoverPos.y - 220 : hoverPos.y + 16,
                zIndex: 1000,
                pointerEvents: "none",
              }}>
                <HoverCard company={hoveredCompany} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
