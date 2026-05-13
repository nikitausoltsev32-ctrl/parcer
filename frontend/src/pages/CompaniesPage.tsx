import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G, SOURCE_BADGE } from "../lib/design";

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
  lead_score: number | null;
  confidence: string | null;
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
  lead_score: number | null;
}

function SourceBadge({ source }: { source: string | null }) {
  const key = source ?? "manual";
  const c = SOURCE_BADGE[key] ?? SOURCE_BADGE["manual"] ?? { bg: "rgba(26,37,64,0.07)", text: "#4a5568", border: "rgba(26,37,64,0.15)" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "1px 7px", borderRadius: "20px",
      fontSize: "11px", fontWeight: 600,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>{source ?? "manual"}</span>
  );
}

function ConfidenceBadge({ state }: { state: string }) {
  const map: Record<string, { label: string; color: string; bg: string; border: string }> = {
    verified: { label: "Verified", color: G.green, bg: G.greenBg, border: "rgba(45,122,95,0.25)" },
    inferred: { label: "Inferred", color: G.amber, bg: G.amberBg, border: "rgba(176,125,42,0.25)" },
    missing:  { label: "Missing",  color: G.textMuted, bg: "rgba(26,37,64,0.06)", border: "rgba(26,37,64,0.12)" },
    failed:   { label: "Failed",   color: G.red,   bg: G.redBg,   border: "rgba(192,57,43,0.25)"  },
  };
  const c = map[state] ?? map["missing"];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "4px",
      padding: "2px 7px", borderRadius: "20px",
      fontSize: "10.5px", fontWeight: 600,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
    }}>
      <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: c.color, display: "inline-block" }} />
      {c.label}
    </span>
  );
}

function HoverCard({ company }: { company: Company }) {
  return (
    <div style={{
      width: "260px",
      background: "rgba(245,248,252,0.95)",
      backdropFilter: G.blurHeavy, WebkitBackdropFilter: G.blurHeavy,
      border: G.border, borderRadius: G.radius,
      padding: "14px", boxShadow: G.shadowModal,
      pointerEvents: "none",
    }}>
      <div style={{ fontWeight: 700, fontSize: "13.5px", color: G.textPrimary, marginBottom: "4px" }}>{company.name}</div>
      <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "10px" }}>{[company.city, company.industry].filter(Boolean).join(" · ")}</div>
      {company.summary && (
        <div style={{ fontSize: "12px", color: G.textSecondary, lineHeight: "1.5", marginBottom: "10px" }}>{company.summary}</div>
      )}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "10px" }}>
        <SourceBadge source={company.source} />
        <ConfidenceBadge state={company.confidence} />
      </div>
      {company.email && (
        <div style={{ fontSize: "12px", color: G.navyLight, display: "flex", alignItems: "center", gap: "5px", marginBottom: "3px" }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          {company.email}
        </div>
      )}
      {company.phone && (
        <div style={{ fontSize: "12px", color: G.textSecondary, display: "flex", alignItems: "center", gap: "5px" }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.18 6.18l1.8-1.8a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
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
        lead_score: c.lead_score ?? null,
      });
    }
  }
  return Array.from(map.values());
}

const thS: React.CSSProperties = {
  padding: "10px 16px", textAlign: "left",
  fontSize: "10.5px", fontWeight: 700, color: G.textMuted,
  textTransform: "uppercase", letterSpacing: "0.07em",
  background: "rgba(255,255,255,0.25)",
  borderBottom: G.borderSubtle, whiteSpace: "nowrap",
};
const tdS: React.CSSProperties = {
  padding: "10px 14px", fontSize: "13px", color: G.textPrimary,
  borderBottom: G.borderSubtle, whiteSpace: "nowrap",
  overflow: "hidden", textOverflow: "ellipsis", maxWidth: "200px",
};

