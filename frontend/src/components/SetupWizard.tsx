import { useState } from "react";
import { useUpdateMe } from "../features/auth/hooks";

const SAGE = "oklch(0.52 0.10 165)";

const TONES = [
  { id: "friendly", label: "Дружелюбный", desc: "Тепло и по-человечески" },
  { id: "formal", label: "Деловой", desc: "Официально и профессионально" },
  { id: "direct", label: "Прямой", desc: "Чётко и по делу" },
];

interface Props {
  onDone: () => void;
  initialBusiness?: string;
  initialCity?: string;
}

export default function SetupWizard({ onDone, initialBusiness, initialCity }: Props) {
  const update = useUpdateMe();
  const [step, setStep] = useState(0);
  const [fullName, setFullName] = useState("");
  const [city, setCity] = useState(initialCity ?? "");
  const [business, setBusiness] = useState(initialBusiness ?? "");
  const [offer, setOffer] = useState("");
  const [tone, setTone] = useState("friendly");

  const STEPS = [
    { title: "Расскажите о себе", sub: "Это поможет Лиде персонализировать общение" },
    { title: "Ваш бизнес", sub: "Лида будет использовать это при поиске клиентов" },
    { title: "Тон писем", sub: "Как Лида будет общаться с вашими клиентами" },
  ];

  async function finish() {
    await update.mutateAsync({
      full_name: fullName || undefined,
      business_profile: { business, offer, city, tone_default: tone },
    });
    onDone();
  }

  function skip() {
    update.mutate({ business_profile: { business: "", offer: "", city: "", tone_default: "friendly" } });
    onDone();
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 998,
      background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "16px",
      fontFamily: "'Manrope', sans-serif",
    }}>
      <div style={{
        background: "white",
        borderRadius: "16px",
        width: "100%",
        maxWidth: "440px",
        padding: "32px",
        boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
      }}>
        {/* Progress */}
        <div style={{ display: "flex", gap: "6px", marginBottom: "28px" }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              flex: 1, height: "3px", borderRadius: "2px",
              background: i <= step ? SAGE : "rgba(0,0,0,0.1)",
              transition: "background 0.3s",
            }} />
          ))}
        </div>

        <div style={{ marginBottom: "24px" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: SAGE, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "6px" }}>
            Шаг {step + 1} из {STEPS.length}
          </div>
          <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#1A1A1A", letterSpacing: "-0.5px", margin: "0 0 6px" }}>
            {STEPS[step].title}
          </h2>
          <p style={{ fontSize: "13.5px", color: "#888", margin: 0 }}>{STEPS[step].sub}</p>
        </div>

        {/* Step 0: name + city */}
        {step === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div>
              <label htmlFor="fullName" style={{ fontSize: "12.5px", fontWeight: 600, color: "#555", display: "block", marginBottom: "6px" }}>Ваше имя</label>
              <input
                id="fullName"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Иван Иванов"
                autoFocus
                style={inputStyle}
              />
            </div>
            <div>
              <label htmlFor="city" style={{ fontSize: "12.5px", fontWeight: 600, color: "#555", display: "block", marginBottom: "6px" }}>Город / регион</label>
              <input
                id="city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Москва"
                style={inputStyle}
              />
            </div>
          </div>
        )}

        {/* Step 1: business + offer */}
        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div>
              <label htmlFor="business" style={{ fontSize: "12.5px", fontWeight: 600, color: "#555", display: "block", marginBottom: "6px" }}>Чем занимается ваш бизнес?</label>
              <textarea
                id="business"
                value={business}
                onChange={(e) => setBusiness(e.target.value)}
                placeholder="Разрабатываем мобильные приложения для малого бизнеса"
                rows={3}
                autoFocus
                style={{ ...inputStyle, resize: "none" }}
              />
            </div>
            <div>
              <label htmlFor="offer" style={{ fontSize: "12.5px", fontWeight: 600, color: "#555", display: "block", marginBottom: "6px" }}>Что предлагаете клиентам?</label>
              <textarea
                id="offer"
                value={offer}
                onChange={(e) => setOffer(e.target.value)}
                placeholder="Разработка MVP за 4 недели с фиксированной ценой"
                rows={3}
                style={{ ...inputStyle, resize: "none" }}
              />
            </div>
          </div>
        )}

        {/* Step 2: tone */}
        {step === 2 && (
          <div role="radiogroup" aria-label="Тон писем" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {TONES.map((t) => (
              <div
                key={t.id}
                role="radio"
                aria-checked={tone === t.id}
                tabIndex={0}
                onClick={() => setTone(t.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setTone(t.id);
                  }
                }}
                style={{
                  border: `2px solid ${tone === t.id ? SAGE : "rgba(0,0,0,0.1)"}`,
                  borderRadius: "10px",
                  padding: "12px 14px",
                  cursor: "pointer",
                  background: tone === t.id ? `color-mix(in oklch, ${SAGE} 8%, white)` : "white",
                  transition: "all 0.15s",
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                }}
              >
                <div style={{
                  width: "18px", height: "18px", borderRadius: "50%",
                  border: `2px solid ${tone === t.id ? SAGE : "#DDD"}`,
                  background: tone === t.id ? SAGE : "white",
                  flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {tone === t.id && <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "white" }} />}
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: 600, color: "#1A1A1A" }}>{t.label}</div>
                  <div style={{ fontSize: "12px", color: "#888" }}>{t.desc}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "10px", marginTop: "28px", alignItems: "center" }}>
          <button
            onClick={skip}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "13px", color: "#BBB", padding: 0, fontFamily: "inherit" }}
          >
            Пропустить
          </button>
          <div style={{ flex: 1 }} />
          {step > 0 && (
            <button
              onClick={() => setStep((s) => s - 1)}
              style={{ ...btnSecondary }}
            >
              Назад
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <button onClick={() => setStep((s) => s + 1)} style={btnPrimary}>
              Далее →
            </button>
          ) : (
            <button
              onClick={finish}
              disabled={update.isPending}
              style={{ ...btnPrimary, opacity: update.isPending ? 0.6 : 1 }}
            >
              {update.isPending ? "Сохраняем..." : "Начать работу"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  borderRadius: "8px",
  border: "1.5px solid rgba(0,0,0,0.12)",
  padding: "10px 12px",
  fontSize: "14px",
  fontFamily: "'Manrope', sans-serif",
  color: "#1A1A1A",
  outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.15s",
};

const btnPrimary: React.CSSProperties = {
  background: SAGE,
  color: "white",
  border: "none",
  borderRadius: "8px",
  padding: "10px 20px",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  fontFamily: "'Manrope', sans-serif",
};

const btnSecondary: React.CSSProperties = {
  background: "rgba(0,0,0,0.06)",
  color: "#555",
  border: "none",
  borderRadius: "8px",
  padding: "10px 16px",
  fontSize: "14px",
  fontWeight: 500,
  cursor: "pointer",
  fontFamily: "'Manrope', sans-serif",
};
