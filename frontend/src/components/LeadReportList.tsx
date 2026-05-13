import { useState, useEffect, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { G, SOURCE_BADGE } from "../lib/design";

export interface LeadReportItem {
  id?: string | number;
  domain?: string | null;
  website?: string | null;
  name?: string | null;
  company_name?: string | null;
  summary?: string | null;
  website_summary?: string | null;
  description?: string | null;
  city?: string | null;
  address?: string | null;
  industry?: string | null;
  source?: string | null;
  email?: string | null;
  phone?: string | null;
  telegram?: string | null;
  whatsapp?: string | null;
  vk?: string | null;
  confidence?: string | number | null;
  ai_level?: string | null;
  score?: number | null;
  url_label?: string | null;
  reason_to_contact?: string | null;
  pain_points?: string[] | null;
  website_quality?: {
    comments?: string | null;
    has_clear_cta?: boolean | null;
    has_online_booking?: boolean | null;
    has_modern_design?: boolean | null;
    has_mobile_adaptation?: boolean | null;
    seo_visible?: boolean | null;
  } | null;
  lead_fit?: {
    score?: number | null;
    reason?: string | null;
    priority?: string | null;
  } | null;
  processing?: {
    ai_level?: string | null;
    confidence?: string | number | null;
    source?: string | null;
    sources?: string[] | null;
  } | null;
  maps_rating?: number | null;
  maps_reviews_count?: number | null;
  serp_position?: number | null;
}

interface LeadReportListProps {
  leads: LeadReportItem[];
  title?: string;
  compact?: boolean;
}

// ── Helpers ───────────────────────────────────────────────────

function clean(value: string | null | undefined): string | null {
  const v = value?.trim();
  return v || null;
}

function companyName(lead: LeadReportItem): string {
  return clean(lead.company_name) || clean(lead.name) || clean(lead.domain) || clean(lead.website) || "Без названия";
}

function leadDescription(lead: LeadReportItem): string | null {
  return clean(lead.description) || clean(lead.summary) || clean(lead.website_summary);
}

function leadReason(lead: LeadReportItem): string | null {
  const aiLevel = clean(lead.ai_level) || clean(lead.processing?.ai_level);
  const deepReason = aiLevel === "deep" ? clean(lead.lead_fit?.reason) : null;
  return clean(lead.reason_to_contact) || deepReason || clean(lead.website_quality?.comments);
}

function leadScore(lead: LeadReportItem): number | null {
  if (typeof lead.score === "number") return lead.score;
  if (typeof lead.lead_fit?.score === "number") return lead.lead_fit.score;
  return null;
}

function sourceLabel(lead: LeadReportItem): string {
  return clean(lead.source) || clean(lead.processing?.source) || clean(lead.processing?.sources?.[0]) || "источник";
}

function sourceBadgeStyle(source: string): CSSProperties {
  const b = SOURCE_BADGE[source] ?? { bg: "rgba(26,37,64,0.07)", text: G.textSecondary, border: "rgba(26,37,64,0.15)" };
  return { background: b.bg, color: b.text, border: `1px solid ${b.border}` };
}

function scoreColor(score: number): string {
  return score >= 70 ? G.green : score >= 45 ? G.amber : G.red;
}

function displayUrl(url: string | null | undefined): string | null {
  const u = clean(url);
  return u ? u.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "") : null;
}

function fullUrl(url: string): string {
  return url.startsWith("http") ? url : `https://${url}`;
}

const PRIORITY_RU: Record<string, string> = { high: "высокий", medium: "средний", low: "низкий" };

// ── HoverCard ─────────────────────────────────────────────────

