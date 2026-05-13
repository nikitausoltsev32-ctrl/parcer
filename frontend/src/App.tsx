import { Routes, Route, Navigate } from "react-router-dom";

import AppShell from "./components/AppShell";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import ContactsPage from "./pages/ContactsPage";
import CompaniesPage from "./pages/CompaniesPage";
import InboxPage from "./pages/InboxPage";
import CampaignsPage from "./pages/CampaignsPage";
import SettingsPage from "./pages/SettingsPage";
import TemplatesPage from "./pages/TemplatesPage";
import SmtpPage from "./pages/SmtpPage";
import ContactPage from "./pages/ContactPage";
import CompanyPage from "./pages/CompanyPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />

      <Route path="/app" element={<AppShell />}>
        <Route index element={<ChatPage />} />
        <Route path="contacts" element={<ContactsPage />} />
        <Route path="contacts/:id" element={<ContactPage />} />
        <Route path="companies" element={<CompaniesPage />} />
        <Route path="companies/:name" element={<CompanyPage />} />
        <Route path="inbox" element={<InboxPage />} />
        <Route path="campaigns" element={<CampaignsPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="smtp" element={<SmtpPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
