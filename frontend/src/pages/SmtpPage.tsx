import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

type ProviderId = "yandex" | "mailru" | "gmail" | "outlook" | "custom";

interface ProviderInfo {
  name: string;
  hint: string;
  domains: string[];
  host: string | null;
  port: number | null;
  accent: string;
  icon: string;
  auth: "oauth" | "password";
}

const PROVIDER_INFO: Record<ProviderId, ProviderInfo> = {
  yandex:  { name: "Яндекс Почта", hint: "Нужен только пароль приложения из Яндекс ID",           domains: ["yandex.ru", "ya.ru", "yandex.com"],                   host: "smtp.yandex.ru",    port: 465, accent: "#FC3F1D", icon: "Я", auth: "password" },
  mailru:  { name: "Mail.ru",      hint: "Нужен только пароль приложения Mail.ru",                domains: ["mail.ru", "bk.ru", "list.ru", "inbox.ru"],            host: "smtp.mail.ru",      port: 465, accent: "#2563EB", icon: "@", auth: "password" },
  gmail:   { name: "Gmail",        hint: "Подключение через Google OAuth без пароля приложения",  domains: ["gmail.com"],                                          host: null,                port: null, accent: "#EA4335", icon: "G", auth: "oauth"    },
  outlook: { name: "Outlook",      hint: "Нужен пароль приложения Microsoft, SMTP настроим автоматически", domains: ["outlook.com", "hotmail.com", "live.com"],   host: "smtp.office365.com",port: 587, accent: "#0078D4", icon: "O", auth: "password" },
  custom:  { name: "Свой SMTP",    hint: "Укажите SMTP-хост и порт вручную",                      domains: [],                                                     host: null,                port: null, accent: "#6B7280", icon: "S", auth: "password" },
};

const DETECTABLE_PROVIDERS: ProviderId[] = ["yandex", "mailru", "gmail", "outlook"];

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

function detectSmtp(email: string): { host: string | null; port: number | null; provider: ProviderId } | null {
  const domain = email.trim().split("@")[1]?.toLowerCase();
  if (!domain) return null;
  const provider = DETECTABLE_PROVIDERS.find((id) => PROVIDER_INFO[id].domains.includes(domain));
  if (provider) return { host: PROVIDER_INFO[provider].host, port: PROVIDER_INFO[provider].port, provider };
  return null;
}

function defaultSenderName(email: string) {
  return email.trim().split("@")[0] || email.trim();
}

function normalizeProvider(provider: string): ProviderId {
  return Object.prototype.hasOwnProperty.call(PROVIDER_INFO, provider) ? (provider as ProviderId) : "custom";
}

function ProviderIcon({ provider, size = 28 }: { provider: ProviderId; size?: number }) {
  const meta = PROVIDER_INFO[provider];
  return (
    <div style={{
      width: `${size}px`, height: `${size}px`, borderRadius: "7px",
      background: meta.accent, flexShrink: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "white", fontWeight: 800, fontSize: `${Math.max(12, size / 2)}px`,
      fontFamily: "Arial",
    }}>
      {meta.icon}
    </div>
  );
}

interface SmtpAccount {
  id: string;
  provider: string;
  from_email: string;
  from_name: string;
  daily_limit: number;
  is_active: boolean;
}

interface FormState {
  from_email: string;
  password: string;
  from_name: string;
  host: string;
  port: string;
  username: string;
}

const EMPTY_FORM: FormState = { from_email: "", password: "", from_name: "", host: "", port: "", username: "" };

const inputS: React.CSSProperties = {
  width: "100%", padding: "9px 12px", borderRadius: G.radiusSm,
  border: G.border, outline: "none",
  fontSize: "13.5px", fontFamily: "inherit", color: G.textPrimary,
  background: "rgba(255,255,255,0.70)", boxSizing: "border-box",
};
const labelS: React.CSSProperties = {
  fontSize: "12px", fontWeight: 600, color: G.textSecondary,
  display: "block", marginBottom: "5px",
};

