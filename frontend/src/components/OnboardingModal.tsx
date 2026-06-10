import { useState } from "react";

const SLIDE_BG = [
  "linear-gradient(155deg, #1a2540 0%, #2e3f6e 45%, #1a3a5c 100%)",
  "linear-gradient(155deg, #1a3050 0%, #1e5080 50%, #1a4060 100%)",
  "linear-gradient(155deg, #1a3340 0%, #1e6050 50%, #1a4035 100%)",
  "linear-gradient(155deg, #2a1a40 0%, #4a2e70 50%, #3a1a55 100%)",
  "linear-gradient(155deg, #1a2030 0%, #2e3f5e 50%, #1a2840 100%)",
  "linear-gradient(155deg, #1a3528 0%, #1e6040 50%, #1a4530 100%)",
];

const TOTAL = 6;

function ProgressBar({ current }: { current: number }) {
  return (
    <div style={{ display: "flex", gap: "4px", width: "100%" }}>
      {Array.from({ length: TOTAL }).map((_, i) => (
        <div key={i} style={{ flex: 1, height: "2.5px", borderRadius: "2px", background: i < current ? "rgba(255,255,255,0.9)" : i === current ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.18)", overflow: "hidden" }}>
          {i === current && <div style={{ height: "100%", background: "rgba(255,255,255,0.9)", width: "100%" }} />}
        </div>
      ))}
    </div>
  );
}

function Slide0({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px" }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
        <div style={{ position: "absolute", width: "260px", height: "260px", borderRadius: "50%", background: "radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%)", animation: "obPulse 3s ease-in-out infinite" }} />
        <div style={{ position: "absolute", width: "340px", height: "340px", borderRadius: "50%", border: "1px solid rgba(255,255,255,0.06)", animation: "obPulse 3.5s 0.5s ease-in-out infinite" }} />
        <div style={{ width: "110px", height: "110px", borderRadius: "28px", background: "rgba(255,255,255,0.12)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.25)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 24px 64px rgba(0,0,0,0.30)", animation: "obScaleIn 0.6s cubic-bezier(0.16,1,0.3,1) both", position: "relative", zIndex: 2 }}>
          <svg width="60" height="60" viewBox="0 0 52 52" fill="none"><rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white"/><rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white"/><line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.6"/></svg>
        </div>
        {[
          { text: "AI Sales", top: "10%", left: "0%", delay: "0s" },
          { text: "24/7", top: "5%", right: "5%", delay: "0.15s" },
          { text: "Авто", bottom: "18%", left: "2%", delay: "0.3s" },
          { text: "CRM", bottom: "12%", right: "2%", delay: "0.2s" },
        ].map(p => (
          <div key={p.text} style={{ position: "absolute", top: p.top, bottom: p.bottom, left: p.left, right: p.right, padding: "7px 16px", borderRadius: "24px", background: "rgba(255,255,255,0.12)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.22)", fontSize: "13px", fontWeight: 700, color: "rgba(255,255,255,0.9)", boxShadow: "0 4px 20px rgba(0,0,0,0.15)", animation: `obFloat 3.5s ${p.delay} ease-in-out infinite`, zIndex: 1 }}>{p.text}</div>
        ))}
      </div>
      <div style={{ paddingBottom: "40px", animation: "obFadeUp 0.5s 0.2s cubic-bezier(0.16,1,0.3,1) both" }}>
        <h1 style={{ fontSize: "clamp(32px, 7vw, 42px)", fontWeight: 800, color: "white", letterSpacing: "-1px", lineHeight: "1.15", margin: "0 0 14px" }}>Знакомьтесь,<br/>это Лида</h1>
        <p style={{ fontSize: "16px", color: "rgba(255,255,255,0.70)", lineHeight: "1.65", margin: "0 0 28px" }}>AI-менеджер по продажам — ищет клиентов, пишет письма и ведёт до сделки.</p>
        <button onClick={onNext} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", height: "54px", borderRadius: "16px", background: "white", color: "#1a2540", fontSize: "16px", fontWeight: 700, border: "none", cursor: "pointer", boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
          Начать <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
        <button onClick={onSkip} style={{ width: "100%", marginTop: "12px", background: "none", border: "none", color: "rgba(255,255,255,0.45)", fontSize: "14px", cursor: "pointer", fontFamily: "Manrope, sans-serif", padding: "8px" }}>Уже знаком — войти</button>
      </div>
    </div>
  );
}

function Slide1() {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px" }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
        {[{ label: "2ГИС", color: "#60b4ff", top: "8%", left: "2%" }, { label: "SerpAPI", color: "#5eead4", top: "5%", right: "0%" }, { label: "Firecrawl", color: "#fbbf24", bottom: "18%", right: "2%" }].map(b => (
          <div key={b.label} style={{ position: "absolute", top: b.top, left: b.left, right: b.right, bottom: b.bottom, padding: "6px 14px", borderRadius: "20px", background: "rgba(255,255,255,0.10)", backdropFilter: "blur(12px)", border: `1px solid ${b.color}55`, fontSize: "12.5px", fontWeight: 700, color: b.color, animation: "obFloat 3.5s ease-in-out infinite" }}>{b.label}</div>
        ))}
        <div style={{ background: "rgba(255,255,255,0.10)", backdropFilter: "blur(24px)", border: "1px solid rgba(255,255,255,0.20)", borderRadius: "22px", padding: "20px", width: "100%", maxWidth: "300px", boxShadow: "0 24px 64px rgba(0,0,0,0.25)", animation: "obScaleIn 0.5s 0.1s cubic-bezier(0.16,1,0.3,1) both" }}>
          <div style={{ fontSize: "10px", fontWeight: 800, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "14px" }}>Найдено · 7 компаний</div>
          {[{ name: "Студия Форма", col: "#5eead4" }, { name: "Pixel Lab", col: "#5eead4" }, { name: "Craft Bureau", col: "#fbbf24" }, { name: "Линия Дизайна", col: "#5eead4" }].map((c, i) => (
            <div key={c.name} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 0", borderBottom: i < 3 ? "1px solid rgba(255,255,255,0.07)" : "none", animation: `obFadeUp 0.35s ${0.2 + i * 0.08}s cubic-bezier(0.16,1,0.3,1) both` }}>
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: c.col, flexShrink: 0, boxShadow: `0 0 8px ${c.col}` }} />
              <div style={{ flex: 1, fontSize: "14px", fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>{c.name}</div>
            </div>
          ))}
        </div>
      </div>
      <SlideText num="01" title={"Находит компании\nпо всей России"} desc="2ГИС, SerpAPI, Firecrawl — Лида сама читает сайты и оценивает каждого лида." features={["Фильтр по городу, нише, размеру", "Авто-обогащение email и телефона", "Оценка качества каждой компании"]} color="#5eead4" />
    </div>
  );
}

