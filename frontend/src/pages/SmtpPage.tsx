import { useState } from "react";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

const PROVIDERS = [
  {
    id: "yandex",
    name: "Яндекс Почта",
    hint: "Используйте пароль приложения из настроек Яндекс ID",
    icon: (
      <div style={{ width: "28px", height: "28px", borderRadius: "7px", background: "#FC3F1D", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 800, fontSize: "14px", fontFamily: "Arial" }}>Я</div>
    ),
  },
  {
    id: "gmail",
    name: "Gmail",
    hint: "Включите двухфакторную аутентификацию и создайте пароль приложения в Google Account",
    icon: (
      <div style={{ width: "28px", height: "28px", borderRadius: "7px", background: "#EA4335", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: "13px", fontFamily: "Arial" }}>G</div>
    ),
  },
  {
    id: "custom",
    name: "Свой SMTP",
    hint: "Введите данные вашего почтового провайдера вручную",
    icon: (
      <div style={{ width: "28px", height: "28px", borderRadius: "7px", background: "#6B7280", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
      </div>
    ),
  },
];

interface SmtpAccount {
  id: number;
  provider: string;
  from_email: string;
  from_name: string;
  daily_limit: number;
  is_active: boolean;
}

export default function SmtpPage() {
  const [accounts] = useState<SmtpAccount[]>([
    { id: 1, provider: "gmail", from_email: "alexey@gmail.com", from_name: "Алексей Иванов", daily_limit: 30, is_active: true },
  ]);
  const [showSetup, setShowSetup] = useState(false);
  const [step, setStep] = useState(1);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9", flexShrink: 0,
      }}>
        <div>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#111" }}>Почтовые ящики</span>
          <span style={{ fontSize: "13px", color: "#AAA", marginLeft: "8px" }}>{accounts.length} подключено</span>
        </div>
        <button
          onClick={() => { setShowSetup(true); setStep(1); setSelectedProvider(null); }}
          style={{
            padding: "7px 14px", borderRadius: "6px", background: SAGE,
            color: "#FFF", border: "none", fontSize: "13px", fontWeight: 500,
            cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: "6px",
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          Подключить ящик
        </button>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {accounts.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingTop: "64px", gap: "12px" }}>
            <div style={{ width: "44px", height: "44px", borderRadius: "10px", background: "#F5F5F4", display: "flex", alignItems: "center", justifyContent: "center", color: "#AAA" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
            </div>
            <div style={{ fontSize: "14.5px", fontWeight: 500, color: "#333" }}>Нет подключённых ящиков</div>
            <div style={{ fontSize: "13px", color: "#999", maxWidth: "300px", textAlign: "center", lineHeight: "1.5" }}>
              Подключите Gmail или Яндекс, чтобы отправлять письма через Лиду
            </div>
            <button onClick={() => { setShowSetup(true); setStep(1); }} style={{ marginTop: "4px", padding: "8px 16px", borderRadius: "6px", background: SAGE, color: "#FFF", border: "none", fontSize: "13px", fontWeight: 500, cursor: "pointer", fontFamily: "inherit" }}>
              Подключить
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxWidth: "600px" }}>
            {accounts.map((acc) => (
              <div key={acc.id} style={{ padding: "16px 18px", borderRadius: "10px", border: `1px solid ${BORDER}`, background: "#FFF", display: "flex", alignItems: "center", gap: "14px" }}>
                <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: acc.provider === "gmail" ? "#EA4335" : "#FC3F1D", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: "14px", fontFamily: "Arial", flexShrink: 0 }}>
                  {acc.provider === "gmail" ? "G" : "Я"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: "13.5px", color: "#111" }}>{acc.from_email}</div>
                  <div style={{ fontSize: "12px", color: "#999", marginTop: "2px" }}>{acc.from_name} · {acc.daily_limit} писем/день</div>
                </div>
                <span style={{ padding: "3px 9px", borderRadius: "5px", fontSize: "11.5px", fontWeight: 500, background: acc.is_active ? "#F0FFF4" : "#F7FAFC", color: acc.is_active ? "#276749" : "#718096", border: `1px solid ${acc.is_active ? "#9AE6B4" : "#CBD5E0"}` }}>
                  {acc.is_active ? "Активен" : "Отключён"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Setup modal */}
      {showSetup && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", animation: "fadeIn 0.15s ease" }}>
          <div style={{ background: "#FFF", borderRadius: "12px", width: "480px", maxWidth: "95vw", boxShadow: "0 16px 48px rgba(0,0,0,0.18)", overflow: "hidden", animation: "slideInRight 0.2s ease" }}>
            <div style={{ padding: "20px 24px 16px", borderBottom: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "15px", color: "#111" }}>Подключить почту</div>
                <div style={{ fontSize: "12px", color: "#AAA", marginTop: "2px" }}>Шаг {step} из 2</div>
              </div>
              <button onClick={() => setShowSetup(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#BBB", fontSize: "20px", lineHeight: 1 }}>×</button>
            </div>

            <div style={{ padding: "20px 24px" }}>
              {step === 1 && (
                <>
                  <div style={{ fontSize: "13px", color: "#666", marginBottom: "16px" }}>Выберите почтового провайдера:</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {PROVIDERS.map((p) => (
                      <div
                        key={p.id}
                        onClick={() => setSelectedProvider(p.id)}
                        style={{
                          display: "flex", alignItems: "center", gap: "12px",
                          padding: "12px 14px", borderRadius: "8px", cursor: "pointer",
                          border: `1px solid ${selectedProvider === p.id ? SAGE + "80" : "rgba(0,0,0,0.1)"}`,
                          background: selectedProvider === p.id ? `color-mix(in oklch, ${SAGE} 8%, transparent)` : "#FFF",
                          transition: "all 0.12s",
                        }}
                      >
                        {p.icon}
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 500, fontSize: "13.5px", color: "#111" }}>{p.name}</div>
                          <div style={{ fontSize: "11.5px", color: "#999", marginTop: "2px" }}>{p.hint}</div>
                        </div>
                        {selectedProvider === p.id && (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={SAGE} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        )}
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
                    <button
                      disabled={!selectedProvider}
                      onClick={() => setStep(2)}
                      style={{ padding: "8px 20px", borderRadius: "7px", background: selectedProvider ? SAGE : "#E5E5E5", color: selectedProvider ? "#FFF" : "#AAA", border: "none", fontSize: "13.5px", fontWeight: 500, cursor: selectedProvider ? "pointer" : "default", fontFamily: "inherit" }}
                    >
                      Далее
                    </button>
                  </div>
                </>
              )}

              {step === 2 && (
                <>
                  <div style={{ fontSize: "13px", color: "#666", marginBottom: "16px" }}>Введите данные учётной записи:</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {[
                      { label: "Email", placeholder: "you@gmail.com", type: "email" },
                      { label: "Пароль приложения", placeholder: "xxxx xxxx xxxx xxxx", type: "password" },
                      { label: "Имя отправителя", placeholder: "Алексей Иванов", type: "text" },
                    ].map(({ label, placeholder, type }) => (
                      <div key={label}>
                        <label style={{ fontSize: "12px", fontWeight: 500, color: "#666", display: "block", marginBottom: "5px" }}>{label}</label>
                        <input
                          type={type}
                          placeholder={placeholder}
                          style={{ width: "100%", padding: "9px 12px", borderRadius: "7px", border: `1px solid rgba(0,0,0,0.12)`, outline: "none", fontSize: "13.5px", fontFamily: "inherit", color: "#1A1A1A", boxSizing: "border-box" }}
                        />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "20px" }}>
                    <button onClick={() => setStep(1)} style={{ padding: "8px 16px", borderRadius: "7px", border: `1px solid ${BORDER}`, background: "#FFF", fontSize: "13px", cursor: "pointer", fontFamily: "inherit", color: "#555" }}>
                      Назад
                    </button>
                    <button onClick={() => setShowSetup(false)} style={{ padding: "8px 20px", borderRadius: "7px", background: SAGE, color: "#FFF", border: "none", fontSize: "13.5px", fontWeight: 500, cursor: "pointer", fontFamily: "inherit" }}>
                      Подключить
                    </button>
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
