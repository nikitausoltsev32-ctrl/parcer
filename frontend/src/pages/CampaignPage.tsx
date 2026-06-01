import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface Campaign {
  id: string;
  name: string;
  status: string;
  stats: Record<string, number> | null;
  created_at: string;
}

interface CampaignMessage {
  id: string;
  subject: string;
  body: string;
  status: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  generating: "Генерация",
  pending_approval: "Ожидает утверждения",
  approved: "Утверждена",
  generated: "Готова",
  sending: "Отправка",
  sent: "Отправлена",
  paused: "Пауза",
};

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  draft:            { bg: "rgba(26,37,64,0.06)",  text: G.textMuted,  border: "rgba(26,37,64,0.12)" },
  generating:       { bg: G.amberBg,              text: G.amber,      border: "rgba(176,125,42,0.25)" },
  pending_approval: { bg: "rgba(236,72,153,0.1)", text: "#ec4899",    border: "rgba(236,72,153,0.25)" },
  approved:         { bg: "rgba(16,185,129,0.1)", text: "#10b981",    border: "rgba(16,185,129,0.25)" },
  generated:        { bg: G.blueBg,               text: G.blue,       border: "rgba(43,108,176,0.25)" },
  sending:          { bg: "rgba(192,84,43,0.10)", text: "#c0542b",    border: "rgba(192,84,43,0.25)" },
  sent:             { bg: G.greenBg,              text: G.green,      border: "rgba(45,122,95,0.25)" },
  paused:           { bg: "rgba(26,37,64,0.06)",  text: G.textMuted,  border: "rgba(26,37,64,0.12)" },
};

