import { useEffect, useRef, useState } from "react";

const SLIDES = [
  {
    bg: "linear-gradient(160deg, #0C0C0C 0%, #111810 100%)",
    accent: "oklch(0.52 0.10 165)",
    tag: "Добро пожаловать",
    title: "Лида — ваш\nAI Sales Manager",
    sub: "Находит компании, читает их сайты, готовит персональные письма и помнит всё о клиентах.",
    Visual: () => (
      <div style={{ position: "relative", width: "220px", height: "180px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "absolute", inset: "-40px", borderRadius: "50%", background: "radial-gradient(circle, oklch(0.52 0.10 165 / 0.25) 0%, transparent 65%)", zIndex: 0 }} />
        <div style={{ display: "flex", alignItems: "center", gap: "14px", position: "relative", zIndex: 1 }}>
          <svg width="64" height="64" viewBox="0 0 52 52" fill="none">
            <rect width="52" height="52" rx="13" fill="oklch(0.52 0.10 165)" />
            <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
            <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
            <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
          </svg>
          <span style={{ fontSize: "42px", fontWeight: 800, color: "white", letterSpacing: "-2px" }}>Лида</span>
        </div>
      </div>
    ),
  },
  {
    bg: "linear-gradient(160deg, #0A0F0C 0%, #0D1A12 100%)",
    accent: "oklch(0.60 0.12 165)",
    tag: "Шаг 1 — Поиск",
    title: "Найди любые\nкомпании в чате",
    sub: "Напишите «найди дизайн-студии в Казани» — Лида проверит 2ГИС, SerpAPI и прочитает сайты.",
    Visual: () => (
      <div style={{ width: "280px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "7px" }}>
        <div style={{ background: "rgba(255,255,255,0.08)", borderRadius: "10px 10px 2px 10px", padding: "10px 14px", fontSize: "13px", color: "#DDD", alignSelf: "flex-end", maxWidth: "220px" }}>
          найди дизайн-студии в Казани
        </div>
        {["Студия Форма", "Pixel Lab", "Craft Bureau"].map((n) => (
          <div key={n} style={{ display: "flex", alignItems: "center", gap: "10px", background: "rgba(255,255,255,0.06)", borderRadius: "8px", padding: "9px 12px" }}>
            <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: "oklch(0.60 0.12 165)", flexShrink: 0 }} />
            <span style={{ fontSize: "13px", color: "white", fontWeight: 500, flex: 1 }}>{n}</span>
            <span style={{ fontSize: "10.5px", padding: "1px 6px", borderRadius: "4px", background: "rgba(255,255,255,0.1)", color: "#AAA" }}>SerpAPI</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    bg: "linear-gradient(160deg, #0C0A10 0%, #130F1A 100%)",
    accent: "oklch(0.65 0.14 280)",
    tag: "Шаг 2 — Обогащение",
    title: "Лида читает сайты\nи находит контакты",
    sub: "Firecrawl сканирует каждую компанию — email, телефон, краткое описание. Никаких ручных поисков.",
    Visual: () => (
      <div style={{ width: "280px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "8px" }}>
        {[
          { url: "forma-kazan.ru", email: "hello@forma-kazan.ru", ok: true, src: "Firecrawl" },
          { url: "pixellab.kzn.ru", email: "info@pixellab.kzn.ru", ok: true, src: "SerpAPI" },
          { url: "buroart.ru", email: null, ok: false, src: "2ГИС" },
        ].map((r, i) => (
          <div key={i} style={{ background: "rgba(255,255,255,0.06)", borderRadius: "8px", padding: "9px 12px", display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ width: "24px", height: "24px", borderRadius: "5px", background: r.ok ? "rgba(72,187,120,0.2)" : "rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              {r.ok
                ? <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#48BB78" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                : <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              }
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "12px", color: "#CCC", fontWeight: 500 }}>{r.url}</div>
              {r.email
                ? <div style={{ fontSize: "11px", color: "oklch(0.65 0.14 280)" }}>{r.email}</div>
                : <div style={{ fontSize: "11px", color: "#555" }}>email не найден</div>
              }
            </div>
            <span style={{ fontSize: "10px", padding: "1px 6px", borderRadius: "4px", background: "rgba(255,255,255,0.07)", color: "#888" }}>{r.src}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    bg: "linear-gradient(160deg, #0F0C09 0%, #1A1208 100%)",
    accent: "oklch(0.68 0.14 65)",
    tag: "Шаг 3 — Рассылки",
    title: "Персональные письма\nи ответы в одном месте",
    sub: "Лида пишет письма под каждую компанию, отправляет кампанию и помогает отвечать на входящие.",
    Visual: () => (
      <div style={{ width: "280px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "7px" }}>
        <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "8px", padding: "10px 12px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: "12.5px", color: "white", fontWeight: 600 }}>Дизайн-студии Казань</div>
            <div style={{ fontSize: "11px", color: "#888", marginTop: "2px" }}>7 контактов · активна</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "18px", fontWeight: 700, color: "oklch(0.68 0.14 65)" }}>3</div>
            <div style={{ fontSize: "10px", color: "#666" }}>ответа</div>
          </div>
        </div>
        <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "8px", padding: "9px 12px", display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: "rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700, color: "#AAA", flexShrink: 0 }}>АП</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "12.5px", color: "white", fontWeight: 500 }}>Алина Петрова</div>
            <div style={{ fontSize: "11px", color: "#888", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>Да, интересно! Расскажите подробнее...</div>
          </div>
          <span style={{ fontSize: "10.5px", padding: "2px 7px", borderRadius: "4px", background: "rgba(72,187,120,0.15)", color: "#48BB78", fontWeight: 500, flexShrink: 0 }}>Интерес</span>
        </div>
        <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: "8px", padding: "8px 12px", border: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", gap: "8px" }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="oklch(0.68 0.14 65)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
          <span style={{ fontSize: "11.5px", color: "#888" }}>Лида предлагает ответ...</span>
        </div>
      </div>
    ),
  },
];

const DURATION = 5000;

interface Props {
  onDone: () => void;
  onRegister: () => void;
}

export default function OnboardingModal({ onDone, onRegister }: Props) {
  const [idx, setIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const [exiting, setExiting] = useState(false);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);

  function finish() {
    setExiting(true);
    localStorage.setItem("lida_onboarding_seen", "1");
    setTimeout(onDone, 400);
  }

  function goNext() {
    if (idx < SLIDES.length - 1) setIdx((i) => i + 1);
    else finish();
  }

  function goPrev() {
    if (idx > 0) setIdx((i) => i - 1);
  }

  useEffect(() => {
    setProgress(0);
    startRef.current = null;

    function tick(ts: number) {
      if (!startRef.current) startRef.current = ts;
      const p = Math.min((ts - startRef.current) / DURATION, 1);
      setProgress(p);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        goNext();
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [idx]);

  const slide = SLIDES[idx];
  const isLast = idx === SLIDES.length - 1;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 999,
      background: slide.bg,
      display: "flex", flexDirection: "column",
      opacity: exiting ? 0 : 1,
      transition: "opacity 0.4s ease",
      userSelect: "none",
      fontFamily: "'Manrope', sans-serif",
    }}>
      {/* Progress bars */}
      <div style={{ display: "flex", gap: "4px", padding: "14px 16px 0", position: "relative", zIndex: 10 }}>
        {SLIDES.map((_, i) => (
          <div key={i} style={{ flex: 1, height: "2.5px", borderRadius: "2px", background: "rgba(255,255,255,0.2)", overflow: "hidden" }}>
            <div style={{
              height: "100%", borderRadius: "2px", background: "white",
              width: i < idx ? "100%" : i === idx ? `${progress * 100}%` : "0%",
            }} />
          </div>
        ))}
      </div>

      {/* Top bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", position: "relative", zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <svg width="22" height="22" viewBox="0 0 52 52" fill="none">
            <rect width="52" height="52" rx="13" fill={slide.accent} />
            <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
            <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
            <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
          </svg>
          <span style={{ fontSize: "13px", fontWeight: 700, color: "white", letterSpacing: "-0.3px" }}>Лида</span>
        </div>
        <button onClick={finish} style={{ background: "rgba(255,255,255,0.12)", border: "none", borderRadius: "20px", padding: "5px 13px", color: "rgba(255,255,255,0.7)", fontSize: "12.5px", cursor: "pointer", fontFamily: "inherit", fontWeight: 500 }}>
          Пропустить
        </button>
      </div>

      {/* Tap zones */}
      <div style={{ position: "absolute", inset: 0, display: "flex", zIndex: 5 }}>
        <div style={{ flex: 1 }} onClick={goPrev} />
        <div style={{ flex: 1 }} onClick={goNext} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 24px 40px", position: "relative", zIndex: 6, gap: "28px" }}>
        <div key={`vis-${idx}`} style={{ animation: "onboardFadeUp 0.45s cubic-bezier(0.16,1,0.3,1) both" }}>
          <slide.Visual />
        </div>

        <div key={`txt-${idx}`} style={{ textAlign: "center", animation: "onboardFadeUp 0.45s 0.08s cubic-bezier(0.16,1,0.3,1) both" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: slide.accent, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "10px" }}>{slide.tag}</div>
          <h2 style={{ fontSize: "28px", fontWeight: 800, color: "white", letterSpacing: "-0.8px", lineHeight: "1.2", marginBottom: "12px", whiteSpace: "pre-line", margin: "0 0 12px" }}>{slide.title}</h2>
          <p style={{ fontSize: "14px", color: "rgba(255,255,255,0.55)", lineHeight: "1.6", maxWidth: "340px", margin: "0 auto" }}>{slide.sub}</p>
        </div>

        {isLast && (
          <button
            onClick={() => { finish(); setTimeout(onRegister, 420); }}
            style={{ marginTop: "8px", padding: "13px 32px", borderRadius: "12px", background: slide.accent, color: "white", border: "none", fontSize: "15px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", boxShadow: `0 4px 20px ${slide.accent}55`, animation: "onboardFadeUp 0.45s 0.2s cubic-bezier(0.16,1,0.3,1) both" }}
          >
            Начать работу →
          </button>
        )}
      </div>

      {/* Dot nav */}
      <div style={{ display: "flex", justifyContent: "center", gap: "6px", paddingBottom: "28px", position: "relative", zIndex: 6 }}>
        {SLIDES.map((_, i) => (
          <div key={i} onClick={() => setIdx(i)} style={{ width: i === idx ? "18px" : "6px", height: "6px", borderRadius: "3px", background: i === idx ? "white" : "rgba(255,255,255,0.25)", transition: "all 0.2s", cursor: "pointer" }} />
        ))}
      </div>

      <style>{`
        @keyframes onboardFadeUp {
          from { opacity: 0; transform: translateY(14px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
