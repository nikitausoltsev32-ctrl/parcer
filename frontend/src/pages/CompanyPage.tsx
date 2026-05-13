import { useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
  enrichment_summary: string | null;
  lead_score: number | null;
}

const thS: React.CSSProperties = {
  padding: "10px 16px", textAlign: "left",
  fontSize: "10.5px", fontWeight: 700, color: G.textMuted,
  textTransform: "uppercase", letterSpacing: "0.07em",
  background: "rgba(255,255,255,0.25)",
  borderBottom: G.borderSubtle, whiteSpace: "nowrap",
};
const tdS: React.CSSProperties = {
  padding: "10px 16px", fontSize: "13px", color: G.textPrimary,
  borderBottom: G.borderSubtle, whiteSpace: "nowrap",
  overflow: "hidden", textOverflow: "ellipsis", maxWidth: "200px",
};

export default function CompanyPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const decodedName = name ? decodeURIComponent(name) : "";

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: () => api.get("/contacts?limit=500").then((r) => r.data),
  });

  const companyContacts = useMemo(
    () => contacts.filter((c) => c.company_name?.trim() === decodedName),
    [contacts, decodedName],
  );

  const summary = useMemo(() => {
    const first = companyContacts[0];
    return {
      website: first?.website ?? null,
      city: first?.city ?? null,
      industry: first?.industry ?? null,
      source: first?.source ?? null,
      description: first?.enrichment_summary ?? null,
    };
  }, [companyContacts]);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", gap: "10px",
        padding: "0 24px",
        background: G.glassHeader, backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <button
          onClick={() => navigate("/app/companies")}
          style={{ display: "flex", alignItems: "center", gap: "4px", background: "none", border: "none", cursor: "pointer", color: G.textMuted, fontSize: "13px", fontFamily: "inherit", padding: 0 }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          Компании
        </button>
        <span style={{ color: G.textMuted }}>/</span>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>{decodedName}</span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        {isLoading ? (
          <div style={{ color: G.textMuted, fontSize: "13px", textAlign: "center", paddingTop: "48px" }}>Загрузка…</div>
        ) : (
          <div style={{ maxWidth: "720px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* Company info */}
            <div style={{ borderRadius: G.radius, border: G.border, background: G.glassCard, backdropFilter: G.blur, WebkitBackdropFilter: G.blur, boxShadow: G.shadowCard, padding: "20px 24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "16px" }}>
                <div style={{
                  width: "44px", height: "44px", borderRadius: G.radiusSm, background: G.navyXLight, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: G.border,
                }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={G.navy} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
                  </svg>
                </div>
                <div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: G.textPrimary }}>{decodedName}</div>
                  <div style={{ fontSize: "13px", color: G.textMuted, marginTop: "2px" }}>
                    {[summary.city, summary.industry].filter(Boolean).join(" · ") || "—"}
                  </div>
                </div>
                {summary.source && (
                  <div style={{ marginLeft: "auto" }}>
                    <span style={{
                      display: "inline-flex", alignItems: "center",
                      padding: "1px 7px", borderRadius: "20px",
                      fontSize: "11px", fontWeight: 600,
                      background: (SOURCE_BADGE[summary.source] ?? SOURCE_BADGE["manual"]).bg,
                      color: (SOURCE_BADGE[summary.source] ?? SOURCE_BADGE["manual"]).text,
                      border: `1px solid ${(SOURCE_BADGE[summary.source] ?? SOURCE_BADGE["manual"]).border}`,
                    }}>{summary.source}</span>
                  </div>
                )}
              </div>
              {summary.website && (
                <div style={{ fontSize: "13px", color: G.navyLight, marginBottom: "10px" }}>
                  <a href={summary.website} target="_blank" rel="noreferrer" style={{ color: G.navyLight }}>{summary.website}</a>
                </div>
              )}
              {summary.description && (
                <div style={{ fontSize: "13px", color: G.textSecondary, lineHeight: "1.6" }}>{summary.description}</div>
              )}
            </div>

            {/* Contacts table */}
            <div style={{ borderRadius: G.radius, border: G.border, background: G.glassCard, backdropFilter: G.blur, WebkitBackdropFilter: G.blur, boxShadow: G.shadowCard, overflow: "hidden" }}>
              <div style={{ padding: "14px 20px 10px", borderBottom: G.borderSubtle, fontSize: "13px", fontWeight: 700, color: G.textPrimary }}>
                Контакты ({companyContacts.length})
              </div>
              {companyContacts.length === 0 ? (
                <div style={{ padding: "32px", textAlign: "center", color: G.textMuted, fontSize: "13px" }}>Нет контактов</div>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {["Имя", "Email", "Телефон", "Score"].map((col) => (
                        <th key={col} style={thS}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {companyContacts.map((c) => (
                      <tr
                        key={c.id}
                        onClick={() => navigate(`/app/contacts/${c.id}`)}
                        style={{ cursor: "pointer", transition: "background 0.1s" }}
                        onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.55)"}
                        onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "transparent"}
                      >
                        <td style={{ ...tdS, fontWeight: 600 }}>{c.full_name ?? "—"}</td>
                        <td style={tdS}>
                          {c.email ? <span style={{ color: G.navyLight }}>{c.email}</span> : <span style={{ color: G.textMuted }}>—</span>}
                        </td>
                        <td style={{ ...tdS, color: G.textSecondary }}>{c.phone ?? <span style={{ color: G.textMuted }}>—</span>}</td>
                        <td style={tdS}>
                          {c.lead_score != null ? (
                            <span style={{
                              padding: "2px 8px", borderRadius: G.radiusXs, fontSize: "11.5px", fontWeight: 700,
                              background: c.lead_score >= 70 ? G.greenBg : c.lead_score >= 40 ? G.amberBg : G.redBg,
                              color: c.lead_score >= 70 ? G.green : c.lead_score >= 40 ? G.amber : G.red,
                            }}>{c.lead_score}</span>
                          ) : <span style={{ color: G.textMuted }}>—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
