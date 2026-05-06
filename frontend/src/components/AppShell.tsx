import { Navigate, useLocation } from "react-router-dom";
import { useMe } from "../features/auth/hooks";
import AppLayout from "./AppLayout";

export default function AppShell() {
  const { data, isLoading } = useMe();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center", color: "#AAA", fontSize: "14px", fontFamily: "'Manrope', sans-serif" }}>
        Загрузка...
      </div>
    );
  }

  if (!data) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <AppLayout />;
}
