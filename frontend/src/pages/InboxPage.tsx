import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

interface InboxMsg {
  id: string;
  from_email: string;
  subject: string;
  body_text: string | null;
  classification: string | null;
  classification_confidence: number | null;
  received_at: string | null;
  created_at: string;
  campaign_id: string | null;
  contact_id: string | null;
}

const CLASSIFICATION_LABELS: Record<string, string> = {
  interested: "Интерес",
  not_interested: "Отказ",
  auto_reply: "Авто-ответ",
  question: "Вопрос",
  meeting_request: "Встреча",
  other: "Другое",
};

const TAG_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Интерес":    { bg: "#F0FFF4", text: "#276749", border: "#9AE6B4" },
  "Вопрос":     { bg: "#EBF8FF", text: "#2B6CB0", border: "#90CDF4" },
  "Встреча":    { bg: "#FAF5FF", text: "#6B46C1", border: "#D6BCFA" },
  "Отказ":      { bg: "#FFF5F5", text: "#C53030", border: "#FEB2B2" },
  "Авто-ответ": { bg: "#FFFFF0", text: "#975A16", border: "#FAF089" },
  "Другое":     { bg: "#F7F7F7", text: "#555",    border: "#DDD" },
};
const DEFAULT_TAG = TAG_COLORS["Другое"];

function tagLabel(classification: string | null): string {
  if (!classification) return "Другое";
  return CLASSIFICATION_LABELS[classification] ?? "Другое";
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 60) return `${min} мин`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} ч`;
  return `${Math.floor(h / 24)} д`;
}

function senderName(email: string): string {
  return email.split("@")[0];
}

function initials(email: string): string {
  return email.slice(0, 2).toUpperCase();
}

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
        <div style={{ fontSize: "14.5px", fontWeight: 500, color: "#333", textAlign: "center", marginBottom: "6px" }}>Нет входящих</div>
        <div style={{ fontSize: "13px", color: "#999", textAlign: "center", maxWidth: "300px", lineHeight: "1.5" }}>
          Подключите Gmail в настройках, чтобы видеть ответы на ваши кампании
        </div>
      </div>
    </div>
  );
}

export default function InboxPage() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);

  const { data: msgs = [], isLoading } = useQuery<InboxMsg[]>({
    queryKey: ["inbox"],
    queryFn: () => api.get("/inbox").then((r) => r.data),
    refetchInterval: 60_000,
  });

  const patchClassification = useMutation({
    mutationFn: ({ id, classification }: { id: string; classification: string }) =>
      api.patch(`/inbox/${id}`, { classification }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inbox"] }),
  });

  const effectiveActiveId = activeId ?? msgs[0]?.id ?? null;
  const selected = msgs.find((m) => m.id === effectiveActiveId) ?? null;
  const selectedTag = tagLabel(selected?.classification ?? null);
  const tc = TAG_COLORS[selectedTag] ?? DEFAULT_TAG;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9", flexShrink: 0,
      }}>
        <div>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Входящие</span>
          {msgs.length > 0 && (
            <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{msgs.length} сообщений</span>
          )}
        </div>
      </div>

      {isLoading ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#AAA", fontSize: "13px" }}>
          Загрузка…
        </div>
      ) : msgs.length === 0 ? (
        <EmptyInbox />
      ) : (
        <div style={{ flex: 1, overflow: "hidden", display: "flex", gap: "16px", padding: "20px 24px" }}>
          {/* List */}
          <div style={{ width: "320px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "6px", overflowY: "auto" }}>
            {msgs.map((msg) => {
              const tag = tagLabel(msg.classification);
              const tc2 = TAG_COLORS[tag] ?? DEFAULT_TAG;
              return (
                <div
                  key={msg.id}
                  onClick={() => setActiveId(msg.id)}
                  style={{
                    padding: "12px 14px", borderRadius: "8px", cursor: "pointer",
                    border: `1px solid ${effectiveActiveId === msg.id ? SAGE + "60" : "rgba(0,0,0,0.07)"}`,
                    background: effectiveActiveId === msg.id ? `color-mix(in oklch, ${SAGE} 8%, transparent)` : "#FFF",
                    transition: "all 0.12s",
                    flexShrink: 0,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "5px" }}>
                    <span style={{ fontWeight: 600, fontSize: "13px", color: "#111" }}>{senderName(msg.from_email)}</span>
                    <span style={{ fontSize: "11px", color: "#BBB" }}>{relativeTime(msg.received_at ?? msg.created_at)}</span>
                  </div>
                  <div style={{ fontSize: "12px", color: "#888", marginBottom: "5px", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{msg.from_email}</div>
                  <div style={{ fontSize: "12.5px", fontWeight: 500, color: "#333", marginBottom: "5px", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{msg.subject}</div>
                  <div style={{
                    fontSize: "12.5px", color: "#666", lineHeight: "1.4",
                    overflow: "hidden", display: "-webkit-box",
                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                    marginBottom: "8px",
                  }}>{msg.body_text}</div>
                  <span style={{ padding: "2px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 500, background: tc2.bg, color: tc2.text, border: `1px solid ${tc2.border}` }}>
                    {tag}
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
                  {initials(selected.from_email)}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "14px", color: "#111" }}>{selected.from_email}</div>
                  <div style={{ fontSize: "12px", color: "#AAA" }}>{selected.subject}</div>
                </div>
                <div style={{ marginLeft: "auto", display: "flex", gap: "6px", alignItems: "center" }}>
                  <span style={{ padding: "2px 8px", borderRadius: "4px", fontSize: "11.5px", fontWeight: 500, background: tc.bg, color: tc.text, border: `1px solid ${tc.border}` }}>
                    {selectedTag}
                  </span>
                  {/* Manual reclassification */}
                  <select
                    value={selected.classification ?? "other"}
                    onChange={(e) => patchClassification.mutate({ id: selected.id, classification: e.target.value })}
                    style={{
                      fontSize: "12px", color: "#666", border: "1px solid rgba(0,0,0,0.12)",
                      borderRadius: "5px", padding: "2px 6px", background: "#FFF",
                      cursor: "pointer", fontFamily: "inherit",
                    }}
                  >
                    {Object.entries(CLASSIFICATION_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ flex: 1, padding: "20px", overflow: "auto" }}>
                <div style={{ padding: "14px 16px", background: "#F7F7F5", borderRadius: "8px", fontSize: "14px", lineHeight: "1.6", color: "#333", whiteSpace: "pre-wrap" }}>
                  {selected.body_text || "(нет текста)"}
                </div>

                <div style={{ marginTop: "20px", borderRadius: "8px", border: `1px solid rgba(0,0,0,0.1)`, overflow: "hidden", background: "#FAFAF9" }}>
                  <div style={{ padding: "10px 14px", borderBottom: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#AAA" }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Ответить (скоро)
                  </div>
                  <div style={{ padding: "14px", fontSize: "13.5px", lineHeight: "1.6", color: "#AAA" }}>
                    Функция ответа через Gmail API появится в следующем обновлении.
                  </div>
                  <div style={{ padding: "8px 14px", borderTop: "1px solid rgba(0,0,0,0.06)", display: "flex", gap: "8px" }}>
                    <button
                      disabled
                      style={{ padding: "7px 14px", borderRadius: "6px", background: "#E5E5E5", color: "#AAA", border: "none", fontSize: "13px", fontWeight: 500, cursor: "not-allowed", fontFamily: "inherit" }}
                    >
                      Отправить
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
