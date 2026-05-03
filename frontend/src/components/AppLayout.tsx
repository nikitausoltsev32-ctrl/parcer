import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useLogout, useMe } from "../features/auth/hooks";
import OnboardingModal from "./OnboardingModal";
import SetupWizard from "./SetupWizard";

const SAGE = "oklch(0.52 0.10 165)";

function LidaLogo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="52" height="52" rx="13" fill={SAGE} />
      <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
      <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
      <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}

const NAV_ITEMS = [
  {
    to: "/app",
    label: "Чат",
    end: true,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    to: "/app/companies",
    label: "Компании",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
        <line x1="12" y1="12" x2="12" y2="16" />
        <line x1="10" y1="14" x2="14" y2="14" />
      </svg>
    ),
  },
  {
    to: "/app/contacts",
    label: "Контакты",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    to: "/app/campaigns",
    label: "Кампании",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    to: "/app/inbox",
    label: "Входящие",
    badge: 3,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 13 16 13 14 16 10 16 8 13 2 13" />
        <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
      </svg>
    ),
  },
  {
    to: "/app/templates",
    label: "Шаблоны",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    to: "/app/smtp",
    label: "Почтовые ящики",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
        <polyline points="22,6 12,13 2,6" />
      </svg>
    ),
  },
];

export default function AppLayout() {
  const logout = useLogout();
  const { data: me } = useMe();
  const navigate = useNavigate();
  const [showTour, setShowTour] = useState(() => !localStorage.getItem("lida_onboarding_seen"));
  const [showWizard, setShowWizard] = useState(false);

  const initials = me?.full_name
    ? me.full_name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()
    : me?.email?.slice(0, 2).toUpperCase() ?? "??";
  const displayName = me?.full_name ?? me?.email ?? "Пользователь";

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", fontFamily: "'Manrope', sans-serif" }}>
      {showTour && (
        <OnboardingModal
          onDone={() => {
            setShowTour(false);
            if (!me?.business_profile?.business) setShowWizard(true);
          }}
          onRegister={() => navigate("/register")}
        />
      )}
      {!showTour && showWizard && (
        <SetupWizard onDone={() => setShowWizard(false)} />
      )}
      <aside style={{
        width: "200px",
        minWidth: "200px",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid rgba(0,0,0,0.08)",
        background: "#FAFAF9",
        userSelect: "none",
      }}>
        <div style={{
          padding: "20px 20px 16px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
          marginBottom: "8px",
        }}>
          <LidaLogo size={28} />
          <span style={{ fontSize: "15px", fontWeight: 600, color: "#1A1A1A", letterSpacing: "-0.3px" }}>Лида AI</span>
        </div>

        <nav style={{ flex: 1, padding: "4px 10px", display: "flex", flexDirection: "column", gap: "2px", overflowY: "auto" }}>
          {NAV_ITEMS.map(({ to, label, icon, badge, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 10px",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "13.5px",
                fontWeight: isActive ? 500 : 400,
                color: isActive ? SAGE : "#666",
                background: isActive ? `color-mix(in oklch, ${SAGE} 12%, transparent)` : "transparent",
                textDecoration: "none",
                transition: "background 0.1s, color 0.1s",
              })}
            >
              {({ isActive }) => (
                <>
                  <span style={{ opacity: isActive ? 1 : 0.7, color: isActive ? SAGE : "inherit", flexShrink: 0, display: "flex" }}>
                    {icon}
                  </span>
                  <span style={{ flex: 1 }}>{label}</span>
                  {badge && (
                    <span style={{
                      background: "#E53E3E",
                      color: "white",
                      borderRadius: "10px",
                      fontSize: "11px",
                      fontWeight: 600,
                      padding: "1px 6px",
                      lineHeight: "16px",
                    }}>{badge}</span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: "12px 10px", borderTop: "1px solid rgba(0,0,0,0.06)" }}>
          <NavLink
            to="/app/settings"
            style={({ isActive }) => ({
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "8px 10px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13.5px",
              fontWeight: isActive ? 500 : 400,
              color: isActive ? SAGE : "#999",
              background: isActive ? `color-mix(in oklch, ${SAGE} 12%, transparent)` : "transparent",
              textDecoration: "none",
              transition: "background 0.1s, color 0.1s",
            })}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Настройки
          </NavLink>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "8px 10px", marginTop: "4px" }}>
            <div style={{
              width: "28px", height: "28px", borderRadius: "50%",
              background: "#E5E5E5",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "12px", fontWeight: 600, color: "#555", flexShrink: 0,
            }}>{initials}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "12.5px", fontWeight: 500, color: "#333", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{displayName}</div>
            </div>
            <button
              onClick={() => logout.mutate()}
              title="Выйти"
              style={{ background: "none", border: "none", cursor: "pointer", color: "#CCC", padding: "2px", display: "flex", flexShrink: 0 }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      <main style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        <Outlet />
      </main>
    </div>
  );
}
