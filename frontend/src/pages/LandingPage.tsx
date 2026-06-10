import { useNavigate } from "react-router-dom";

const NAVY = "#1a2540";
const TEAL = "#0d9488";
const TEAL_LIGHT = "#5eead4";

const FEATURES = [
  {
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    ),
    title: "Находит компании",
    text: "Назовите нишу и город — Лида найдёт реальные сайты компаний, отсеет каталоги и статьи и оценит качество каждого лида.",
  },
  {
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
    ),
    title: "Изучает и пишет",
    text: "Лида читает сайт компании, находит контакты и конкретный повод для письма — и готовит персональное первое сообщение без шаблонов.",
  },
  {
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
    ),
    title: "Ведёт до ответа",
    text: "Встроенная CRM: статусы, follow-up, входящие ответы. Вы сами решаете — автопилот или подтверждение каждого письма.",
  },
];

const STEPS = [
  { num: "01", label: "Запрос", text: "«Найди стоматологии в Екатеринбурге»" },
  { num: "02", label: "Анализ", text: "Лида читает сайты и оценивает каждого лида" },
  { num: "03", label: "Письмо", text: "Персональное сообщение с конкретным поводом" },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <>
      <style>{`
        @keyframes fadeInUp {
          0% { opacity: 0; transform: translateY(30px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fadeInUp 0.9s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          opacity: 0;
        }
        .delay-100 { animation-delay: 100ms; }
        .delay-200 { animation-delay: 200ms; }
        .delay-300 { animation-delay: 300ms; }
        .delay-400 { animation-delay: 400ms; }

        .landing-nav {
          background: rgba(255, 255, 255, 0.65);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-bottom: 1px solid rgba(26, 37, 64, 0.07);
          padding: 14px 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: fixed;
          top: 0; left: 0; right: 0;
          z-index: 100;
        }
        .landing-hero {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 130px 20px 64px;
          text-align: center;
          position: relative;
        }
        .landing-cta-row {
          display: flex;
          gap: 14px;
          justify-content: center;
          flex-wrap: wrap;
        }
        .btn-primary {
          background: ${NAVY};
          color: white;
          padding: 15px 32px;
          border-radius: 14px;
          font-weight: 700;
          font-size: 16px;
          border: none;
          cursor: pointer;
          font-family: inherit;
          transition: transform 0.2s, box-shadow 0.2s;
          box-shadow: 0 10px 28px rgba(26, 37, 64, 0.28);
        }
        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 14px 36px rgba(26, 37, 64, 0.34);
        }
        .btn-secondary {
          background: rgba(255, 255, 255, 0.75);
          color: ${NAVY};
          padding: 15px 32px;
          border-radius: 14px;
          font-weight: 600;
          font-size: 16px;
          border: 1px solid rgba(26, 37, 64, 0.12);
          cursor: pointer;
          font-family: inherit;
          backdrop-filter: blur(10px);
          transition: transform 0.2s, background 0.2s;
          box-shadow: 0 4px 16px rgba(20, 40, 80, 0.08);
        }
        .btn-secondary:hover {
          background: white;
          transform: translateY(-2px);
        }
        .steps-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
          gap: 14px;
          max-width: 860px;
          width: 100%;
          margin: 56px auto 0;
        }
        .step-card {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          border: 1px solid rgba(255, 255, 255, 0.9);
          border-radius: 18px;
          padding: 20px 22px;
          text-align: left;
          box-shadow: 0 8px 30px rgba(20, 40, 80, 0.08);
        }
        .dark-band {
          background: linear-gradient(155deg, #1a2540 0%, #2e3f6e 55%, #1a3a5c 100%);
          border-radius: 36px 36px 0 0;
          padding: 64px 20px 56px;
          position: relative;
          overflow: hidden;
        }
        .feature-card {
          background: rgba(255, 255, 255, 0.07);
          border: 1px solid rgba(255, 255, 255, 0.13);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-radius: 22px;
          padding: 28px;
          transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), background 0.3s;
        }
        .feature-card:hover {
          transform: translateY(-6px);
          background: rgba(255, 255, 255, 0.11);
        }
        @media (min-width: 640px) {
          .landing-nav { padding: 18px 48px; }
          .landing-hero { padding: 150px 24px 80px; }
          .dark-band { padding: 80px 48px 72px; }
          .feature-card { padding: 36px; }
        }
        @media (max-width: 480px) {
          .landing-cta-row { flex-direction: column; align-items: stretch; }
          .nav-login-btn { display: none; }
        }
      `}</style>

      <div style={{
        minHeight: "100vh", display: "flex", flexDirection: "column",
        background: "linear-gradient(165deg, #f4f7fb 0%, #e9eff7 55%, #e3ebf5 100%)",
        color: NAVY, fontFamily: "'Manrope', sans-serif",
      }}>
        {/* Navigation */}
        <nav className="landing-nav">
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <svg width="36" height="36" viewBox="0 0 52 52" fill="none" style={{ flexShrink: 0 }}>
              <rect width="52" height="52" rx="13" fill={NAVY} />
              <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
              <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
              <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
            </svg>
            <span style={{ fontSize: "20px", fontWeight: 800, letterSpacing: "-0.03em", whiteSpace: "nowrap" }}>Лида AI</span>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button className="nav-login-btn" onClick={() => navigate("/login")} style={{
              background: "transparent", color: NAVY, border: "none",
              fontSize: "15px", fontWeight: 600, cursor: "pointer",
              padding: "10px 20px", fontFamily: "inherit", opacity: 0.8,
            }}>Войти</button>
            <button onClick={() => navigate("/register")} style={{
              background: NAVY, color: "white", border: "none",
              fontSize: "14px", fontWeight: 700, cursor: "pointer",
              padding: "11px 22px", borderRadius: "12px", whiteSpace: "nowrap",
              boxShadow: "0 6px 18px rgba(26, 37, 64, 0.25)",
              transition: "transform 0.2s", fontFamily: "inherit",
            }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-2px)"}
               onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}>
              Начать бесплатно
            </button>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="landing-hero">
          <div style={{
            position: "absolute", top: "-120px", left: "50%", transform: "translateX(-50%)",
            width: "min(900px, 120vw)", height: "600px",
            background: "radial-gradient(ellipse, rgba(94, 234, 212, 0.18) 0%, rgba(26, 37, 64, 0.05) 45%, transparent 70%)",
            pointerEvents: "none", zIndex: 0,
          }} />

          <div style={{ position: "relative", zIndex: 1, maxWidth: "900px" }}>
            <div className="animate-fade-in" style={{
              display: "inline-flex", alignItems: "center", gap: "8px",
              background: "rgba(255, 255, 255, 0.7)", border: "1px solid rgba(26, 37, 64, 0.08)",
              padding: "7px 16px", borderRadius: "30px", marginBottom: "28px",
              backdropFilter: "blur(10px)", color: TEAL, fontSize: "13px", fontWeight: 700,
              boxShadow: "0 4px 16px rgba(20, 40, 80, 0.06)",
            }}>
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: TEAL, boxShadow: `0 0 8px ${TEAL_LIGHT}`, flexShrink: 0 }} />
              ИИ-агент по продажам для вашего бизнеса
            </div>

            <h1 className="animate-fade-in delay-100" style={{
              fontSize: "clamp(36px, 9vw, 68px)", fontWeight: 800, lineHeight: 1.08, letterSpacing: "-0.03em",
              marginBottom: "24px", color: NAVY,
            }}>
              Ваш ИИ-сотрудник<br/>для <span style={{
                background: `linear-gradient(110deg, ${NAVY} 10%, ${TEAL} 90%)`,
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>B2B продаж</span>
            </h1>

            <p className="animate-fade-in delay-200" style={{
              fontSize: "clamp(16px, 4vw, 20px)", color: "rgba(26, 37, 64, 0.65)", lineHeight: 1.65,
              maxWidth: "640px", margin: "0 auto 40px", fontWeight: 500,
            }}>
              Лида находит компании по вашей нише и городу, изучает их сайты и готовит персональные письма с конкретным поводом. Вам остаётся подтвердить отправку.
            </p>

            <div className="animate-fade-in delay-300 landing-cta-row">
              <button className="btn-primary" onClick={() => navigate("/register")}>
                Попробовать бесплатно
              </button>
              <button className="btn-secondary" onClick={() => navigate("/login")}>
                Войти
              </button>
            </div>

            <p className="animate-fade-in delay-400" style={{ marginTop: "18px", fontSize: "13px", color: "rgba(26, 37, 64, 0.45)", fontWeight: 600 }}>
              До 20 лидов бесплатно · без карты
            </p>
          </div>

          {/* How it works strip */}
          <div className="animate-fade-in delay-400 steps-row">
            {STEPS.map((s) => (
              <div key={s.num} className="step-card">
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 800, color: TEAL, letterSpacing: "0.08em" }}>{s.num}</span>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</span>
                </div>
                <div style={{ fontSize: "14.5px", color: "rgba(26, 37, 64, 0.7)", lineHeight: 1.55, fontWeight: 500 }}>{s.text}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Dark features band — onboarding palette */}
        <div className="dark-band">
          <div style={{
            position: "absolute", top: "-200px", right: "-150px",
            width: "500px", height: "500px", borderRadius: "50%",
            background: "radial-gradient(circle, rgba(94, 234, 212, 0.10) 0%, transparent 70%)",
            pointerEvents: "none",
          }} />
          <div style={{ maxWidth: "1100px", margin: "0 auto", position: "relative" }}>
            <div style={{ textAlign: "center", marginBottom: "44px" }}>
              <div style={{ fontSize: "12px", fontWeight: 800, color: TEAL_LIGHT, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: "12px" }}>
                Как работает Лида
              </div>
              <h2 style={{ fontSize: "clamp(26px, 6vw, 40px)", fontWeight: 800, color: "white", letterSpacing: "-0.02em", margin: 0, lineHeight: 1.2 }}>
                От запроса до тёплого ответа
              </h2>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))", gap: "20px" }}>
              {FEATURES.map((f) => (
                <div key={f.title} className="feature-card">
                  <div style={{
                    width: "52px", height: "52px", borderRadius: "15px",
                    background: "rgba(94, 234, 212, 0.12)", border: "1px solid rgba(94, 234, 212, 0.25)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    marginBottom: "20px", color: TEAL_LIGHT,
                  }}>
                    {f.icon}
                  </div>
                  <h3 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "12px", color: "white" }}>{f.title}</h3>
                  <p style={{ color: "rgba(255, 255, 255, 0.65)", lineHeight: 1.65, fontSize: "15px", margin: 0 }}>{f.text}</p>
                </div>
              ))}
            </div>

            {/* CTA inside dark band */}
            <div style={{ textAlign: "center", marginTop: "52px" }}>
              <button onClick={() => navigate("/register")} style={{
                background: "white", color: NAVY, border: "none",
                fontSize: "16px", fontWeight: 700, cursor: "pointer",
                padding: "16px 40px", borderRadius: "14px", fontFamily: "inherit",
                boxShadow: "0 10px 32px rgba(0, 0, 0, 0.25)",
                transition: "transform 0.2s",
              }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-2px)"}
                 onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}>
                Начать бесплатно
              </button>
            </div>

            <footer style={{ marginTop: "56px", paddingTop: "24px", borderTop: "1px solid rgba(255,255,255,0.1)", textAlign: "center", fontSize: "13px", color: "rgba(255,255,255,0.4)" }}>
              Лида AI · ИИ-агент для поиска и квалификации B2B-лидов
            </footer>
          </div>
        </div>
      </div>
    </>
  );
}
