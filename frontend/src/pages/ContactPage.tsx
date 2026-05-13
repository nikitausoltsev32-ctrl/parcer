import { type ReactNode, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface Contact {
  id: string;
  full_name: string;
  company_name: string | null;
  status: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  website: string | null;
  city: string | null;
  industry: string | null;
  enrichment_summary: string | null;
  lead_score: number | null;
  next_step: string | null;
}

interface Activity {
  id: string;
  type: string;
  body: string | null;
  created_at: string;
}

const ACTIVITY_LABELS: Record<string, string> = {
  note: "Заметка",
  email_sent: "Письмо отправлено",
  email_opened: "Письмо открыто",
  email_clicked: "Переход по ссылке",
  email_replied: "Ответ получен",
};

function Row({ label, value }: { label: string; value: ReactNode }) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", gap: "12px", padding: "8px 0", borderBottom: G.borderSubtle }}>
      <span style={{ width: "130px", flexShrink: 0, fontSize: "12px", color: G.textMuted, fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: "13px", color: G.textPrimary }}>{value}</span>
    </div>
  );
}

export default function ContactPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [noteText, setNoteText] = useState("");
  const [showNote, setShowNote] = useState(false);

  const { data: contact, isLoading } = useQuery<Contact>({
    queryKey: ["contact", id],
    queryFn: () => api.get(`/contacts/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  const { data: activities = [] } = useQuery<Activity[]>({
    queryKey: ["contact-activities", id],
    queryFn: () => api.get(`/contacts/${id}/activities`).then((r) => r.data),
    enabled: !!id,
  });

  const addNote = useMutation({
    mutationFn: (body: string) => api.post(`/contacts/${id}/notes`, { body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contact-activities", id] });
      setNoteText("");
      setShowNote(false);
    },
  });

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: G.textMuted, fontSize: "13px" }}>Загрузка…</span>
      </div>
    );
  }

  if (!contact) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: G.textMuted, fontSize: "13px" }}>Контакт не найден</span>
      </div>
    );
  }

  const initials = (contact.full_name ?? "?").split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", gap: "10px",
        padding: "0 24px",
        background: G.glassHeader, backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <button
          onClick={() => navigate("/app/contacts")}
          style={{ display: "flex", alignItems: "center", gap: "4px", background: "none", border: "none", cursor: "pointer", color: G.textMuted, fontSize: "13px", fontFamily: "inherit", padding: 0 }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          Контакты
        </button>
        <span style={{ color: G.textMuted }}>/</span>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>{contact.full_name}</span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        <div style={{ maxWidth: "720px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "16px" }}>

          {/* Info card */}
          <div style={{ borderRadius: G.radius, border: G.border, background: G.glassCard, backdropFilter: G.blur, WebkitBackdropFilter: G.blur, boxShadow: G.shadowCard, padding: "20px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "18px" }}>
              <div style={{
                width: "46px", height: "46px", borderRadius: "50%", background: G.navy, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "15px", fontWeight: 700, color: "rgba(255,255,255,0.85)",
                boxShadow: G.shadowBtn,
              }}>{initials}</div>
              <div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: G.textPrimary }}>{contact.full_name}</div>
                {contact.company_name && (
                  <span
                    onClick={() => navigate(`/app/companies/${encodeURIComponent(contact.company_name!)}`)}
                    style={{ fontSize: "13px", color: G.navyLight, cursor: "pointer" }}
                  >{contact.company_name}</span>
                )}
              </div>
              {contact.lead_score != null && (
                <div style={{ marginLeft: "auto" }}>
                  <span style={{
                    padding: "3px 11px", borderRadius: G.radiusXs, fontSize: "12px", fontWeight: 700,
                    background: contact.lead_score >= 70 ? G.greenBg : contact.lead_score >= 40 ? G.amberBg : G.redBg,
                    color: contact.lead_score >= 70 ? G.green : contact.lead_score >= 40 ? G.amber : G.red,
                  }}>Score {contact.lead_score}</span>
                </div>
              )}
            </div>
            <Row label="Email" value={contact.email && <span style={{ color: G.navyLight }}>{contact.email}</span>} />
            <Row label="Телефон" value={contact.phone} />
            <Row label="Сайт" value={contact.website && <a href={contact.website} target="_blank" rel="noreferrer" style={{ color: G.navyLight }}>{contact.website}</a>} />
            <Row label="Город" value={contact.city} />
            <Row label="Отрасль" value={contact.industry} />
            <Row label="Следующий шаг" value={contact.next_step} />
            {contact.enrichment_summary && (
              <div style={{ paddingTop: "12px" }}>
                <div style={{ fontSize: "12px", color: G.textMuted, fontWeight: 600, marginBottom: "6px" }}>Описание</div>
                <div style={{ fontSize: "13px", color: G.textSecondary, lineHeight: "1.6" }}>{contact.enrichment_summary}</div>
              </div>
            )}
          </div>

          {/* Activities */}
          <div style={{ borderRadius: G.radius, border: G.border, background: G.glassCard, backdropFilter: G.blur, WebkitBackdropFilter: G.blur, boxShadow: G.shadowCard, padding: "20px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: G.textPrimary }}>Активности</span>
              <button
                onClick={() => setShowNote((v) => !v)}
                style={{ display: "flex", alignItems: "center", gap: "5px", padding: "5px 12px", height: "30px", borderRadius: G.radiusSm, background: G.navy, color: "white", border: "none", fontSize: "12.5px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", boxShadow: G.shadowBtn }}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Заметка
              </button>
            </div>

            {showNote && (
              <div style={{ marginBottom: "14px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Текст заметки..."
                  rows={3}
                  style={{ width: "100%", borderRadius: G.radiusSm, border: G.borderDark, background: G.glassInput, color: G.textPrimary, fontSize: "13px", fontFamily: "inherit", padding: "10px 12px", outline: "none", resize: "vertical", boxSizing: "border-box" }}
                />
                <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                  <button onClick={() => setShowNote(false)} style={{ padding: "5px 12px", borderRadius: G.radiusSm, border: G.borderDark, background: "transparent", color: G.textSecondary, fontSize: "12.5px", fontFamily: "inherit", cursor: "pointer" }}>Отмена</button>
                  <button
                    onClick={() => noteText.trim() && addNote.mutate(noteText.trim())}
                    disabled={!noteText.trim() || addNote.isPending}
                    style={{ padding: "5px 12px", borderRadius: G.radiusSm, border: "none", background: G.navy, color: "white", fontSize: "12.5px", fontWeight: 600, fontFamily: "inherit", cursor: "pointer", opacity: !noteText.trim() || addNote.isPending ? 0.6 : 1 }}
                  >{addNote.isPending ? "Сохраняем..." : "Сохранить"}</button>
                </div>
              </div>
            )}

            {activities.length === 0 ? (
              <div style={{ padding: "28px 0", textAlign: "center", color: G.textMuted, fontSize: "13px" }}>Нет активностей</div>
            ) : (
              <div>
                {activities.map((a, i) => (
                  <div key={a.id} style={{ display: "flex", gap: "12px", padding: "9px 0", borderBottom: i < activities.length - 1 ? G.borderSubtle : "none" }}>
                    <div style={{ width: "7px", height: "7px", borderRadius: "50%", marginTop: "5px", flexShrink: 0, background: a.type === "note" ? G.amber : a.type.includes("opened") ? G.green : G.navyLight }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "12.5px", fontWeight: 600, color: G.textPrimary }}>{ACTIVITY_LABELS[a.type] ?? a.type}</span>
                        <span style={{ fontSize: "11.5px", color: G.textMuted }}>{new Date(a.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      {a.body && <div style={{ fontSize: "13px", color: G.textSecondary, marginTop: "3px", lineHeight: "1.5" }}>{a.body}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
