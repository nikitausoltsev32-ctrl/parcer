import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import OnboardingModal from "../components/OnboardingModal";

const ACCENT     = "oklch(0.52 0.10 165)";
const ACCENT_MID = "oklch(0.66 0.10 165)";
const ACCENT_BG  = "oklch(0.96 0.03 165)";

const SUGGESTIONS = [
  "Найди дизайн-студии в Казани",
  "Обогати контакты",
  "Напиши письмо",
  "Покажи без email",
];

function LidaLogo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none">
      <rect width="52" height="52" rx="13" fill={ACCENT} />
      <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
      <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
      <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}

function BgGrid() {
  return (
    <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(0,0,0,0.045)" strokeWidth="1" />
        </pattern>
        <radialGradient id="fade" cx="50%" cy="55%" r="55%">
          <stop offset="0%" stopColor="white" stopOpacity="0" />
          <stop offset="100%" stopColor="white" stopOpacity="1" />
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
      <rect width="100%" height="100%" fill="url(#fade)" />
    </svg>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  function resize() {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }

  function handleChip(s: string) {
    setInput(s);
    setTimeout(resize, 10);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#FAFAF8", position: "relative", overflow: "hidden", fontFamily: "'Manrope', sans-serif" }}>
      {showOnboarding && (
        <OnboardingModal
          onDone={() => setShowOnboarding(false)}
          onRegister={() => { setShowOnboarding(false); navigate("/register"); }}
        />
      )}

      <BgGrid />

      {/* Top glow */}
      <div style={{ position: "absolute", left: 0, right: 0, top: "-80px", height: "420px", background: "radial-gradient(ellipse 90% 55% at 50% 0%, oklch(0.84 0.09 165 / 0.5) 0%, transparent 100%)", pointerEvents: "none", zIndex: 1 }} />

      {/* Nav */}
      <nav style={{ position: "relative", zIndex: 10, height: "58px", display: "flex", alignItems: "center", padding: "0 28px", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <LidaLogo size={30} />
          <span style={{ fontSize: "17px", fontWeight: 800, letterSpacing: "-0.5px", color: "#1A1A1A" }}>Лида</span>
          <span style={{ marginLeft: "4px", fontSize: "11px", padding: "2px 7px", borderRadius: "20px", background: ACCENT_BG, color: ACCENT, border: `1px solid ${ACCENT_MID}55`, fontWeight: 600, letterSpacing: "0.02em" }}>Beta</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={() => navigate("/login")} style={{ padding: "8px 18px", borderRadius: "8px", background: "rgba(255,255,255,0.8)", border: "1px solid rgba(0,0,0,0.12)", fontSize: "13.5px", fontWeight: 500, cursor: "pointer", color: "#333", fontFamily: "inherit" }}>
            Войти
          </button>
          <button onClick={() => setShowOnboarding(true)} style={{ padding: "8px 18px", borderRadius: "8px", background: ACCENT, border: "none", fontSize: "13.5px", fontWeight: 600, cursor: "pointer", color: "#FFF", fontFamily: "inherit", boxShadow: `0 2px 12px oklch(0.52 0.10 165 / 0.3)` }}>
            Зарегистрироваться
          </button>
        </div>
      </nav>

      {/* Center */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 24px", position: "relative", zIndex: 5 }}>
        {/* Tagline pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "7px", padding: "5px 12px", borderRadius: "20px", background: ACCENT_BG, border: `1px solid ${ACCENT_MID}44`, marginBottom: "12px" }}>
          <span style={{ fontSize: "12.5px", fontWeight: 600, color: ACCENT }}>AI Sales Manager для малого бизнеса</span>
        </div>

        {/* Heading */}
        <h1 style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.7px", color: "#1A1A1A", margin: "0 0 6px", textAlign: "center", lineHeight: 1.25, whiteSpace: "nowrap" }}>
          Что сегодня в повестке?
        </h1>
        <p style={{ fontSize: "13.5px", color: "#888", marginBottom: "16px", textAlign: "center", maxWidth: "400px", lineHeight: "1.5", fontWeight: 400, margin: "0 0 16px" }}>
          Найдите клиентов, изучите их и напишите первое письмо — не выходя из чата.
        </p>

        {/* Input */}
        <div style={{ width: "100%", maxWidth: "660px" }}>
          <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: "14px", background: "#FFF", boxShadow: "0 4px 24px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04)" }}>
            <textarea
              ref={taRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); resize(); }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim()) navigate("/register");
                }
              }}
              placeholder="Спросите Лиду…"
              rows={1}
              style={{ width: "100%", border: "none", outline: "none", resize: "none", padding: "15px 18px 10px", fontSize: "15px", lineHeight: "1.55", color: "#1A1A1A", background: "transparent", fontFamily: "Manrope, sans-serif", minHeight: "52px", maxHeight: "180px", overflow: "auto", boxSizing: "border-box" }}
            />
            <div style={{ padding: "0 12px 11px", display: "flex", alignItems: "center", justifyContent: "flex-end" }}>
              <button
                onClick={() => { if (input.trim()) navigate("/register"); }}
                style={{ width: "34px", height: "34px", borderRadius: "8px", flexShrink: 0, background: input.trim() ? ACCENT : "#EBEBEB", border: "none", cursor: input.trim() ? "pointer" : "default", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: input.trim() ? `0 2px 8px oklch(0.52 0.10 165 / 0.35)` : "none", transition: "background 0.15s, box-shadow 0.15s" }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={input.trim() ? "#FFF" : "#AAA"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Chips */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", justifyContent: "center", marginTop: "10px", maxWidth: "660px" }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleChip(s)}
              style={{ padding: "7px 14px", borderRadius: "20px", border: "1px solid rgba(0,0,0,0.1)", background: "rgba(255,255,255,0.8)", fontSize: "13px", cursor: "pointer", color: "#555", fontFamily: "inherit", backdropFilter: "blur(4px)", transition: "border-color 0.12s, color 0.12s, background 0.12s" }}
              onMouseEnter={(e) => { const el = e.currentTarget; el.style.borderColor = ACCENT; el.style.color = ACCENT; el.style.background = ACCENT_BG; }}
              onMouseLeave={(e) => { const el = e.currentTarget; el.style.borderColor = "rgba(0,0,0,0.1)"; el.style.color = "#555"; el.style.background = "rgba(255,255,255,0.8)"; }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Disclaimer */}
        <p style={{ marginTop: "12px", fontSize: "11.5px", color: "#C0C0BA", textAlign: "center", maxWidth: "460px", lineHeight: "1.5" }}>
          Отправляя сообщение, вы соглашаетесь с{" "}
          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: "#AAA", textDecoration: "underline" }}>условиями</a>{" "}и{" "}
          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: "#AAA", textDecoration: "underline" }}>политикой конфиденциальности</a>.{" "}
        </p>
      </div>
    </div>
  );
}