function Slide2() {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "10px", position: "relative" }}>
        <div style={{ alignSelf: "flex-end", maxWidth: "82%", background: "rgba(255,255,255,0.15)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.25)", borderRadius: "18px 18px 4px 18px", padding: "13px 16px", fontSize: "13.5px", lineHeight: "1.55", color: "rgba(255,255,255,0.92)", animation: "obFadeUp 0.4s 0.1s cubic-bezier(0.16,1,0.3,1) both" }}>
          Добрый день! Мы помогаем дизайн-студиям автоматизировать продажи — хотели бы рассказать подробнее.
        </div>
        <div style={{ alignSelf: "flex-start", maxWidth: "80%", background: "rgba(255,255,255,0.95)", borderRadius: "18px 18px 18px 4px", padding: "13px 16px", fontSize: "13.5px", lineHeight: "1.55", color: "#1a2540", boxShadow: "0 12px 40px rgba(0,0,0,0.20)", animation: "obFadeUp 0.4s 0.65s cubic-bezier(0.16,1,0.3,1) both" }}>
          Да, интересно! Расскажите подробнее о ваших услугах…
          <div style={{ marginTop: "8px" }}><span style={{ padding: "3px 10px", borderRadius: "12px", background: "rgba(45,122,95,0.12)", color: "#1e6040", fontSize: "11px", fontWeight: 700 }}>Интерес ✓</span></div>
        </div>
        <div style={{ position: "absolute", top: "8px", left: "0px", padding: "6px 14px", borderRadius: "20px", background: "rgba(255,255,255,0.10)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.20)", fontSize: "12px", fontWeight: 600, color: "#fbbf24", animation: "obFloat 3s 0.2s ease-in-out infinite", display: "flex", gap: "6px", alignItems: "center" }}>
          <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#fbbf24", boxShadow: "0 0 8px #fbbf24" }} /> Follow-up через 3 дня
        </div>
      </div>
      <SlideText num="02" title={"Пишет и отправляет\nсама"} desc="Персональные письма под каждую компанию. Авто follow-up, если не ответили." features={["Персонализация под сайт компании", "Follow-up автоматически через 3–7 дней", "Трекинг открытий, кликов, ответов"]} color="#5eead4" />
    </div>
  );
}