export default function CampaignPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");

  const { data: campaign, isLoading } = useQuery<Campaign>({
    queryKey: ["campaign", id],
    queryFn: () => api.get(`/campaigns`).then((r) => r.data.find((c: Campaign) => c.id === id)),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "generating" || status === "sending" ? 2000 : false;
    },
  });

  const { data: messages = [] } = useQuery<CampaignMessage[]>({
    queryKey: ["campaign_messages", id],
    queryFn: () => api.get(`/campaigns/${id}/messages`).then(r => r.data),
    enabled: !!id,
  });

  const approveMutation = useMutation({
    mutationFn: () => api.post(`/campaigns/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign", id] });
    }
  });

  const sendMutation = useMutation({
    mutationFn: () => api.post(`/campaigns/${id}/send`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign", id] });
    }
  });

  const updateMessageMutation = useMutation({
    mutationFn: ({ messageId, subject, body }: { messageId: string; subject: string; body: string }) => 
      api.put(`/campaigns/${id}/messages/${messageId}`, { subject, body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign_messages", id] });
      setEditingMessageId(null);
    }
  });

  const startEditing = (msg: CampaignMessage) => {
    setEditingMessageId(msg.id);
    setEditSubject(msg.subject || "");
    setEditBody(msg.body || "");
  };

  const exportCsv = async () => {
    try {
      const response = await api.get(`/campaigns/${id}/export.csv`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `campaign_${id}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      console.error("Export failed", err);
      alert("Ошибка экспорта");
    }
  };

  const cs = campaign ? (STATUS_COLORS[campaign.status] ?? STATUS_COLORS.draft) : STATUS_COLORS.draft;
  const stats = campaign?.stats ?? {};

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", gap: "10px",
        padding: "0 24px",
        background: G.glassHeader, backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <button
          onClick={() => navigate("/app/campaigns")}
          style={{ display: "flex", alignItems: "center", gap: "4px", background: "none", border: "none", cursor: "pointer", color: G.textMuted, fontSize: "13px", fontFamily: "inherit", padding: 0 }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          Кампании
        </button>
        <span style={{ color: G.textMuted }}>/</span>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>{campaign ? campaign.name : "..."}</span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        {isLoading ? (
          <div style={{ color: G.textMuted, fontSize: "13px", textAlign: "center", paddingTop: "48px" }}>Загрузка…</div>
        ) : !campaign ? (
          <div style={{ color: G.textMuted, fontSize: "13px", textAlign: "center", paddingTop: "48px" }}>Кампания не найдена</div>
        ) : (
          <div style={{ maxWidth: "720px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>

            <div style={{ borderRadius: G.radius, border: G.border, background: G.glassCard, backdropFilter: G.blur, WebkitBackdropFilter: G.blur, boxShadow: G.shadowCard, padding: "20px 24px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div style={{
                    width: "44px", height: "44px", borderRadius: G.radiusSm, background: G.navyXLight, flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center", border: G.border,
                  }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={G.navy} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                  </div>
                  <div>
                    <div style={{ fontSize: "16px", fontWeight: 700, color: G.textPrimary, display: "flex", alignItems: "center", gap: "8px" }}>
                      {campaign.name}
                      <span style={{
                        padding: "2px 9px", borderRadius: "6px", fontSize: "11.5px", fontWeight: 500,
                        background: cs.bg, color: cs.text, border: `1px solid ${cs.border}`,
                      }}>
                        {STATUS_LABELS[campaign.status] ?? campaign.status}
                      </span>
                    </div>
                    <div style={{ fontSize: "13px", color: G.textMuted, marginTop: "2px" }}>
                      Создана: {new Date(campaign.created_at).toLocaleString("ru-RU")}
                    </div>
                  </div>
                </div>
                
                <button onClick={exportCsv} style={{
                  display: "flex", alignItems: "center", gap: "6px",
                  padding: "0 14px", height: "34px", borderRadius: G.radiusSm,
                  background: "white", color: G.textPrimary,
                  border: G.border, fontSize: "13px", fontWeight: 600,
                  cursor: "pointer", fontFamily: "inherit", boxShadow: G.shadowCard,
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  Скачать CSV
                </button>
              </div>

              {campaign.status === "pending_approval" && (
                <div style={{ marginTop: "16px", padding: "16px", background: "rgba(236,72,153,0.05)", borderRadius: G.radius, border: "1px solid rgba(236,72,153,0.2)" }}>
                  <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#be185d", marginBottom: "8px" }}>Требуется ваше утверждение</h4>
                  <p style={{ fontSize: "14px", color: G.textSecondary, marginBottom: "16px", lineHeight: 1.5 }}>
                    Лида сгенерировала письма для этой кампании. Проверьте их ниже, и если всё отлично — нажмите кнопку «Утвердить».
                  </p>
                  <button 
                    onClick={() => approveMutation.mutate()}
                    disabled={approveMutation.isPending}
                    style={{
                      background: "#ec4899", color: "white", padding: "10px 20px", borderRadius: "8px",
                      border: "none", fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "8px"
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    Утвердить письма
                  </button>
                </div>
              )}

              {campaign.status === "approved" && (
                <div style={{ marginTop: "16px", padding: "16px", background: "rgba(16,185,129,0.05)", borderRadius: G.radius, border: "1px solid rgba(16,185,129,0.2)" }}>
                  <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#047857", marginBottom: "8px" }}>Готово к отправке</h4>
                  <button 
                    onClick={() => sendMutation.mutate()}
                    disabled={sendMutation.isPending}
                    style={{
                      background: "#10b981", color: "white", padding: "10px 20px", borderRadius: "8px",
                      border: "none", fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "8px"
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                    Начать рассылку
                  </button>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginTop: "24px", borderTop: G.borderSubtle, paddingTop: "20px" }}>
                <div style={{ padding: "16px", background: "rgba(255,255,255,0.5)", borderRadius: G.radius, border: G.border }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: G.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Сгенерировано</div>
                  <div style={{ fontSize: "28px", fontWeight: 700, color: G.textPrimary, fontFamily: "'JetBrains Mono', monospace" }}>{stats.generated ?? 0}</div>
                </div>
                <div style={{ padding: "16px", background: "rgba(255,255,255,0.5)", borderRadius: G.radius, border: G.border }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: G.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Отправлено</div>
                  <div style={{ fontSize: "28px", fontWeight: 700, color: G.green, fontFamily: "'JetBrains Mono', monospace" }}>{stats.sent ?? 0}</div>
                </div>
                <div style={{ padding: "16px", background: "rgba(255,255,255,0.5)", borderRadius: G.radius, border: G.border }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: G.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Ошибок</div>
                  <div style={{ fontSize: "28px", fontWeight: 700, color: stats.failed ? G.red : G.textPrimary, fontFamily: "'JetBrains Mono', monospace" }}>{stats.failed ?? 0}</div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: G.textPrimary }}>Сгенерированные письма ({messages.length})</h3>
              {messages.map(msg => (
                <div key={msg.id} style={{
                  background: "white", borderRadius: G.radius, border: G.border, padding: "16px",
                  boxShadow: G.shadowCard, position: "relative"
                }}>
                  {editingMessageId === msg.id ? (
                    <div>
                      <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "4px" }}>Тема</div>
                      <input 
                        value={editSubject}
                        onChange={e => setEditSubject(e.target.value)}
                        style={{
                          width: "100%", padding: "10px", borderRadius: "8px", border: G.borderSubtle,
                          fontSize: "14px", fontFamily: "inherit", marginBottom: "12px", background: "rgba(0,0,0,0.02)"
                        }}
                      />
                      <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "4px" }}>Текст письма</div>
                      <textarea 
                        value={editBody}
                        onChange={e => setEditBody(e.target.value)}
                        style={{
                          width: "100%", padding: "12px", borderRadius: "8px", border: G.borderSubtle,
                          fontSize: "14px", fontFamily: "inherit", minHeight: "150px", background: "rgba(0,0,0,0.02)",
                          resize: "vertical", marginBottom: "16px"
                        }}
                      />
                      <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                        <button 
                          onClick={() => setEditingMessageId(null)}
                          style={{ padding: "8px 16px", borderRadius: "6px", background: "white", border: G.border, cursor: "pointer", fontSize: "13px", fontWeight: 500 }}
                        >
                          Отмена
                        </button>
                        <button 
                          onClick={() => updateMessageMutation.mutate({ messageId: msg.id, subject: editSubject, body: editBody })}
                          disabled={updateMessageMutation.isPending}
                          style={{ padding: "8px 16px", borderRadius: "6px", background: G.navy, color: "white", border: "none", cursor: "pointer", fontSize: "13px", fontWeight: 500 }}
                        >
                          Сохранить
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      {campaign.status === "pending_approval" && (
                        <button 
                          onClick={() => startEditing(msg)}
                          style={{ position: "absolute", top: "16px", right: "16px", background: "none", border: "none", color: G.blue, cursor: "pointer", fontSize: "13px", fontWeight: 600, display: "flex", alignItems: "center", gap: "4px" }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                          Редактировать
                        </button>
                      )}
                      <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "4px" }}>Тема</div>
                      <div style={{ fontSize: "15px", fontWeight: 600, color: G.textPrimary, marginBottom: "12px", paddingRight: "100px" }}>{msg.subject || "Без темы"}</div>
                      <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "4px" }}>Текст письма</div>
                      <div style={{
                        fontSize: "14px", color: G.textSecondary, lineHeight: 1.6,
                        background: "rgba(0,0,0,0.02)", padding: "12px", borderRadius: "8px",
                        whiteSpace: "pre-wrap"
                      }}>
                        {msg.body}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {messages.length === 0 && (
                <div style={{ color: G.textMuted, fontSize: "14px", padding: "20px", textAlign: "center", background: "white", borderRadius: G.radius, border: G.border }}>
                  Писем пока нет
                </div>
              )}
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
