const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

const CAMPAIGNS = [
  { id: 1, name: "Дизайн-студии Казань", status: "Активна", contacts: 7, sent: 5, opened: 3, replied: 1, created: "26 апр" },
  { id: 2, name: "IT-компании Москва", status: "Черновик", contacts: 14, sent: 0, opened: 0, replied: 0, created: "24 апр" },
  { id: 3, name: "Агентства недвижимости", status: "Завершена", contacts: 22, sent: 22, opened: 11, replied: 4, created: "10 апр" },
];

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Активна":   { bg: "#EBF8FF", text: "#2B6CB0", border: "#90CDF4" },
  "Черновик":  { bg: "#F7FAFC", text: "#718096", border: "#CBD5E0" },
  "Завершена": { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
};

export default function CampaignsPage() {
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
  const mono: React.CSSProperties = { fontFamily: "'JetBrains Mono', monospace", fontSize: "12.5px" };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9", flexShrink: 0,
      }}>
        <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Кампании</span>
        <button style={{
          padding: "7px 14px", borderRadius: "6px", background: SAGE,
          color: "#FFF", border: "none", fontSize: "13px", fontWeight: 500,
          cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: "6px",
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          Новая кампания
        </button>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        <div style={{ borderRadius: "8px", border: `1px solid ${BORDER}`, overflow: "hidden", background: "#FFF" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Кампания", "Статус", "Контакты", "Отправлено", "Открыто", "Ответили", "Создана"].map((col) => (
                  <th key={col} style={headCell}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CAMPAIGNS.map((c) => {
                const cs = STATUS_COLORS[c.status] ?? STATUS_COLORS["Черновик"];
                return (
                  <tr
                    key={c.id}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.02)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <td style={{ ...cell, fontWeight: 500, color: "#111" }}>{c.name}</td>
                    <td style={cell}>
                      <span style={{ padding: "2px 8px", borderRadius: "4px", fontSize: "11.5px", fontWeight: 500, background: cs.bg, color: cs.text, border: `1px solid ${cs.border}` }}>
                        {c.status}
                      </span>
                    </td>
                    <td style={{ ...cell, ...mono }}>{c.contacts}</td>
                    <td style={{ ...cell, ...mono }}>
                      {c.sent > 0 ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          {c.sent}
                          <div style={{ width: "60px", height: "4px", borderRadius: "2px", background: "#EEE", overflow: "hidden" }}>
                            <div style={{ width: `${(c.sent / c.contacts) * 100}%`, height: "100%", background: SAGE, borderRadius: "2px" }} />
                          </div>
                        </div>
                      ) : <span style={{ color: "#CCC" }}>—</span>}
                    </td>
                    <td style={{ ...cell, ...mono }}>{c.opened > 0 ? c.opened : <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={{ ...cell, ...mono }}>{c.replied > 0 ? c.replied : <span style={{ color: "#CCC" }}>—</span>}</td>
                    <td style={{ ...cell, color: "#999", fontSize: "12px" }}>{c.created}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