export default function CompaniesPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [hoveredName, setHoveredName] = useState<string | null>(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const tableRef = useRef<HTMLDivElement>(null);

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: () => api.get("/contacts?limit=100").then((r) => r.data),
  });

  const companies = useMemo(() => contactsToCompanies(contacts), [contacts]);
  const filtered = useMemo(() => {
    if (!search) return companies;
    const lowerSearch = search.toLowerCase();
    return companies.filter((c) =>
      c.name.toLowerCase().includes(lowerSearch) ||
      (c.industry ?? "").toLowerCase().includes(lowerSearch)
    );
  }, [companies, search]);

  const hoveredCompany = useMemo(
    () => companies.find((c) => c.name === hoveredName),
    [companies, hoveredName],
  );

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
        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Компании</span>
          <span style={{ fontSize: "13px", color: G.textMuted }}>{companies.length} записей</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "0 12px", borderRadius: G.radiusSm, height: "34px",
            background: "rgba(255,255,255,0.60)", backdropFilter: "blur(8px)",
            border: G.border,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск..."
              style={{ border: "none", outline: "none", background: "transparent", fontSize: "13px", color: G.textPrimary, fontFamily: "inherit", width: "160px" }}
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
            Добавить
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {isLoading ? (
          <div style={{ color: G.textMuted, fontSize: "13px", padding: "48px 0", textAlign: "center" }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "80px", gap: "10px" }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4 }}>
              <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
            </svg>
            <div style={{ fontSize: "14.5px", fontWeight: 600, color: G.textPrimary }}>Нет компаний</div>
            <div style={{ fontSize: "13px", color: G.textMuted }}>Добавьте контакты с названием компании через чат с Лидой</div>
          </div>
        ) : (
          <div
            ref={tableRef}
            onMouseMove={(e) => setHoverPos({ x: e.clientX, y: e.clientY })}
            style={{
              position: "relative", borderRadius: G.radius, border: G.border, overflow: "hidden",
              background: "rgba(255,255,255,0.45)",
              backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
              boxShadow: G.shadowCard,
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Компания", "Сайт", "Город", "Отрасль", "Email", "Score", "Источник", "Статус"].map((col) => (
                    <th key={col} style={thS}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr
                    key={c.name}
                    onMouseEnter={() => setHoveredName(c.name)}
                    onMouseLeave={() => setHoveredName(null)}
                    onClick={() => navigate(`/app/companies/${encodeURIComponent(c.name)}`)}
                    style={{
                      cursor: "pointer",
                      background: hoveredName === c.name ? "rgba(255,255,255,0.55)" : "transparent",
                      transition: "background 0.1s",
                    }}
                  >
                    <td style={{ ...tdS, fontWeight: 600 }}>{c.name}</td>
                    <td style={tdS}>
                      {c.website
                        ? <span style={{ color: G.navyLight }}>{c.website}</span>
                        : <span style={{ color: G.textMuted }}>—</span>}
                    </td>
                    <td style={{ ...tdS, color: G.textSecondary }}>{c.city ?? <span style={{ color: G.textMuted }}>—</span>}</td>
                    <td style={{ ...tdS, color: G.textSecondary }}>{c.industry ?? <span style={{ color: G.textMuted }}>—</span>}</td>
                    <td style={tdS}>
                      {c.email
                        ? <span style={{ color: G.navyLight }}>{c.email}</span>
                        : <span style={{ color: G.textMuted }}>—</span>}
                    </td>
                    <td style={{ ...tdS, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                      {c.lead_score !== null
                        ? <span style={{ color: c.lead_score >= 75 ? G.green : c.lead_score >= 50 ? "#d97706" : G.textMuted }}>{c.lead_score}</span>
                        : <span style={{ color: G.textMuted }}>—</span>}
                    </td>
                    <td style={tdS}><SourceBadge source={c.source} /></td>
                    <td style={tdS}><ConfidenceBadge state={c.confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>

            {hoveredName && hoveredCompany && (
              <div style={{
                position: "fixed",
                left: Math.min(hoverPos.x + 16, window.innerWidth - 280),
                top: hoverPos.y + 16 + 220 > window.innerHeight ? hoverPos.y - 220 : hoverPos.y + 16,
                zIndex: 1000, pointerEvents: "none",
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
