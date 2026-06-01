import { type CSSProperties, useEffect, useState } from "react";
import { useMe, useUpdateMe } from "../features/auth/hooks";
import { G } from "../lib/design";

const TONES = [
  { id: "friendly", label: "Дружелюбный", desc: "Тепло и по-человечески" },
  { id: "formal", label: "Деловой", desc: "Официально и профессионально" },
  { id: "direct", label: "Прямой", desc: "Чётко и по делу" },
];

const inputStyle: CSSProperties = {
  width: "100%",
  borderRadius: "8px",
  border: "1.5px solid rgba(0,0,0,0.12)",
  padding: "10px 12px",
  fontSize: "14px",
  fontFamily: "inherit",
  color: G.textPrimary,
  outline: "none",
  boxSizing: "border-box",
  background: G.glassInput,
};

const labelStyle: CSSProperties = {
  display: "block",
  marginBottom: "6px",
  color: G.textSecondary,
  fontSize: "12.5px",
  fontWeight: 600,
};

export default function SettingsPage() {
  const { data: me } = useMe();
  const update = useUpdateMe();
  const [fullName, setFullName] = useState("");
  const [business, setBusiness] = useState("");
  const [offer, setOffer] = useState("");
  const [city, setCity] = useState("");
  const [tone, setTone] = useState("friendly");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!me) return;

    setFullName(me.full_name ?? "");
    setBusiness(me.business_profile?.business ?? "");
    setOffer(me.business_profile?.offer ?? "");
    setCity(me.business_profile?.city ?? "");
    setTone(me.business_profile?.tone_default ?? "friendly");
  }, [me]);

  async function save() {
    await update.mutateAsync({
      full_name: fullName || undefined,
      business_profile: { business, offer, city, tone_default: tone },
    });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center",
        padding: "0 24px",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Настройки</span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        <div style={{ maxWidth: "640px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "16px" }}>
          <section style={{
            borderRadius: G.radius,
            border: G.border,
            background: "rgba(255,255,255,0.50)",
            backdropFilter: G.blur,
            WebkitBackdropFilter: G.blur,
            boxShadow: G.shadowCard,
            padding: "20px 24px",
          }}>
            <div style={{ marginBottom: "16px" }}>
              <div style={{ fontSize: "15px", fontWeight: 700, color: G.textPrimary }}>Профиль бизнеса</div>
              <div style={{ marginTop: "4px", color: G.textMuted, fontSize: "13px", lineHeight: 1.45 }}>
                Эти данные используются в чате, поиске лидов и генерации сообщений.
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label htmlFor="fullName" style={labelStyle}>Ваше имя</label>
                <input
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Иван Иванов"
                  style={inputStyle}
                />
              </div>

              <div>
                <label htmlFor="city" style={labelStyle}>Город / регион</label>
                <input
                  id="city"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="Москва"
                  style={inputStyle}
                />
              </div>

              <div>
                <label htmlFor="business" style={labelStyle}>Чем занимается ваш бизнес?</label>
                <textarea
                  id="business"
                  value={business}
                  onChange={(e) => setBusiness(e.target.value)}
                  placeholder="Разрабатываем мобильные приложения для малого бизнеса"
                  rows={3}
                  style={{ ...inputStyle, resize: "vertical", minHeight: "88px" }}
                />
              </div>

              <div>
                <label htmlFor="offer" style={labelStyle}>Что предлагаете клиентам?</label>
                <textarea
                  id="offer"
                  value={offer}
                  onChange={(e) => setOffer(e.target.value)}
                  placeholder="Разработка MVP за 4 недели с фиксированной ценой"
                  rows={3}
                  style={{ ...inputStyle, resize: "vertical", minHeight: "88px" }}
                />
              </div>

              <div>
                <div style={labelStyle}>Тон писем</div>
                <div role="radiogroup" aria-label="Тон писем" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {TONES.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      role="radio"
                      aria-checked={tone === t.id}
                      onClick={() => setTone(t.id)}
                      style={{
                        width: "100%",
                        border: `1.5px solid ${tone === t.id ? G.green : "rgba(0,0,0,0.10)"}`,
                        borderRadius: G.radiusSm,
                        padding: "11px 13px",
                        cursor: "pointer",
                        background: tone === t.id ? G.greenBg : "rgba(255,255,255,0.42)",
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        textAlign: "left",
                        fontFamily: "inherit",
                      }}
                    >
                      <span style={{
                        width: "18px",
                        height: "18px",
                        borderRadius: "50%",
                        border: `2px solid ${tone === t.id ? G.green : "rgba(0,0,0,0.18)"}`,
                        background: tone === t.id ? G.green : "rgba(255,255,255,0.65)",
                        flexShrink: 0,
                        boxSizing: "border-box",
                        boxShadow: tone === t.id ? "inset 0 0 0 4px rgba(255,255,255,0.9)" : "none",
                      }} />
                      <span>
                        <span style={{ display: "block", color: G.textPrimary, fontSize: "14px", fontWeight: 650 }}>{t.label}</span>
                        <span style={{ display: "block", marginTop: "2px", color: G.textMuted, fontSize: "12.5px" }}>{t.desc}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "20px" }}>
              <button
                type="button"
                onClick={save}
                disabled={update.isPending}
                style={{
                  height: "38px",
                  padding: "0 18px",
                  borderRadius: G.radiusSm,
                  border: "none",
                  background: G.navy,
                  color: "white",
                  fontSize: "13.5px",
                  fontWeight: 600,
                  cursor: update.isPending ? "default" : "pointer",
                  fontFamily: "inherit",
                  boxShadow: G.shadowBtn,
                  opacity: update.isPending ? 0.6 : 1,
                }}
              >
                {update.isPending ? "Сохраняем..." : "Сохранить"}
              </button>
              {saved && <span style={{ color: G.green, fontSize: "13px", fontWeight: 600 }}>Сохранено</span>}
              {update.isError && <span style={{ color: G.red, fontSize: "13px", fontWeight: 600 }}>Не удалось сохранить</span>}
            </div>
          </section>

          <section style={{
            borderRadius: G.radius,
            border: G.border,
            background: "rgba(255,255,255,0.50)",
            backdropFilter: G.blur,
            WebkitBackdropFilter: G.blur,
            boxShadow: G.shadowCard,
            padding: "20px 24px",
          }}>
            <div style={{ fontSize: "15px", fontWeight: 700, color: G.textPrimary, marginBottom: "12px" }}>Тариф</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
              {[
                { label: "План", value: me?.plan ?? "-" },
                { label: "Лиды", value: me?.leads_quota ?? "-" },
                { label: "Отправки", value: me?.sends_quota ?? "-" },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    borderRadius: G.radiusSm,
                    border: G.borderSubtle,
                    background: "rgba(255,255,255,0.35)",
                    padding: "12px 14px",
                  }}
                >
                  <div style={{ color: G.textMuted, fontSize: "12px", fontWeight: 600 }}>{item.label}</div>
                  <div style={{ marginTop: "4px", color: G.textPrimary, fontSize: "16px", fontWeight: 750 }}>{item.value}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