function HoverCard({ lead, x, y }: { lead: LeadReportItem; x: number; y: number }) {
  const name        = companyName(lead);
  const description = leadDescription(lead);
  const reason      = leadReason(lead);
  const score       = leadScore(lead);
  const source      = sourceLabel(lead);
  const location    = [clean(lead.city), clean(lead.industry)].filter(Boolean).join(" · ");
  const priority    = clean(lead.lead_fit?.priority);
  const painPoints  = (lead.pain_points ?? []).filter(Boolean).slice(0, 3);
  const siteDisplay = displayUrl(lead.website);

  const cardWidth = 300;
  const cardHeight = 280;
  const left = Math.min(x + 14, window.innerWidth - cardWidth - 8);
  const top  = y + 14 + cardHeight > window.innerHeight ? y - cardHeight - 8 : y + 14;

  return createPortal(
    <div style={{
      position: "fixed",
      left, top,
      zIndex: 9999,
      pointerEvents: "none",
      width: `${cardWidth}px`,
    }}>
      <div style={{
        background: "rgba(255,255,255,0.97)",
        border: "1px solid rgba(26,37,64,0.12)",
        borderRadius: G.radius,
        padding: "14px 16px",
        boxShadow: "0 8px 40px rgba(20,40,80,0.18), 0 2px 8px rgba(20,40,80,0.10)",
        display: "flex", flexDirection: "column", gap: "9px",
      }}>
        {/* Header */}
        <div>
          <div style={{ fontWeight: 700, fontSize: "13.5px", color: G.textPrimary, lineHeight: 1.3 }}>{name}</div>
          {location && <div style={{ fontSize: "11.5px", color: G.textMuted, marginTop: "3px" }}>{location}</div>}
        </div>

        {/* Description */}
        {description && (
          <div style={{ fontSize: "12px", color: G.textSecondary, lineHeight: 1.55 }}>{description}</div>
        )}

        {/* Reason to contact */}
        {reason && (
          <div style={{
            fontSize: "12px", color: G.navy, lineHeight: 1.5,
            background: "rgba(74,111,165,0.07)",
            borderLeft: `3px solid ${G.navyLight}`,
            borderRadius: "0 6px 6px 0",
            padding: "6px 10px",
          }}>
            {reason}
          </div>
        )}

        {/* Pain points */}
        {painPoints.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
            {painPoints.map((p) => (
              <span key={p} style={{
                fontSize: "10.5px", fontWeight: 600, padding: "2px 7px",
                borderRadius: "999px", background: G.amberBg, color: G.amber,
                border: "1px solid rgba(176,125,42,0.22)",
              }}>{p}</span>
            ))}
          </div>
        )}

        {/* Contacts */}
        {(clean(lead.email) || clean(lead.phone)) && (
          <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
            {clean(lead.email) && (
              <div style={{ fontSize: "12px", color: G.navyLight, fontWeight: 500 }}>{lead.email}</div>
            )}
            {clean(lead.phone) && (
              <div style={{ fontSize: "12px", color: G.textSecondary }}>{lead.phone}</div>
            )}
          </div>
        )}

        {/* Maps signals */}
        {(typeof lead.maps_rating === "number" || typeof lead.maps_reviews_count === "number" || typeof lead.serp_position === "number") && (
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {typeof lead.maps_rating === "number" && (
              <span style={{ fontSize: "11px", color: G.amber }}>★ {lead.maps_rating.toFixed(1)}</span>
            )}
            {typeof lead.maps_reviews_count === "number" && (
              <span style={{ fontSize: "11px", color: G.textMuted }}>{lead.maps_reviews_count} отзывов</span>
            )}
            {typeof lead.serp_position === "number" && (
              <span style={{ fontSize: "11px", color: G.textMuted }}>позиция #{lead.serp_position}</span>
            )}
          </div>
        )}

        {/* Footer */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          paddingTop: "8px", borderTop: "1px solid rgba(26,37,64,0.08)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{
              ...sourceBadgeStyle(source),
              fontSize: "10.5px", fontWeight: 700, padding: "2px 8px", borderRadius: "999px",
            }}>{source}</span>
            {siteDisplay && (
              <span style={{ fontSize: "11px", color: G.textMuted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "120px" }}>
                {siteDisplay}
              </span>
            )}
          </div>
          {score !== null && (
            <div style={{ display: "flex", alignItems: "baseline", gap: "4px" }}>
              <span style={{ fontSize: "18px", fontWeight: 800, color: scoreColor(score), lineHeight: 1 }}>{score}</span>
              {priority && (
                <span style={{ fontSize: "10px", color: G.textMuted }}>{PRIORITY_RU[priority] ?? priority}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

// ── MobileLeadCard ────────────────────────────────────────────

function MobileLeadCard({ lead }: { lead: LeadReportItem }) {
  const name       = companyName(lead);
  const reason     = leadReason(lead) || leadDescription(lead);
  const score      = leadScore(lead);
  const source     = sourceLabel(lead);
  const painPoints = (lead.pain_points ?? []).filter(Boolean).slice(0, 3);
  const email      = clean(lead.email);
  const phone      = clean(lead.phone);
  const website    = clean(lead.website);
  const siteShort  = displayUrl(lead.website);
  const location   = [clean(lead.city), clean(lead.industry)].filter(Boolean).join(" · ");
  const priority   = clean(lead.lead_fit?.priority);

  return (
    <div style={{ padding: "12px 14px", borderBottom: G.borderSubtle }}>
      {/* Name + score */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: "13.5px", color: G.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {name}
          </div>
          {location && (
            <div style={{ fontSize: "11.5px", color: G.textMuted, marginTop: "2px" }}>{location}</div>
          )}
        </div>
        {score !== null && (
          <div style={{ textAlign: "right", flexShrink: 0 }}>
            <div style={{ fontSize: "18px", fontWeight: 800, color: scoreColor(score), lineHeight: 1 }}>{score}</div>
            {priority && (
              <div style={{ fontSize: "9.5px", color: G.textMuted, marginTop: "1px" }}>{PRIORITY_RU[priority] ?? priority}</div>
            )}
          </div>
        )}
      </div>

      {/* Contacts + site */}
      {(email || phone || siteShort) && (
        <div style={{ marginTop: "7px", display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
          {email && <span style={{ fontSize: "12px", color: G.navyLight, fontWeight: 500 }}>{email}</span>}
          {phone && <span style={{ fontSize: "12px", color: G.textSecondary }}>{phone}</span>}
          {website && siteShort && (
            <a href={fullUrl(website)} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: "11.5px", color: G.navyLight, textDecoration: "none" }}>
              {siteShort}
            </a>
          )}
        </div>
      )}

      {/* Reason / description */}
      {reason && (
        <div style={{
          marginTop: "7px", fontSize: "12px", color: G.textSecondary, lineHeight: 1.45,
          display: "-webkit-box", overflow: "hidden",
          WebkitLineClamp: 3, WebkitBoxOrient: "vertical",
        }}>
          {reason}
        </div>
      )}

      {/* Pain points + maps + source */}
      <div style={{ marginTop: "7px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "4px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "3px", alignItems: "center" }}>
          {painPoints.map((p) => (
            <span key={p} style={{
              fontSize: "10px", fontWeight: 600, padding: "1px 6px", borderRadius: "999px",
              background: G.amberBg, color: G.amber, border: "1px solid rgba(176,125,42,0.22)",
            }}>{p}</span>
          ))}
          {typeof lead.maps_rating === "number" && (
            <span style={{ fontSize: "11px", color: G.amber, marginLeft: "2px" }}>★ {lead.maps_rating.toFixed(1)}</span>
          )}
          {typeof lead.maps_reviews_count === "number" && (
            <span style={{ fontSize: "11px", color: G.textMuted }}>{lead.maps_reviews_count} отз.</span>
          )}
        </div>
        <span style={{
          ...sourceBadgeStyle(source),
          fontSize: "10.5px", fontWeight: 700, padding: "2px 7px", borderRadius: "999px",
        }}>{source}</span>
      </div>
    </div>
  );
}

// ── LeadTable ─────────────────────────────────────────────────

const COLS = ["Компания", "Контакты", "Зацепка", "Score", "Источник"] as const;
const COL_WIDTHS = ["30%", "20%", "28%", "9%", "13%"];

function thStyle(compact: boolean): CSSProperties {
  return {
    padding: compact ? "8px 12px" : "10px 16px",
    textAlign: "left",
    fontSize: "10.5px", fontWeight: 700, color: G.textMuted,
    textTransform: "uppercase", letterSpacing: "0.07em",
    background: "rgba(255,255,255,0.25)",
    borderBottom: G.borderSubtle, whiteSpace: "nowrap",
    overflow: "hidden",
  };
}

function tdStyle(compact: boolean): CSSProperties {
  return {
    padding: compact ? "9px 12px" : "11px 16px",
    fontSize: "13px", color: G.textPrimary,
    borderBottom: G.borderSubtle,
    overflow: "hidden",
    verticalAlign: "top",
  };
}

function LeadTable({ leads, compact }: { leads: LeadReportItem[]; compact: boolean }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 640);
  const hoveredLead = hoveredIndex !== null ? leads[hoveredIndex] : null;
  const th = thStyle(compact);
  const td = tdStyle(compact);

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  if (isMobile) {
    return (
      <div>
        {leads.map((lead, index) => (
          <MobileLeadCard key={lead.id ?? lead.website ?? `${companyName(lead)}-${index}`} lead={lead} />
        ))}
      </div>
    );
  }

  return (
    <div
      style={{ overflowX: "auto" }}
      onMouseMove={(e) => setHoverPos({ x: e.clientX, y: e.clientY })}
    >
      <table style={{ width: "100%", borderCollapse: "collapse", tableLayout: "fixed", minWidth: "520px" }}>
        <colgroup>
          {COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}
        </colgroup>
        <thead>
          <tr>
            {COLS.map((col) => <th key={col} style={th}>{col}</th>)}
          </tr>
        </thead>
        <tbody>
          {leads.map((lead, index) => {
            const name       = companyName(lead);
            // Повод: reason first, fall back to description so AI agent data is shown
            const reason     = leadReason(lead) || leadDescription(lead);
            const score      = leadScore(lead);
            const source     = sourceLabel(lead);
            const painPoints = (lead.pain_points ?? []).filter(Boolean).slice(0, 2);
            const priority   = clean(lead.lead_fit?.priority);
            const email      = clean(lead.email);
            const phone      = clean(lead.phone);
            const website    = clean(lead.website);
            const siteShort  = displayUrl(lead.website);
            const isHovered  = hoveredIndex === index;

            return (
              <tr
                key={lead.id ?? website ?? `${name}-${index}`}
                style={{
                  cursor: "default",
                  background: isHovered ? "rgba(74,111,165,0.06)" : "transparent",
                  transition: "background 0.12s",
                }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                {/* Компания */}
                <td style={td}>
                  <div style={{
                    fontWeight: 600, fontSize: "13px", color: G.textPrimary,
                    lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {name}
                  </div>
                  {website && siteShort && (
                    <a
                      href={fullUrl(website)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        display: "inline-flex", alignItems: "center", gap: "3px",
                        fontSize: "11.5px", color: G.navyLight,
                        textDecoration: "none", marginTop: "2px",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        maxWidth: "100%",
                      }}
                      onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.textDecoration = "underline"}
                      onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.textDecoration = "none"}
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.7 }}>
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                      </svg>
                      {siteShort}
                    </a>
                  )}
                </td>

                {/* Контакты */}
                <td style={td}>
                  {(email || phone) ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                      {email && (
                        <span style={{
                          color: G.navyLight, fontSize: "12px",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block",
                        }}>{email}</span>
                      )}
                      {phone && (
                        <span style={{ color: G.textSecondary, fontSize: "12px", whiteSpace: "nowrap" }}>{phone}</span>
                      )}
                    </div>
                  ) : (
                    <span style={{ color: G.textMuted }}>—</span>
                  )}
                </td>

                {/* Повод */}
                <td style={td}>
                  {reason && (
                    <div style={{
                      fontSize: "12px", color: G.textSecondary, lineHeight: 1.4,
                      display: "-webkit-box", overflow: "hidden",
                      WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                    }}>
                      {reason}
                    </div>
                  )}
                  {painPoints.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "3px", marginTop: reason ? "4px" : "0" }}>
                      {painPoints.map((p) => (
                        <span key={p} style={{
                          fontSize: "10px", fontWeight: 600,
                          padding: "1px 5px", borderRadius: "999px",
                          background: G.amberBg, color: G.amber,
                          border: "1px solid rgba(176,125,42,0.22)",
                          whiteSpace: "nowrap",
                        }}>{p}</span>
                      ))}
                    </div>
                  )}
                  {!reason && !painPoints.length && <span style={{ color: G.textMuted }}>—</span>}
                </td>

                {/* Score */}
                <td style={{ ...td, textAlign: "right" }}>
                  {score !== null ? (
                    <>
                      <div style={{ fontSize: "16px", fontWeight: 800, color: scoreColor(score), lineHeight: 1 }}>{score}</div>
                      {priority && (
                        <div style={{ fontSize: "9.5px", color: G.textMuted, marginTop: "2px", whiteSpace: "nowrap" }}>
                          {PRIORITY_RU[priority] ?? priority}
                        </div>
                      )}
                    </>
                  ) : (
                    <span style={{ color: G.textMuted }}>—</span>
                  )}
                </td>

                {/* Источник */}
                <td style={td}>
                  <span style={{
                    ...sourceBadgeStyle(source),
                    fontSize: "10.5px", fontWeight: 700,
                    padding: "2px 7px", borderRadius: "999px",
                    display: "inline-block",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    maxWidth: "100%",
                  }}>{source}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {hoveredLead && (
        <HoverCard lead={hoveredLead} x={hoverPos.x} y={hoverPos.y} />
      )}
    </div>
  );
}

// ── Public component ──────────────────────────────────────────

export function LeadReportList({ leads, title, compact = false }: LeadReportListProps) {
  if (!leads.length) return null;

  const titleRow = title ? (
    <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "10px" }}>
      <span style={{ fontSize: "13px", fontWeight: 700, color: G.textPrimary }}>{title}</span>
      <span style={{
        fontSize: "11px", fontWeight: 650, color: G.textSecondary,
        background: "rgba(26,37,64,0.08)", borderRadius: "999px", padding: "1px 8px",
      }}>{leads.length}</span>
    </div>
  ) : null;

  if (compact) {
    return (
      <div>
        {titleRow}
        <LeadTable leads={leads} compact />
      </div>
    );
  }

  return (
    <div>
      {titleRow}
      <div style={{
        borderRadius: G.radius, border: G.border, overflow: "hidden",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        boxShadow: G.shadowCard,
      }}>
        <LeadTable leads={leads} compact={false} />
      </div>
    </div>
  );
}