export default function SmtpPage() {
  const qc = useQueryClient();
  const [showSetup, setShowSetup] = useState(false);
  const [step, setStep] = useState(1);
  const [selectedProvider, setSelectedProvider] = useState<ProviderId | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [gmailConnecting, setGmailConnecting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [detectedHost, setDetectedHost] = useState<string | null>(null);
  const [detectedPort, setDetectedPort] = useState<number | null>(null);

  const searchParams = new URLSearchParams(window.location.search);
  const gmailConnected = searchParams.get("gmail_connected");
  const gmailError = searchParams.get("gmail_error");
  if (gmailConnected || gmailError) {
    window.history.replaceState({}, "", window.location.pathname + "?tab=smtp");
    if (gmailConnected) qc.invalidateQueries({ queryKey: ["smtp-accounts"] });
  }

  const { data: accounts = [] } = useQuery<SmtpAccount[]>({
    queryKey: ["smtp-accounts"],
    queryFn: () => api.get("/smtp-accounts").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body: object) => api.post("/smtp-accounts", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["smtp-accounts"] });
      setShowSetup(false);
      setForm(EMPTY_FORM);
      setStep(1);
      setSelectedProvider(null);
      setShowAdvanced(false);
      setDetectedHost(null);
      setDetectedPort(null);
    },
  });

  const verifyMut = useMutation({
    mutationFn: (id: string) => api.post(`/smtp-accounts/${id}/verify`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["smtp-accounts"] }),
    onSettled: () => setVerifyingId(null),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/smtp-accounts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["smtp-accounts"] }),
  });

  async function handleGmailOAuth() {
    setGmailConnecting(true);
    try {
      const { data } = await api.get("/smtp-accounts/gmail/oauth/start");
      window.location.href = data.auth_url;
    } catch {
      setGmailConnecting(false);
    }
  }

  function resetSetupState() {
    setStep(1);
    setSelectedProvider(null);
    setForm(EMPTY_FORM);
    setShowAdvanced(false);
    setDetectedHost(null);
    setDetectedPort(null);
  }

  function syncEmailDetection(email: string) {
    const detected = detectSmtp(email);
    if (detected) {
      setSelectedProvider(detected.provider);
      setDetectedHost(detected.host);
      setDetectedPort(detected.port);
    } else if (isValidEmail(email)) {
      setSelectedProvider("custom");
      setDetectedHost(null);
      setDetectedPort(null);
    } else {
      setSelectedProvider(null);
      setDetectedHost(null);
      setDetectedPort(null);
    }
  }

  function handleEmailChange(email: string) {
    setForm((f) => ({ ...f, from_email: email }));
    syncEmailDetection(email);
  }

  function continueFromEmail() {
    if (!isValidEmail(form.from_email)) return;
    syncEmailDetection(form.from_email);
    setStep(2);
  }

  function handleConnect() {
    const provider = selectedProvider ?? "custom";
    const providerDefaults = PROVIDER_INFO[provider];
    const fromEmail = form.from_email.trim();
    const isCustomProvider = provider === "custom";
    const host = isCustomProvider ? form.host.trim() : (detectedHost ?? providerDefaults.host ?? "");
    const portValue = isCustomProvider ? form.port : String(detectedPort ?? providerDefaults.port ?? "");
    const port = parseInt(portValue, 10);
    if (!host || !Number.isFinite(port)) return;
    const body: Record<string, unknown> = {
      provider,
      from_email: fromEmail,
      from_name: form.from_name.trim() || defaultSenderName(fromEmail),
      username: form.username.trim() || fromEmail,
      password: form.password.trim(),
      daily_limit: 30,
      host,
      port,
    };
    createMut.mutate(body);
  }

  const emailReady = isValidEmail(form.from_email);
  const currentProvider = selectedProvider ?? (emailReady ? "custom" : null);
  const providerMeta = currentProvider ? PROVIDER_INFO[currentProvider] : null;
  const isCustom = currentProvider === "custom";
  const isOauth = currentProvider !== null && PROVIDER_INFO[currentProvider].auth === "oauth";
  const isAutoDetected = currentProvider !== null && currentProvider !== "custom" && currentProvider !== "gmail";
  const customPort = parseInt(form.port, 10);
  const canConnect = Boolean(
    emailReady &&
    form.password.trim() &&
    (!isCustom || (form.host.trim() && Number.isFinite(customPort) && customPort > 0))
  );

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Почтовые ящики</span>
          <span style={{ fontSize: "13px", color: G.textMuted }}>{accounts.length} подключено</span>
        </div>
        <button
          onClick={() => { resetSetupState(); setShowSetup(true); }}
          style={{
            display: "flex", alignItems: "center", gap: "6px",
            padding: "0 14px", height: "34px", borderRadius: G.radiusSm,
            background: G.navy, color: "white",
            border: "none", fontSize: "13px", fontWeight: 600,
            cursor: "pointer", fontFamily: "inherit", boxShadow: G.shadowBtn,
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Подключить ящик
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {accounts.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingTop: "80px", gap: "12px" }}>
            <div style={{
              width: "48px", height: "48px", borderRadius: "12px",
              background: "rgba(255,255,255,0.55)", backdropFilter: G.blur, border: G.border,
              display: "flex", alignItems: "center", justifyContent: "center", color: G.textMuted,
            }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
            </div>
            <div style={{ fontSize: "14.5px", fontWeight: 600, color: G.textPrimary }}>Нет подключённых ящиков</div>
            <div style={{ fontSize: "13px", color: G.textMuted, maxWidth: "300px", textAlign: "center", lineHeight: "1.5" }}>
              Подключите Gmail, Яндекс, Mail.ru или Outlook, чтобы отправлять письма через Лиду
            </div>
            <button
              onClick={() => { resetSetupState(); setShowSetup(true); }}
              style={{
                marginTop: "4px", padding: "8px 20px", borderRadius: G.radiusSm,
                background: G.navy, color: "white",
                border: "none", fontSize: "13px", fontWeight: 600,
                cursor: "pointer", fontFamily: "inherit", boxShadow: G.shadowBtn,
              }}
            >
              Подключить
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxWidth: "600px" }}>
            {accounts.map((acc) => (
              <div key={acc.id} style={{
                padding: "16px 18px", borderRadius: G.radius,
                border: G.border,
                background: "rgba(255,255,255,0.50)",
                backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
                boxShadow: G.shadowCard,
                display: "flex", alignItems: "center", gap: "14px",
              }}>
                <ProviderIcon provider={normalizeProvider(acc.provider)} size={36} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: "13.5px", color: G.textPrimary }}>{acc.from_email}</div>
                  <div style={{ fontSize: "12px", color: G.textMuted, marginTop: "2px" }}>{acc.from_name} · {acc.daily_limit} писем/день</div>
                </div>
                <span style={{
                  padding: "3px 9px", borderRadius: "6px", fontSize: "11.5px", fontWeight: 600,
                  background: acc.is_active ? G.greenBg : "rgba(26,37,64,0.06)",
                  color: acc.is_active ? G.green : G.textMuted,
                  border: `1px solid ${acc.is_active ? "rgba(45,122,95,0.25)" : "rgba(26,37,64,0.12)"}`,
                }}>
                  {acc.is_active ? "Активен" : "Не проверен"}
                </span>
                <button
                  onClick={() => { setVerifyingId(acc.id); verifyMut.mutate(acc.id); }}
                  disabled={verifyingId === acc.id}
                  style={{
                    padding: "5px 10px", borderRadius: G.radiusXs,
                    border: G.border,
                    background: "rgba(255,255,255,0.60)",
                    fontSize: "12px", cursor: "pointer",
                    fontFamily: "inherit", color: G.textSecondary,
                  }}
                >
                  {verifyingId === acc.id ? "..." : "Проверить"}
                </button>
                <button
                  onClick={() => deleteMut.mutate(acc.id)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: G.textMuted, padding: "4px" }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
                    <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Setup modal */}
      {showSetup && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15,25,50,0.35)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{
            background: "rgba(245,248,252,0.92)",
            backdropFilter: G.blurHeavy, WebkitBackdropFilter: G.blurHeavy,
            border: G.border, borderRadius: G.radius,
            width: "480px", maxWidth: "95vw",
            boxShadow: G.shadowModal, overflow: "hidden",
          }}>
            <div style={{
              padding: "20px 24px 16px", borderBottom: G.borderSubtle,
              display: "flex", alignItems: "center", justifyContent: "space-between",
              background: "rgba(255,255,255,0.30)",
            }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "15px", color: G.textPrimary }}>Подключить почту</div>
                <div style={{ fontSize: "12px", color: G.textMuted, marginTop: "2px" }}>Шаг {step} из 2</div>
              </div>
              <button onClick={() => { setShowSetup(false); resetSetupState(); }} style={{ background: "none", border: "none", cursor: "pointer", color: G.textMuted, fontSize: "20px", lineHeight: 1 }}>×</button>
            </div>

            <div style={{ padding: "20px 24px" }}>
              {step === 1 && (
                <>
                  <div style={{ fontSize: "13px", color: G.textSecondary, marginBottom: "14px" }}>Введите email, а настройки подставим автоматически.</div>
                  <label style={labelS}>Email</label>
                  <input
                    autoFocus
                    type="email"
                    placeholder="you@yandex.ru"
                    value={form.from_email}
                    onChange={(e) => handleEmailChange(e.target.value)}
                    style={inputS}
                  />
                  {form.from_email && !emailReady && (
                    <div style={{ marginTop: "8px", fontSize: "12px", color: G.red }}>Введите корректный email.</div>
                  )}
                  {emailReady && providerMeta && currentProvider && (
                    <div style={{
                      marginTop: "14px", display: "flex", alignItems: "center", gap: "12px",
                      padding: "12px 14px", borderRadius: G.radiusSm,
                      border: currentProvider === "custom" ? G.border : `1px solid rgba(26,37,64,0.20)`,
                      background: currentProvider === "custom" ? "rgba(255,255,255,0.50)" : G.navyXLight,
                    }}>
                      <ProviderIcon provider={currentProvider} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: "13.5px", color: G.textPrimary }}>{providerMeta.name}</div>
                        <div style={{ fontSize: "11.5px", color: G.textMuted, marginTop: "2px", lineHeight: 1.4 }}>
                          {providerMeta.hint}
                          {isAutoDetected && detectedHost && detectedPort ? ` · ${detectedHost}:${detectedPort}` : ""}
                        </div>
                      </div>
                    </div>
                  )}
                  {emailReady && currentProvider === "custom" && (
                    <div style={{ marginTop: "10px", fontSize: "12px", color: G.textMuted, lineHeight: 1.45 }}>
                      Домен не распознан. На следующем шаге потребуется SMTP-хост и порт.
                    </div>
                  )}
                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
                    <button
                      disabled={!emailReady}
                      onClick={continueFromEmail}
                      style={{
                        padding: "8px 20px", borderRadius: G.radiusSm,
                        background: emailReady ? G.navy : "rgba(26,37,64,0.08)",
                        color: emailReady ? "white" : G.textMuted,
                        border: "none", fontSize: "13.5px", fontWeight: 600,
                        cursor: emailReady ? "pointer" : "default",
                        fontFamily: "inherit",
                        boxShadow: emailReady ? G.shadowBtn : "none",
                      }}
                    >
                      Далее
                    </button>
                  </div>
                </>
              )}

              {step === 2 && (
                <>
                  {isOauth && currentProvider === "gmail" ? (
                    <div style={{ textAlign: "center", padding: "12px 0 8px" }}>
                      <div style={{ display: "flex", justifyContent: "center", marginBottom: "14px" }}>
                        <ProviderIcon provider="gmail" size={48} />
                      </div>
                      <div style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary, marginBottom: "8px" }}>Подключить Gmail</div>
                      <div style={{ fontSize: "12.5px", color: G.textMuted, lineHeight: "1.5", maxWidth: "320px", margin: "0 auto 20px" }}>
                        Войдите в Google аккаунт {form.from_email}. Пароль приложения не нужен.
                      </div>
                      <button
                        onClick={handleGmailOAuth}
                        disabled={gmailConnecting}
                        style={{
                          padding: "10px 24px", borderRadius: G.radiusSm,
                          background: "#EA4335", color: "white",
                          border: "none", fontSize: "13.5px", fontWeight: 600,
                          cursor: "pointer", fontFamily: "inherit",
                          opacity: gmailConnecting ? 0.7 : 1,
                        }}
                      >
                        {gmailConnecting ? "Перенаправление..." : "Войти через Google"}
                      </button>
                    </div>
                  ) : (
                    <>
                      {providerMeta && currentProvider && (
                        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                          <ProviderIcon provider={currentProvider} />
                          <div>
                            <div style={{ fontSize: "13.5px", fontWeight: 600, color: G.textPrimary }}>{providerMeta.name}</div>
                            <div style={{ fontSize: "11.5px", color: G.textMuted, marginTop: "2px" }}>{form.from_email}</div>
                          </div>
                        </div>
                      )}
                      {createMut.error && (
                        <div style={{ marginBottom: "12px", padding: "8px 12px", borderRadius: G.radiusXs, background: G.redBg, border: `1px solid rgba(192,57,43,0.25)`, fontSize: "12.5px", color: G.red }}>
                          {(createMut.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Ошибка подключения"}
                        </div>
                      )}
                      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                        {[
                          { key: "password", label: "Пароль приложения", placeholder: "xxxx xxxx xxxx xxxx", type: "password" },
                          ...(isCustom ? [
                            { key: "host", label: "SMTP-хост", placeholder: "smtp.example.com", type: "text" },
                            { key: "port", label: "Порт", placeholder: "587", type: "text" },
                          ] : []),
                        ].map(({ key, label, placeholder, type }) => (
                          <div key={key}>
                            <label style={labelS}>{label}</label>
                            <input
                              type={type}
                              placeholder={placeholder}
                              value={form[key as keyof FormState]}
                              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                              style={inputS}
                            />
                          </div>
                        ))}
                        {isAutoDetected && (
                          <div style={{ fontSize: "12px", color: G.textMuted, padding: "6px 10px", borderRadius: G.radiusXs, background: G.navyXLight, border: G.borderDark }}>
                            SMTP определён автоматически: {detectedHost}:{detectedPort}
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={() => setShowAdvanced((v) => !v)}
                          style={{ alignSelf: "flex-start", background: "none", border: "none", color: G.textSecondary, padding: 0, fontSize: "12.5px", cursor: "pointer", fontFamily: "inherit" }}
                        >
                          {showAdvanced ? "Скрыть дополнительные поля" : "Дополнительные поля"}
                        </button>
                        {showAdvanced && (
                          <>
                            {[
                              { key: "from_name", label: "Имя отправителя", placeholder: defaultSenderName(form.from_email), type: "text" },
                              { key: "username", label: "SMTP-логин", placeholder: form.from_email, type: "text" },
                            ].map(({ key, label, placeholder, type }) => (
                              <div key={key}>
                                <label style={labelS}>{label}</label>
                                <input
                                  type={type}
                                  placeholder={placeholder}
                                  value={form[key as keyof FormState]}
                                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                                  style={inputS}
                                />
                              </div>
                            ))}
                          </>
                        )}
                      </div>
                    </>
                  )}
                  <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "20px" }}>
                    <button
                      onClick={() => setStep(1)}
                      style={{
                        padding: "8px 16px", borderRadius: G.radiusSm,
                        border: G.border, background: "rgba(255,255,255,0.60)",
                        fontSize: "13px", cursor: "pointer",
                        fontFamily: "inherit", color: G.textSecondary,
                      }}
                    >
                      Назад
                    </button>
                    {!isOauth && (
                      <button
                        onClick={handleConnect}
                        disabled={createMut.isPending || !canConnect}
                        style={{
                          padding: "8px 20px", borderRadius: G.radiusSm,
                          background: canConnect ? G.navy : "rgba(26,37,64,0.08)",
                          color: canConnect ? "white" : G.textMuted,
                          border: "none", fontSize: "13.5px", fontWeight: 600,
                          cursor: canConnect ? "pointer" : "default",
                          fontFamily: "inherit",
                          opacity: createMut.isPending || !canConnect ? 0.7 : 1,
                          boxShadow: canConnect ? G.shadowBtn : "none",
                        }}
                      >
                        {createMut.isPending ? "Подключение..." : "Подключить"}
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
