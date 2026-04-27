import { NavLink, Outlet } from "react-router-dom";
import {
  MessageSquare,
  Users,
  Building2,
  Mail,
  Megaphone,
  Settings,
  LogOut,
} from "lucide-react";
import { useLogout } from "../features/auth/hooks";

const NAV = [
  { to: "/app", label: "Чат", icon: MessageSquare, end: true },
  { to: "/app/contacts", label: "Клиенты", icon: Users },
  { to: "/app/companies", label: "Компании", icon: Building2 },
  { to: "/app/inbox", label: "Входящие", icon: Mail },
  { to: "/app/campaigns", label: "Кампании", icon: Megaphone },
  { to: "/app/settings", label: "Настройки", icon: Settings },
];

export default function AppLayout() {
  const logout = useLogout();

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex w-56 flex-col border-r bg-muted/40">
        <div className="px-5 py-4 text-lg font-semibold tracking-tight">parcer</div>
        <nav className="flex-1 space-y-0.5 px-2">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2">
          <button
            onClick={() => logout.mutate()}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <LogOut size={16} />
            Выйти
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
