import { useRef, useState } from "react";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface Company {
  id: number;
  name: string;
  website: string;
  city: string;
  industry: string;
  source: string;
  email: string | null;
  phone: string | null;
  summary: string;
  confidence: "verified" | "inferred" | "missing" | "failed";
}

const COMPANIES: Company[] = [
  { id: 1, name: "Студия Форма", website: "forma-kazan.ru", city: "Казань", industry: "Дизайн-студия", source: "SerpAPI", email: "hello@forma-kazan.ru", phone: "+7 843 200-11-22", summary: "Занимается брендингом и веб-дизайном, команда 12 человек, активный сайт.", confidence: "verified" },
  { id: 2, name: "Бюро Арт", website: "buroart.ru", city: "Казань", industry: "Дизайн-студия", source: "2ГИС", email: null, phone: "+7 843 511-34-56", summary: "Небольшое дизайн-бюро, специализируется на полиграфии и айдентике.", confidence: "inferred" },
  { id: 3, name: "Pixel Lab", website: "pixellab.kzn.ru", city: "Казань", industry: "Digital-агентство", source: "SerpAPI", email: "info@pixellab.kzn.ru", phone: null, summary: "Digital-агентство, много кейсов в портфолио, работают с локальными брендами.", confidence: "verified" },
  { id: 4, name: "Линия Дизайна", website: "linia-design.ru", city: "Казань", industry: "Дизайн-студия", source: "Firecrawl", email: "contact@linia-design.ru", phone: "+7 917 234-56-78", summary: "UX/UI студия, фокус на мобильных приложениях, есть HR-страница.", confidence: "verified" },
  { id: 5, name: "МаркетАрт", website: "marketart.kzn.ru", city: "Казань", industry: "Маркетинговое агентство", source: "2ГИС", email: null, phone: null, summary: "Сайт не открылся при обходе. Номер телефона взят из 2ГИС.", confidence: "failed" },
  { id: 6, name: "Craft Bureau", website: "craftbureau.ru", city: "Казань", industry: "Дизайн-студия", source: "SerpAPI", email: "hey@craftbureau.ru", phone: "+7 843 900-00-10", summary: "Современная студия, активный Instagram, специализируются на упаковке.", confidence: "verified" },
  { id: 7, name: "Идея Групп", website: "ideagroup.ru", city: "Казань", industry: "Digital-агентство", source: "Firecrawl", email: "info@ideagroup.ru", phone: "+7 843 233-44-55", summary: "Комплексное digital-агентство, контекстная реклама + дизайн.", confidence: "inferred" },
  { id: 8, name: "Студия Контент", website: "studiocontent.ru", city: "Казань", industry: "Контент-студия", source: "manual", email: "hi@studiocontent.ru", phone: null, summary: "Производство видео и фото-контента для брендов.", confidence: "verified" },
];

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "2ГИС":      { bg: "#EEF6FF", text: "#1D6FA4", border: "#BDD8F0" },
  "SerpAPI":   { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "Firecrawl": { bg: "#FFF8F0", text: "#9B4D0F", border: "#FBD38D" },
  "CSV":       { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "manual":    { bg: "#F7FAFC", text: "#4A5568", border: "#CBD5E0" },
};

const CONFIDENCE_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
  verified: { label: "Проверено",     color: "#276749", bg: "#F0FFF4", border: "#9AE6B4" },
  inferred: { label: "Предположение", color: "#7B6000", bg: "#FFFFF0", border: "#ECC94B" },
  missing:  { label: "Нет данных",    color: "#718096", bg: "#F7FAFC", border: "#CBD5E0" },
  failed:   { label: "Ошибка",        color: "#C53030", bg: "#FFF5F5", border: "#FEB2B2" },
};

function SourceBadge({ source }: { source: string }) {
  const c = SOURCE_COLORS[source] ?? SOURCE_COLORS["manual"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "1px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: c.bg, color: c.text, border: `1px solid ${c.border}`, letterSpacing: "0.01em" }}>
      {source}
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
      <div style={{ fontSize: "12px", color: "#999", marginBottom: "10px" }}>{company.city} · {company.industry}</div>
      <div style={{ fontSize: "12px", color: "#666", lineHeight: "1.5", marginBottom: "10px" }}>{company.summary}</div>
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

export default function CompaniesPage() {
  const [search, setSearch] = useState("");
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const tableRef = useRef<HTMLDivElement>(null);

  const filtered = search
    ? COMPANIES.filter((c) =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.industry.toLowerCase().includes(search.toLowerCase())
      )
    : COMPANIES;

  const hoveredCompany = COMPANIES.find((c) => c.id === hoveredId);

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
      {/* Header */}
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9", flexShrink: 0,
      }}>
        <div>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Компании</span>
          <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{COMPANIES.length} записей</span>
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

      {/* Table */}
      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        <div
          ref={tableRef}
          onMouseMove={(e) => {
            setHoverPos({ x: e.clientX, y: e.clientY });
          }}
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
                  key={c.id}
                  onMouseEnter={() => setHoveredId(c.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onClick={() => setSelectedId(c.id === selectedId ? null : c.id)}
                  style={{
                    cursor: "pointer",
                    background: selectedId === c.id ? `color-mix(in oklch, ${SAGE} 6%, transparent)` :
                      hoveredId === c.id ? "rgba(0,0,0,0.02)" : "transparent",
                    transition: "background 0.1s",
                  }}
                >
                  <td style={{ ...cell, fontWeight: 500, color: "#111" }}>{c.name}</td>
                  <td style={cell}><span style={{ color: SAGE }}>{c.website}</span></td>
                  <td style={cell}>{c.city}</td>
                  <td style={cell}>{c.industry}</td>
                  <td style={cell}>{c.email ? <span style={{ color: SAGE }}>{c.email}</span> : <span style={{ color: "#CCC" }}>—</span>}</td>
                  <td style={cell}><SourceBadge source={c.source} /></td>
                  <td style={cell}><ConfidenceBadge state={c.confidence} /></td>
                </tr>
              ))}
            </tbody>
          </table>

          {hoveredId && hoveredCompany && (
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
      </div>
    </div>
  );
}
