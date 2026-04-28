import { useState } from "react";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface Contact {
  id: number;
  name: string;
  company: string;
  status: string;
  email: string | null;
  phone: string | null;
  lastActivity: string;
  nextStep: string;
  source: string;
}

const CONTACTS: Contact[] = [
  { id: 1, name: "Алина Петрова", company: "Студия Форма", status: "Активный", email: "alina@forma-kazan.ru", phone: "+7 843 200-11-22", lastActivity: "2 ч. назад", nextStep: "Отправить КП", source: "SerpAPI" },
  { id: 2, name: "Дмитрий Захаров", company: "Pixel Lab", status: "Новый", email: "dmitry@pixellab.kzn.ru", phone: null, lastActivity: "Сегодня", nextStep: "Позвонить", source: "SerpAPI" },
  { id: 3, name: "Наталья Орлова", company: "Линия Дизайна", status: "Ответил", email: "natasha@linia-design.ru", phone: "+7 917 234-56-78", lastActivity: "1 д. назад", nextStep: "Встреча назначена", source: "manual" },
  { id: 4, name: "Сергей Миронов", company: "Craft Bureau", status: "Пауза", email: "sergey@craftbureau.ru", phone: "+7 843 900-00-10", lastActivity: "5 д. назад", nextStep: "Напомнить через неделю", source: "CSV" },
  { id: 5, name: "Екатерина Смирнова", company: "Бюро Арт", status: "Новый", email: null, phone: "+7 843 511-34-56", lastActivity: "Сегодня", nextStep: "Найти email", source: "2ГИС" },
];

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Активный": { bg: "#EBF8FF", text: "#2B6CB0", border: "#90CDF4" },
  "Новый":    { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "Ответил":  { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "Пауза":    { bg: "#FFFFF0", text: "#7B6000", border: "#ECC94B" },
  "Отказ":    { bg: "#FFF5F5", text: "#C53030", border: "#FEB2B2" },
};

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "2ГИС":    { bg: "#EEF6FF", text: "#1D6FA4", border: "#BDD8F0" },
  "SerpAPI": { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "CSV":     { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "manual":  { bg: "#F7FAFC", text: "#4A5568", border: "#CBD5E0" },
};

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS["Новый"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: "4px", fontSize: "11.5px", fontWeight: 500, background: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
      {status}
    </span>
  );
}

function SourceBadge({ source }: { source: string }) {
  const c = SOURCE_COLORS[source] ?? SOURCE_COLORS["manual"];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "1px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
      {source}
    </span>
  );
}

export default function ContactsPage() {
  const [search, setSearch] = useState("");

  const filtered = search
    ? CONTACTS.filter((c) =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.company.toLowerCase().includes(search.toLowerCase())
      )
    : CONTACTS;

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
          <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{CONTACTS.length} записей</span>
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
        <div style={{ borderRadius: "8px", border: `1px solid ${BORDER}`, overflow: "hidden", background: "#FFF" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Имя", "Компания", "Статус", "Email", "Телефон", "Активность", "Следующий шаг", "Источник"].map((col) => (
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
                        {c.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                      </div>
                      {c.name}
                    </div>
                  </td>
                  <td style={cell}>{c.company}</td>
                  <td style={cell}><StatusBadge status={c.status} /></td>
                  <td style={cell}>{c.email ? <span style={{ color: SAGE }}>{c.email}</span> : <span style={{ color: "#CCC" }}>—</span>}</td>
                  <td style={cell}>{c.phone ?? <span style={{ color: "#CCC" }}>—</span>}</td>
                  <td style={{ ...cell, color: "#999", fontSize: "12px" }}>{c.lastActivity}</td>
                  <td style={cell}>{c.nextStep}</td>
                  <td style={cell}><SourceBadge source={c.source} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
