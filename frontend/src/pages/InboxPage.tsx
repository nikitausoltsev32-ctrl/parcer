import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

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
  "Интерес":    { bg: G.greenBg,  text: G.green,  border: "rgba(45,122,95,0.25)" },
  "Вопрос":     { bg: G.blueBg,   text: G.blue,   border: "rgba(43,108,176,0.25)" },
  "Встреча":    { bg: G.purpleBg, text: G.purple, border: "rgba(107,70,193,0.25)" },
  "Отказ":      { bg: G.redBg,    text: G.red,    border: "rgba(192,57,43,0.25)" },
  "Авто-ответ": { bg: G.amberBg,  text: G.amber,  border: "rgba(176,125,42,0.25)" },
  "Другое":     { bg: "rgba(26,37,64,0.06)", text: G.textMuted, border: "rgba(26,37,64,0.12)" },
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
      {/* Header */}
      <div style={{
        height: "52px", display: "flex", alignItems: "center",
        padding: "0 24px",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Входящие</span>
        {msgs.length > 0 && (
          <span style={{ fontSize: "13px", color: G.textMuted, marginLeft: "8px" }}>{msgs.length} сообщений</span>
        )}
      </div>

      {isLoading ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: G.textMuted, fontSize: "13px" }}>
          Загрузка…
        </div>
      ) : msgs.length === 0 ? (
        /* Empty state */
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "48px 32px", gap: "16px" }}>
          <div style={{
            width: "56px", height: "56px", borderRadius: "14px",
            background: "rgba(255,255,255,0.55)",
            backdropFilter: G.blur, border: G.border,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 13 16 13 14 16 10 16 8 13 2 13"/>
              <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: "14.5px", fontWeight: 600, color: G.textPrimary, textAlign: "center", marginBottom: "6px" }}>Нет входящих</div>
            <div style={{ fontSize: "13px", color: G.textMuted, textAlign: "center", maxWidth: "300px", lineHeight: "1.5" }}>
              Подключите Gmail в настройках, чтобы видеть ответы на ваши кампании
            </div>
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, overflow: "hidden", display: "flex", gap: "16px", padding: "20px 24px" }}>
          {/* List */}
          <div style={{ width: "300px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "5px", overflowY: "auto" }}>
            {msgs.map((msg) => {
              const tag = tagLabel(msg.classification);
              const tc2 = TAG_COLORS[tag] ?? DEFAULT_TAG;
              const active = effectiveActiveId === msg.id;
              return (
                <div
                  key={msg.id}
                  onClick={() => setActiveId(msg.id)}
                  style={{
                    padding: "12px 14px", borderRadius: G.radius,
                    cursor: "pointer", flexShrink: 0,
                    border: active ? `1px solid rgba(26,37,64,0.25)` : G.border,
                    background: active ? "rgba(255,255,255,0.65)" : "rgba(255,255,255,0.40)",
                    backdropFilter: "blur(10px)",
                    transition: "all 0.12s",
                    boxShadow: active ? G.shadowCard : "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "5px" }}>
                    <span style={{ fontWeight: 600, fontSize: "13px", color: G.textPrimary }}>{senderName(msg.from_email)}</span>
                    <span style={{ fontSize: "11px", color: G.textMuted }}>{relativeTime(msg.received_at ?? msg.created_at)}</span>
                  </div>
                  <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "5px", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{msg.from_email}</div>
                  <div style={{ fontSize: "12.5px", fontWeight: 500, color: G.textSecondary, marginBottom: "5px", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{msg.subject}</div>
                  <div style={{
                    fontSize: "12px", color: G.textMuted, lineHeight: "1.4",
                    overflow: "hidden", display: "-webkit-box",
                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                    marginBottom: "8px",
                  }}>{msg.body_text}</div>
                  <span style={{
                    padding: "2px 7px", borderRadius: "6px",
                    fontSize: "11px", fontWeight: 600,
                    background: tc2.bg, color: tc2.text, border: `1px solid ${tc2.border}`,
                  }}>{tag}</span>
                </div>
              );
            })}
          </div>

          {/* Detail */}
          {selected && (
            <div style={{
              flex: 1, borderRadius: G.radius, border: G.border,
              background: "rgba(255,255,255,0.50)",
              backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
              boxShadow: G.shadowCard,
              overflow: "hidden", display: "flex", flexDirection: "column",
            }}>
              {/* Detail header */}
              <div style={{
                padding: "16px 20px", borderBottom: G.borderSubtle,
                display: "flex", alignItems: "center", gap: "10px",
                background: "rgba(255,255,255,0.30)",
              }}>
                <div style={{
                  width: "36px", height: "36px", borderRadius: "50%",
                  background: G.navy, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "13px", fontWeight: 700, color: "rgba(255,255,255,0.85)",
                  border: "2px solid rgba(255,255,255,0.5)",
                }}>
                  {initials(selected.from_email)}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "14px", color: G.textPrimary }}>{selected.from_email}</div>
                  <div style={{ fontSize: "12px", color: G.textMuted }}>{selected.subject}</div>
                </div>
                <div style={{ marginLeft: "auto", display: "flex", gap: "6px", alignItems: "center" }}>
                  <span style={{
                    padding: "2px 8px", borderRadius: "6px",
                    fontSize: "11.5px", fontWeight: 600,
                    background: tc.bg, color: tc.text, border: `1px solid ${tc.border}`,
                  }}>{selectedTag}</span>
                  <select
                    value={selected.classification ?? "other"}
                    onChange={(e) => patchClassification.mutate({ id: selected.id, classification: e.target.value })}
                    style={{
                      fontSize: "12px", color: G.textSecondary,
                      border: G.border, borderRadius: G.radiusXs,
                      padding: "3px 7px",
                      background: "rgba(255,255,255,0.60)",
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
                <div style={{
                  padding: "14px 16px",
                  background: "rgba(255,255,255,0.55)",
                  backdropFilter: "blur(8px)",
                  border: G.border, borderRadius: G.radius,
                  fontSize: "14px", lineHeight: "1.6",
                  color: G.textPrimary, whiteSpace: "pre-wrap",
                }}>
                  {selected.body_text || "(нет текста)"}
                </div>

                <div style={{
                  marginTop: "20px", borderRadius: G.radius, border: G.border,
                  background: "rgba(255,255,255,0.35)", overflow: "hidden",
                }}>
                  <div style={{
                    padding: "10px 14px", borderBottom: G.borderSubtle,
                    display: "flex", alignItems: "center", gap: "6px",
                    fontSize: "12px", color: G.textMuted,
                    background: "rgba(255,255,255,0.20)",
                  }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                    </svg>
                    Ответить (скоро)
                  </div>
                  <div style={{ padding: "14px", fontSize: "13.5px", lineHeight: "1.6", color: G.textMuted }}>
                    Функция ответа через Gmail API появится в следующем обновлении.
                  </div>
                  <div style={{ padding: "8px 14px", borderTop: G.borderSubtle }}>
                    <button disabled style={{
                      padding: "7px 14px", borderRadius: G.radiusSm,
                      background: "rgba(26,37,64,0.06)", color: G.textMuted,
                      border: G.borderSubtle, fontSize: "13px", fontWeight: 500,
                      cursor: "not-allowed", fontFamily: "inherit",
                    }}>
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
