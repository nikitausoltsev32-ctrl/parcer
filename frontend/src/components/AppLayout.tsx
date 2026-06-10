import { useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useLogout, useMe } from "../features/auth/hooks";
import OnboardingModal, { type OnboardingAnswers } from "./OnboardingModal";
import SetupWizard from "./SetupWizard";
import { G } from "../lib/design";

function LidaLogo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none">
      <rect width="52" height="52" rx="13" fill={G.navy} />
      <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
      <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
      <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: "/app", end: true, label: "Чат", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> },
  { to: "/app/contacts", label: "Контакты", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg> },
  { to: "/app/kanban", label: "Канбан", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg> },
  { to: "/app/campaigns", label: "Кампании", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> },
  { to: "/app/inbox", label: "Входящие", badge: true, icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 13 16 13 14 16 10 16 8 13 2 13"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg> },
  { to: "/app/templates", label: "Шаблоны", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> },
  { to: "/app/smtp", label: "Почта", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg> },
];

// Bottom nav shows only top 5 items on mobile
const BOTTOM_NAV_ITEMS = NAV_ITEMS.slice(0, 5);

export default function AppLayout() {
  const logout = useLogout();
  const { data: me } = useMe();
  const [expanded, setExpanded] = useState(false);
  const [showTour, setShowTour] = useState(() => !localStorage.getItem("lida_onboarding_seen"));
  const [showWizard, setShowWizard] = useState(false);
  const [tourAnswers, setTourAnswers] = useState<OnboardingAnswers | undefined>();
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 640);

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  const initials = me?.full_name
    ? me.full_name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()
    : me?.email?.slice(0, 2).toUpperCase() ?? "??";
  const displayName = me?.full_name ?? me?.email ?? "Пользователь";

  const W = expanded ? 200 : 64;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", fontFamily: "'Manrope', sans-serif" }}>
      {showTour && (
        <OnboardingModal
          onDone={(answers) => {
            setTourAnswers(answers);
            setShowTour(false);
            if (!me?.business_profile?.business) setShowWizard(true);
          }}
        />
      )}
      {!showTour && showWizard && (
        <SetupWizard
          initialBusiness={tourAnswers?.industry}
          initialCity={tourAnswers?.geo}
          onDone={() => setShowWizard(false)}
        />
      )}

      {/* Desktop Sidebar */}
      {!isMobile && (
        <aside
          onMouseEnter={() => setExpanded(true)}
          onMouseLeave={() => setExpanded(false)}
          style={{
            width: `${W}px`,
            minWidth: `${W}px`,
            height: "100vh",
            display: "flex",
            flexDirection: "column",
            padding: "12px 0",
            background: G.glassSidebar,
            backdropFilter: G.blur,
            WebkitBackdropFilter: G.blur,
            borderRight: G.borderSubtle,
            boxShadow: expanded ? "4px 0 32px rgba(20,40,80,0.14)" : "2px 0 24px rgba(20,40,80,0.08)",
            zIndex: 20,
            userSelect: "none",
            overflow: "hidden",
            transition: "width 0.22s cubic-bezier(0.16,1,0.3,1), min-width 0.22s cubic-bezier(0.16,1,0.3,1), box-shadow 0.2s",
            position: "relative",
          }}
        >
          {/* Logo */}
          <div style={{ padding: "2px 0 0 14px", marginBottom: "20px", display: "flex", alignItems: "center", gap: "10px", overflow: "hidden" }}>
            <div style={{ flexShrink: 0 }}><LidaLogo size={36} /></div>
            <span style={{
              fontSize: "15px", fontWeight: 700, color: G.textPrimary,
              letterSpacing: "-0.3px", whiteSpace: "nowrap",
              opacity: expanded ? 1 : 0,
              transform: expanded ? "translateX(0)" : "translateX(-8px)",
              transition: "opacity 0.18s 0.05s, transform 0.18s 0.05s",
            }}>Лида</span>
          </div>

          <div style={{ width: "32px", height: "1px", background: "rgba(26,37,64,0.12)", marginBottom: "10px", alignSelf: "center" }} />

          {/* Nav */}
          <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: "3px", padding: "0 10px" }}>
            {NAV_ITEMS.map(({ to, label, icon, badge, end }) => (
              <NavLink key={to} to={to} end={end as boolean | undefined} style={{ textDecoration: "none" }}>
                {({ isActive }) => (
                  <div
                    style={{
                      height: "44px", borderRadius: "12px",
                      display: "flex", alignItems: "center", gap: "10px",
                      padding: "0 12px", cursor: "pointer",
                      background: isActive ? G.navy : "transparent",
                      color: isActive ? "white" : G.textSecondary,
                      boxShadow: isActive ? G.shadowBtn : "none",
                      transition: "background 0.15s, color 0.15s",
                      overflow: "hidden", whiteSpace: "nowrap", flexShrink: 0,
                      position: "relative",
                    }}
                    onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "rgba(26,37,64,0.07)"; }}
                    onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", width: "20px" }}>{icon}</div>
                    {badge && !expanded && (
                      <div style={{ position: "absolute", top: "8px", right: "8px", width: "8px", height: "8px", borderRadius: "50%", background: "#e53e3e", border: "1.5px solid rgba(220,230,240,0.8)" }} />
                    )}
                    <span style={{
                      fontSize: "13.5px", fontWeight: isActive ? 600 : 400,
                      opacity: expanded ? 1 : 0,
                      transform: expanded ? "translateX(0)" : "translateX(-6px)",
                      transition: "opacity 0.16s 0.04s, transform 0.16s 0.04s",
                      flex: 1,
                    }}>{label}</span>
                    {badge && expanded && (
                      <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#e53e3e", flexShrink: 0, opacity: expanded ? 1 : 0, transition: "opacity 0.16s" }} />
                    )}
                  </div>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Bottom */}
          <div style={{ display: "flex", flexDirection: "column", gap: "3px", padding: "0 10px" }}>
            <div style={{ width: "32px", height: "1px", background: "rgba(26,37,64,0.10)", marginBottom: "6px", alignSelf: "center" }} />
            <NavLink to="/app/settings" style={{ textDecoration: "none" }}>
              {({ isActive }) => (
                <div
                  style={{
                    height: "44px", borderRadius: "12px",
                    display: "flex", alignItems: "center", gap: "10px",
                    padding: "0 12px", cursor: "pointer",
                    background: isActive ? G.navy : "transparent",
                    color: isActive ? "white" : G.textMuted,
                    transition: "background 0.15s, color 0.15s",
                    overflow: "hidden", whiteSpace: "nowrap",
                  }}
                  onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "rgba(26,37,64,0.07)"; }}
                  onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                >
                  <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", width: "20px" }}>
                    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="3"/>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                  </div>
                  <span style={{ fontSize: "13.5px", opacity: expanded ? 1 : 0, transform: expanded ? "translateX(0)" : "translateX(-6px)", transition: "opacity 0.16s 0.04s, transform 0.16s 0.04s" }}>Настройки</span>
                </div>
              )}
            </NavLink>

            {/* Avatar */}
            <div
              style={{ height: "44px", borderRadius: "12px", display: "flex", alignItems: "center", gap: "10px", padding: "0 12px", cursor: "pointer", overflow: "hidden", whiteSpace: "nowrap", transition: "background 0.15s", marginTop: "2px" }}
              onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(26,37,64,0.07)"}
              onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "transparent"}
            >
              <div style={{
                width: "28px", height: "28px", borderRadius: "50%",
                background: G.navy, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "10px", fontWeight: 700, color: "rgba(255,255,255,0.85)",
                border: "2px solid rgba(255,255,255,0.5)",
              }}>{initials}</div>
              <div style={{ opacity: expanded ? 1 : 0, transform: expanded ? "translateX(0)" : "translateX(-6px)", transition: "opacity 0.16s 0.04s, transform 0.16s 0.04s", minWidth: 0 }}>
                <div style={{ fontSize: "12.5px", fontWeight: 500, color: G.textPrimary, overflow: "hidden", textOverflow: "ellipsis" }}>{displayName}</div>
                <div style={{ fontSize: "11px", color: G.textMuted, cursor: "pointer" }} onClick={() => logout.mutate()}>Выйти</div>
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* Main content */}
      <main style={{
        flex: 1, overflow: "hidden", display: "flex", flexDirection: "column",
        paddingBottom: isMobile ? "56px" : "0",
      }}>
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      {isMobile && (
        <nav style={{
          position: "fixed", bottom: 0, left: 0, right: 0,
          height: "56px",
          display: "flex", alignItems: "stretch",
          background: "rgba(255,255,255,0.88)",
          backdropFilter: "blur(20px) saturate(1.6)",
          WebkitBackdropFilter: "blur(20px) saturate(1.6)",
          borderTop: "1px solid rgba(255,255,255,0.60)",
          boxShadow: "0 -2px 16px rgba(20,40,80,0.10)",
          zIndex: 50,
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
        }}>
          {BOTTOM_NAV_ITEMS.map(({ to, label, icon, badge, end }) => (
            <NavLink key={to} to={to} end={end as boolean | undefined} style={{ flex: 1, textDecoration: "none" }}>
              {({ isActive }) => (
                <div style={{
                  flex: 1, height: "100%",
                  display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", gap: "3px",
                  color: isActive ? G.navy : G.textMuted,
                  cursor: "pointer", position: "relative",
                  transition: "color 0.15s",
                }}>
                  <div style={{ position: "relative" }}>
                    {icon}
                    {badge && (
                      <div style={{ position: "absolute", top: "-3px", right: "-3px", width: "7px", height: "7px", borderRadius: "50%", background: "#e53e3e", border: "1.5px solid white" }} />
                    )}
                  </div>
                  <span style={{ fontSize: "9.5px", fontWeight: isActive ? 700 : 400, lineHeight: 1 }}>{label}</span>
                  {isActive && (
                    <div style={{ position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)", width: "24px", height: "2px", background: G.navy, borderRadius: "0 0 2px 2px" }} />
                  )}
                </div>
              )}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
