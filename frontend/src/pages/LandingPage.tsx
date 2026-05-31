import { useNavigate } from "react-router-dom";
import { G } from "../lib/design";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <>
      <style>{`
        @keyframes gradientShift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes float {
          0% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
          100% { transform: translateY(0px); }
        }
        @keyframes fadeInUp {
          0% { opacity: 0; transform: translateY(30px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulseGlow {
          0% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4); }
          70% { box-shadow: 0 0 0 20px rgba(79, 70, 229, 0); }
          100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
        }
        .hero-bg {
          background: linear-gradient(-45deg, #0f172a, #1e1b4b, #312e81, #1e1b4b);
          background-size: 400% 400%;
          animation: gradientShift 15s ease infinite;
        }
        .animate-fade-in {
          animation: fadeInUp 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          opacity: 0;
        }
        .delay-100 { animation-delay: 100ms; }
        .delay-200 { animation-delay: 200ms; }
        .delay-300 { animation-delay: 300ms; }
        .delay-400 { animation-delay: 400ms; }
        
        .feature-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-radius: 24px;
          padding: 40px;
          transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), background 0.3s, border 0.3s;
        }
        .feature-card:hover {
          transform: translateY(-8px);
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .btn-primary {
          background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
          color: white;
          padding: 16px 36px;
          border-radius: 30px;
          font-weight: 700;
          font-size: 16px;
          border: none;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 10px 25px rgba(79, 70, 229, 0.3);
          animation: pulseGlow 2s infinite;
        }
        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 15px 35px rgba(79, 70, 229, 0.4);
        }
        .btn-secondary {
          background: rgba(255, 255, 255, 0.1);
          color: white;
          padding: 16px 36px;
          border-radius: 30px;
          font-weight: 600;
          font-size: 16px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          cursor: pointer;
          backdrop-filter: blur(10px);
          transition: all 0.2s;
        }
        .btn-secondary:hover {
          background: rgba(255, 255, 255, 0.15);
          transform: translateY(-2px);
        }
        .glass-nav {
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
      `}</style>

      <div className="hero-bg" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", color: "white", fontFamily: "Inter, sans-serif" }}>
        {/* Navigation */}
        <nav className="glass-nav" style={{ padding: "20px 48px", display: "flex", justifyContent: "space-between", alignItems: "center", position: "fixed", top: 0, left: 0, right: 0, zIndex: 100 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: "36px", height: "36px", borderRadius: "10px",
              background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 4px 15px rgba(99, 102, 241, 0.4)"
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span style={{ fontSize: "20px", fontWeight: 800, letterSpacing: "-0.03em" }}>Lida AI</span>
          </div>
          <div style={{ display: "flex", gap: "16px" }}>
            <button onClick={() => navigate("/login")} style={{
              background: "transparent", color: "white", border: "none",
              fontSize: "15px", fontWeight: 600, cursor: "pointer",
              padding: "10px 20px"
            }}>Войти</button>
            <button onClick={() => navigate("/register")} style={{
              background: "white", color: "#0f172a", border: "none",
              fontSize: "15px", fontWeight: 700, cursor: "pointer",
              padding: "10px 24px", borderRadius: "20px",
              boxShadow: "0 4px 15px rgba(255, 255, 255, 0.15)",
              transition: "transform 0.2s"
            }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-2px)"}
               onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}>
              Начать бесплатно
            </button>
          </div>
        </nav>

        {/* Hero Section */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "140px 24px 80px", textAlign: "center", position: "relative" }}>
          
          <div style={{
            position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
            width: "800px", height: "800px", background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, rgba(0,0,0,0) 70%)",
            pointerEvents: "none", zIndex: 0
          }} />

          <div style={{ position: "relative", zIndex: 1, maxWidth: "900px" }}>
            <div className="animate-fade-in" style={{
              display: "inline-flex", alignItems: "center", gap: "8px",
              background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)",
              padding: "6px 16px", borderRadius: "30px", marginBottom: "32px",
              backdropFilter: "blur(10px)", color: "#a5b4fc", fontSize: "14px", fontWeight: 600
            }}>
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#4f46e5", boxShadow: "0 0 10px #4f46e5" }} />
              ИИ-Ассистент Отдела Продаж
            </div>
            
            <h1 className="animate-fade-in delay-100" style={{
              fontSize: "72px", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-0.03em",
              marginBottom: "32px", background: "linear-gradient(to right, #ffffff, #a5b4fc)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
            }}>
              Ваш ИИ-сотрудник<br/>для B2B продаж
            </h1>
            
            <p className="animate-fade-in delay-200" style={{
              fontSize: "22px", color: "rgba(255, 255, 255, 0.7)", lineHeight: 1.6,
              maxWidth: "680px", margin: "0 auto 48px", fontWeight: 400
            }}>
              Интегрируйте Лиду в вашу amoCRM или Битрикс24. Она обработает входящие лиды, соберет данные о компании и подготовит персонализированные ответы быстрее любого джуна.
            </p>
            
            <div className="animate-fade-in delay-300" style={{ display: "flex", gap: "20px", justifyContent: "center" }}>
              <button className="btn-primary" onClick={() => navigate("/register")}>
                Попробовать бесплатно
              </button>
              <button className="btn-secondary" onClick={() => navigate("/login")}>
                Авторизация
              </button>
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="animate-fade-in delay-400" style={{ padding: "80px 48px 120px", position: "relative", zIndex: 1 }}>
          <div style={{ maxWidth: "1200px", margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "32px" }}>
            
            <div className="feature-card">
              <div style={{ width: "56px", height: "56px", borderRadius: "16px", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "24px", color: "#818cf8" }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </div>
              <h3 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "16px", color: "white" }}>Интеграция с CRM</h3>
              <p style={{ color: "rgba(255, 255, 255, 0.6)", lineHeight: 1.6, fontSize: "16px" }}>
                Принимает лиды напрямую из amoCRM и Битрикс24 по вебхукам. Никакого ручного переноса баз — всё работает в привычном интерфейсе.
              </p>
            </div>

            <div className="feature-card">
              <div style={{ width: "56px", height: "56px", borderRadius: "16px", background: "rgba(236, 72, 153, 0.1)", border: "1px solid rgba(236, 72, 153, 0.2)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "24px", color: "#f472b6" }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
              </div>
              <h3 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "16px", color: "white" }}>Автономный ресерч</h3>
              <p style={{ color: "rgba(255, 255, 255, 0.6)", lineHeight: 1.6, fontSize: "16px" }}>
                Лида сама найдет сайт клиента, изучит стек технологий, вакансии и специфику бизнеса, чтобы составить идеальный ответ.
              </p>
            </div>

            <div className="feature-card">
              <div style={{ width: "56px", height: "56px", borderRadius: "16px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.2)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "24px", color: "#34d399" }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              </div>
              <h3 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "16px", color: "white" }}>Полный контроль</h3>
              <p style={{ color: "rgba(255, 255, 255, 0.6)", lineHeight: 1.6, fontSize: "16px" }}>
                Вы сами решаете, дать Лиде автопилот или утверждать каждый сгенерированный ответ через встроенный Kanban-дашборд.
              </p>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
