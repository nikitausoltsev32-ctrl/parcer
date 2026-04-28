import { useState } from "react";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface InboxMsg {
  id: number;
  from: string;
  company: string;
  campaign: string;
  tag: string;
  preview: string;
  time: string;
  suggested: string;
}

const INBOX: InboxMsg[] = [
  { id: 1, from: "Алина Петрова", company: "Студия Форма", campaign: "Дизайн-студии Казань", tag: "Интерес", preview: "Да, интересно. Можете рассказать подробнее о ваших услугах?", time: "10 мин", suggested: "Ответить с презентацией" },
  { id: 2, from: "Дмитрий Захаров", company: "Pixel Lab", campaign: "Дизайн-студии Казань", tag: "Вопрос", preview: "Скажите, а вы работаете с небольшими проектами от 50к?", time: "2 ч", suggested: "Уточнить бюджет" },
  { id: 3, from: "Наталья Орлова", company: "Линия Дизайна", campaign: "Дизайн-студии Казань", tag: "Встреча", preview: "Можем созвониться в среду в 15:00? Хотим обсудить детали.", time: "1 д", suggested: "Подтвердить встречу" },
];

const TAG_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Интерес": { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "Вопрос":  { bg: "#EBF8FF", text: "#2B6CB0", border: "#90CDF4" },
  "Встреча": { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "Отказ":   { bg: "#FFF5F5", text: "#C53030", border: "#FEB2B2" },
};

function EmptyInbox() {
  return (
    <div style={{
      flex: 1, display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: "48px 32px", gap: "16px",
    }}>
      <div style={{
        width: "56px", height: "56px", borderRadius: "12px",
        background: "#F5F5F4",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#CCC" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 13 16 13 14 16 10 16 8 13 2 13" />
          <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: "14.5px", fontWeight: 500, color: "#333", textAlign: "center", marginBottom: "6px" }}>Подключите почту</div>
        <div style={{ fontSize: "13px", color: "#999", textAlign: "center", maxWidth: "300px", lineHeight: "1.5" }}>
          Чтобы видеть ответы и отправлять письма, подключите Gmail или Яндекс Почту
        </div>
      </div>
      <button style={{
        marginTop: "4px", padding: "9px 18px", borderRadius: "7px",
        background: SAGE, color: "#FFF", border: "none",
        fontSize: "13.5px", fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
        display: "flex", alignItems: "center", gap: "7px",
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
        Подключить почту
      </button>
    </div>
  );
}

export default function InboxPage() {
  const [activeId, setActiveId] = useState(INBOX[0].id);
  const selected = INBOX.find((m) => m.id === activeId)!;
  const tc = TAG_COLORS[selected?.tag] ?? TAG_COLORS["Вопрос"];

  const hasEmails = INBOX.length > 0;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9", flexShrink: 0,
      }}>
        <div>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Входящие</span>
          {hasEmails && <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{INBOX.length} непрочитанных</span>}
        </div>
      </div>

      {!hasEmails ? (
        <EmptyInbox />
      ) : (
        <div style={{ flex: 1, overflow: "hidden", display: "flex", gap: "16px", padding: "20px 24px" }}>
          {/* List */}
          <div style={{ width: "320px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "6px", overflowY: "auto" }}>
            {INBOX.map((msg) => {
              const tc2 = TAG_COLORS[msg.tag] ?? TAG_COLORS["Вопрос"];
              return (
                <div
                  key={msg.id}
                  onClick={() => setActiveId(msg.id)}
                  style={{
                    padding: "12px 14px", borderRadius: "8px", cursor: "pointer",
                    border: `1px solid ${activeId === msg.id ? SAGE + "60" : "rgba(0,0,0,0.07)"}`,
                    background: activeId === msg.id ? `color-mix(in oklch, ${SAGE} 8%, transparent)` : "#FFF",
                    transition: "all 0.12s",
                    flexShrink: 0,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "5px" }}>
                    <span style={{ fontWeight: 600, fontSize: "13px", color: "#111" }}>{msg.from}</span>
                    <span style={{ fontSize: "11px", color: "#BBB" }}>{msg.time}</span>
                  </div>
                  <div style={{ fontSize: "12px", color: "#888", marginBottom: "7px" }}>{msg.company} · {msg.campaign}</div>
                  <div style={{
                    fontSize: "12.5px", color: "#666", lineHeight: "1.4",
                    overflow: "hidden", display: "-webkit-box",
                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                    marginBottom: "8px",
                  }}>{msg.preview}</div>
                  <span style={{ padding: "2px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: tc2.bg, color: tc2.text, border: `1px solid ${tc2.border}` }}>
                    {msg.tag}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Detail */}
          {selected && (
            <div style={{ flex: 1, borderRadius: "8px", border: `1px solid ${BORDER}`, background: "#FFF", overflow: "hidden", display: "flex", flexDirection: "column" }}>
              <div style={{ padding: "16px 20px", borderBottom: `1px solid ${BORDER}`, display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{
                  width: "36px", height: "36px", borderRadius: "50%",
                  background: "#EEE",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "13px", fontWeight: 600, color: "#666",
                }}>
                  {selected.from.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "14px", color: "#111" }}>{selected.from}</div>
                  <div style={{ fontSize: "12px", color: "#AAA" }}>{selected.company} · {selected.campaign}</div>
                </div>
                <div style={{ marginLeft: "auto", display: "flex", gap: "6px", alignItems: "center" }}>
                  <span style={{ padding: "2px 8px", borderRadius: "4px", fontSize: "11.5px", fontWeight: 500, background: tc.bg, color: tc.text, border: `1px solid ${tc.border}` }}>
                    {selected.tag}
                  </span>
                </div>
              </div>

              <div style={{ flex: 1, padding: "20px", overflow: "auto" }}>
                <div style={{ padding: "14px 16px", background: "#F7F7F5", borderRadius: "8px", fontSize: "14px", lineHeight: "1.6", color: "#333", marginBottom: "20px" }}>
                  {selected.preview}
                </div>

                <div style={{ borderRadius: "8px", border: `1px solid rgba(0,0,0,0.1)`, overflow: "hidden", background: "#FAFAF9" }}>
                  <div style={{ padding: "10px 14px", borderBottom: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#AAA" }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Лида предлагает ответ
                  </div>
                  <div style={{ padding: "14px", fontSize: "13.5px", lineHeight: "1.6", color: "#444" }}>
                    Добрый день, {selected.from.split(" ")[0]}! Конечно, расскажу подробнее — будет удобно созвониться на 20 минут на этой неделе?
                  </div>
                  <div style={{ padding: "8px 14px", borderTop: "1px solid rgba(0,0,0,0.06)", display: "flex", gap: "8px" }}>
                    <button style={{ padding: "7px 14px", borderRadius: "6px", background: SAGE, color: "#FFF", border: "none", fontSize: "13px", fontWeight: 500, cursor: "pointer", fontFamily: "inherit" }}>
                      Отправить
                    </button>
                    <button style={{ padding: "7px 14px", borderRadius: "6px", background: "transparent", color: "#555", border: "1px solid rgba(0,0,0,0.12)", fontSize: "13px", cursor: "pointer", fontFamily: "inherit" }}>
                      Редактировать
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