function Slide3() {
  const cols = [
    { label: "Новые", color: "#60b4ff", count: 12, cards: ["Студия Форма", "Pixel Lab", "Бюро Арт"] },
    { label: "Контакт", color: "#fbbf24", count: 5, cards: ["Craft Bureau", "Идея Групп"] },
    { label: "Интерес", color: "#5eead4", count: 3, cards: ["Алина П."] },
  ];
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px" }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", padding: "10px 0" }}>
        {cols.map((col, ci) => (
          <div key={col.label} style={{ flex: 1, background: "rgba(255,255,255,0.07)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.14)", borderRadius: "18px", overflow: "hidden", animation: `obFadeUp 0.4s ${ci * 0.1}s cubic-bezier(0.16,1,0.3,1) both` }}>
            <div style={{ padding: "10px 10px 9px", borderBottom: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", gap: "6px" }}>
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: col.color, boxShadow: `0 0 8px ${col.color}` }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "rgba(255,255,255,0.7)" }}>{col.label}</span>
              <span style={{ marginLeft: "auto", fontSize: "11px", color: col.color, fontWeight: 700 }}>{col.count}</span>
            </div>
            <div style={{ padding: "8px 6px", display: "flex", flexDirection: "column", gap: "5px" }}>
              {col.cards.map((card, i) => (
                <div key={card} style={{ padding: "8px", borderRadius: "10px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", fontSize: "11px", fontWeight: 500, color: "rgba(255,255,255,0.85)", animation: `obFadeUp 0.35s ${ci * 0.1 + i * 0.07 + 0.15}s cubic-bezier(0.16,1,0.3,1) both` }}>{card}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <SlideText num="03" title={"Ведёт воронку\nза вас"} desc="Встроенная CRM с историей, воронкой и умными напоминаниями от Лиды." features={["Воронка: Новые → Интерес → Сделка", "История каждого взаимодействия", "Напоминания и следующие шаги"]} color="#c4b5fd" />
    </div>
  );
}

function Slide4({ answers, setAnswers }: { answers: Record<string, string>; setAnswers: React.Dispatch<React.SetStateAction<Record<string, string>>> }) {
  const fields = [
    { id: "industry", label: "Ваша отрасль", placeholder: "напр. дизайн-студии, IT…" },
    { id: "geo", label: "Город / регион", placeholder: "напр. Казань, вся Россия" },
    { id: "email", label: "Email для рассылки", placeholder: "you@company.com", note: "Можно добавить позже" },
  ];
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px" }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: "130px", height: "130px", borderRadius: "50%", border: "2px dashed rgba(255,255,255,0.12)", display: "flex", alignItems: "center", justifyContent: "center", animation: "obPulse 4s ease-in-out infinite" }}>
          <div style={{ width: "90px", height: "90px", borderRadius: "50%", background: "rgba(255,255,255,0.08)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.18)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="4"/><path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>
          </div>
        </div>
      </div>
      <div style={{ paddingBottom: "28px", animation: "obFadeUp 0.5s 0.1s cubic-bezier(0.16,1,0.3,1) both" }}>
        <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "10px" }}>04 · Настройка</div>
        <h2 style={{ fontSize: "clamp(24px, 5vw, 32px)", fontWeight: 800, color: "white", letterSpacing: "-0.6px", lineHeight: "1.2", margin: "0 0 20px" }}>Расскажите о себе</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {fields.map((f, i) => (
            <div key={f.id} style={{ animation: `obFadeUp 0.4s ${0.15 + i * 0.08}s cubic-bezier(0.16,1,0.3,1) both` }}>
              <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "rgba(255,255,255,0.5)", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.06em" }}>{f.label}</label>
              <input value={answers[f.id] || ""} onChange={e => setAnswers(a => ({ ...a, [f.id]: e.target.value }))} placeholder={f.placeholder} style={{ width: "100%", padding: "13px 15px", borderRadius: "13px", border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.10)", backdropFilter: "blur(12px)", color: "white", fontSize: "14px", fontFamily: "Manrope, sans-serif", outline: "none", boxSizing: "border-box" }} />
              {f.note && <div style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.35)", marginTop: "5px" }}>{f.note}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Slide5({ onComplete }: { onComplete: () => void }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "0 28px" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "20px" }}>
        <div style={{ width: "100px", height: "100px", borderRadius: "50%", background: "rgba(94,234,212,0.12)", border: "2px solid rgba(94,234,212,0.30)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 60px rgba(94,234,212,0.15)", animation: "obScaleIn 0.5s cubic-bezier(0.16,1,0.3,1) both" }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#5eead4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ strokeDasharray: 40, animation: "obCheckDraw 0.5s 0.3s cubic-bezier(0.16,1,0.3,1) both" }}><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div style={{ display: "flex", gap: "10px", width: "100%", maxWidth: "300px", animation: "obFadeUp 0.4s 0.3s cubic-bezier(0.16,1,0.3,1) both" }}>
          {[{ num: "7", label: "источников" }, { num: "∞", label: "лидов" }, { num: "24/7", label: "работает" }].map(s => (
            <div key={s.label} style={{ flex: 1, padding: "14px 10px", borderRadius: "16px", background: "rgba(255,255,255,0.08)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.14)", textAlign: "center" }}>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "white", letterSpacing: "-0.5px" }}>{s.num}</div>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.50)", marginTop: "3px" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ paddingBottom: "40px", animation: "obFadeUp 0.5s 0.2s cubic-bezier(0.16,1,0.3,1) both" }}>
        <h2 style={{ fontSize: "clamp(28px, 6vw, 38px)", fontWeight: 800, color: "white", letterSpacing: "-0.8px", lineHeight: "1.15", margin: "0 0 12px" }}>Лида готова<br/>к работе!</h2>
        <p style={{ fontSize: "15px", color: "rgba(255,255,255,0.60)", lineHeight: "1.60", margin: "0 0 24px" }}>Напишите первый запрос — и она сразу приступит.</p>
        <button onClick={onComplete} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", height: "54px", borderRadius: "16px", background: "white", color: "#1a2540", fontSize: "16px", fontWeight: 700, border: "none", cursor: "pointer", boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
          Начать работу <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>
    </div>
  );
}

function SlideText({ num, title, desc, features, color }: { num: string; title: string; desc: string; features: string[]; color: string }) {
  return (
    <div style={{ paddingBottom: "40px", animation: "obFadeUp 0.5s 0.15s cubic-bezier(0.16,1,0.3,1) both" }}>
      <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "10px" }}>{num} · {title.split("\n")[0].split(" ").slice(-1)[0]}</div>
      <h2 style={{ fontSize: "clamp(26px, 6vw, 36px)", fontWeight: 800, color: "white", letterSpacing: "-0.7px", lineHeight: "1.15", margin: "0 0 14px", whiteSpace: "pre-line" }}>{title}</h2>
      <p style={{ fontSize: "15px", color: "rgba(255,255,255,0.65)", lineHeight: "1.65", margin: "0 0 20px" }}>{desc}</p>
      {features.map((f, i) => (
        <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: "11px", marginBottom: "10px", animation: `obFadeUp 0.4s ${0.3 + i * 0.08}s cubic-bezier(0.16,1,0.3,1) both` }}>
          <div style={{ width: "20px", height: "20px", borderRadius: "50%", background: `rgba(94,234,212,0.15)`, border: `1px solid ${color}55`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: "1px" }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <span style={{ fontSize: "14px", color: "rgba(255,255,255,0.75)", lineHeight: "1.5" }}>{f}</span>
        </div>
      ))}
    </div>
  );
}

export interface OnboardingAnswers {
  industry: string;
  geo: string;
  email: string;
}

interface Props {
  onDone: (answers?: OnboardingAnswers) => void;
}

export default function OnboardingModal({ onDone }: Props) {
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const [answers, setAnswers] = useState<Record<string, string>>({ industry: "", geo: "", email: "" });

  function complete() {
    localStorage.setItem("lida_onboarding_seen", "1");
    const filled = answers.industry.trim() || answers.geo.trim() || answers.email.trim();
    onDone(filled ? (answers as unknown as OnboardingAnswers) : undefined);
  }

  function goNext() {
    if (step >= TOTAL - 1) { complete(); return; }
    setDir(1);
    setStep(s => s + 1);
  }
  function goPrev() {
    if (step <= 0) return;
    setDir(-1);
    setStep(s => s - 1);
  }

  function renderSlide() {
    switch (step) {
      case 0: return <Slide0 onNext={goNext} onSkip={complete} />;
      case 1: return <Slide1 />;
      case 2: return <Slide2 />;
      case 3: return <Slide3 />;
      case 4: return <Slide4 answers={answers} setAnswers={setAnswers} />;
      case 5: return <Slide5 onComplete={complete} />;
      default: return null;
    }
  }

  const showBottomNav = step > 0 && step < TOTAL - 1;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 200, background: SLIDE_BG[step], transition: "background 0.6s cubic-bezier(0.4,0,0.2,1)", display: "flex", flexDirection: "column", fontFamily: "Manrope, sans-serif", overflowY: "auto" }}>
      {/* Tap zones — not on the form slide (4): they'd cover the inputs */}
      {step > 0 && step < 4 && (
        <>
          <div onClick={goPrev} style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: "35%", zIndex: 10, cursor: "pointer" }} />
          <div onClick={goNext} style={{ position: "absolute", top: 0, bottom: 0, right: 0, width: "35%", zIndex: 10, cursor: "pointer" }} />
        </>
      )}

      {/* Top bar */}
      <div style={{ padding: "16px 20px 12px", display: "flex", alignItems: "center", gap: "12px", flexShrink: 0, zIndex: 5, position: "relative", width: "100%", maxWidth: "560px", margin: "0 auto", boxSizing: "border-box" }}>
        {step > 0 && step < TOTAL - 1
          ? <ProgressBar current={step} />
          : <div style={{ flex: 1 }} />
        }
        {step > 0 && step < TOTAL - 1 && (
          <button onClick={complete} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.45)", fontSize: "13px", cursor: "pointer", fontFamily: "Manrope, sans-serif", whiteSpace: "nowrap", flexShrink: 0, padding: "4px" }}>Пропустить</button>
        )}
      </div>

      {/* Slide */}
      <div key={step} style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, animation: `${dir >= 0 ? "obSlideLeft" : "obSlideRight"} 0.35s cubic-bezier(0.16,1,0.3,1) both`, position: "relative", zIndex: 2, width: "100%", maxWidth: "560px", margin: "0 auto" }}>
        {renderSlide()}
      </div>

      {/* Bottom nav */}
      {showBottomNav && (
        <div style={{ padding: "16px 28px 24px", display: "flex", gap: "10px", flexShrink: 0, position: "relative", zIndex: 5, width: "100%", maxWidth: "560px", margin: "0 auto", boxSizing: "border-box" }}>
          <button aria-label="Назад" onClick={goPrev} style={{ width: "54px", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", height: "54px", borderRadius: "16px", background: "rgba(255,255,255,0.18)", border: "1.5px solid rgba(255,255,255,0.35)", color: "rgba(255,255,255,0.85)", cursor: "pointer" }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <button onClick={goNext} style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", height: "54px", borderRadius: "16px", background: "white", color: "#1a2540", fontSize: "16px", fontWeight: 700, border: "none", cursor: "pointer", boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
            {step === 4 ? (answers.industry.trim() ? "Готово" : "Пропустить") : "Далее"}
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      )}
    </div>
  );
}
