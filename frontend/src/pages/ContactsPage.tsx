import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LeadSearchPanel } from "../components/LeadSearchPanel";
import { SearchHistoryPanel } from "../components/SearchHistoryPanel";
import { api } from "../lib/api";
import { G, SOURCE_BADGE, STATUS_BADGE } from "../lib/design";

interface Contact {
  id: string;
  full_name: string;
  company_name: string | null;
  status: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  website: string | null;
  city: string | null;
  industry: string | null;
  enrichment_summary: string | null;
  lead_score: number | null;
  confidence: string | null;
}

interface ImportPreview {
  file_name: string;
  file_type: string;
  file_url: string | null;
  columns_detected: Record<string, string>;
  preview: Array<Record<string, string | null>>;
  stats: {
    rows_total: number;
    valid_rows: number;
    skipped_rows: number;
    duplicate_emails: number;
    remaining_contacts: number | null;
    trial_limit: number;
    would_exceed_trial: boolean;
  };
  message?: string;
}

function StatusBadge({ status }: { status: string | null }) {
  const key = (status ?? "new").toLowerCase();
  const c = STATUS_BADGE[key] ?? STATUS_BADGE["new"] ?? { bg: G.greenBg, text: G.green, border: "rgba(45,122,95,0.25)" };
  const label = status ?? "Новый";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 9px", borderRadius: "6px",
      fontSize: "11.5px", fontWeight: 500,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>{label}</span>
  );
}

function SourceBadge({ source }: { source: string | null }) {
  const key = source ?? "manual";
  const c = SOURCE_BADGE[key] ?? SOURCE_BADGE["manual"] ?? { bg: "rgba(26,37,64,0.07)", text: "#4a5568", border: "rgba(26,37,64,0.15)" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "1px 7px", borderRadius: "20px",
      fontSize: "11px", fontWeight: 600,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>{source ?? "manual"}</span>
  );
}

const thS: React.CSSProperties = {
  padding: "10px 16px", textAlign: "left",
  fontSize: "10.5px", fontWeight: 700,
  color: G.textMuted, textTransform: "uppercase",
  letterSpacing: "0.07em",
  background: "rgba(255,255,255,0.25)",
  borderBottom: G.borderSubtle, whiteSpace: "nowrap",
};
const tdS: React.CSSProperties = {
  padding: "11px 16px", fontSize: "13px",
  color: G.textPrimary, borderBottom: G.borderSubtle,
  whiteSpace: "nowrap", overflow: "hidden",
  textOverflow: "ellipsis", maxWidth: "200px",
};

function importErrorMessage(err: unknown): string {
  const response = (err as { response?: { data?: { detail?: unknown } } }).response;
  const detail = response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return "Import failed";
}

interface ContactList {
  id: string;
  name: string;
  source: string | null;
  total_count: number;
}

function scoreColor(score: number | null): string {
  if (score === null) return G.textMuted;
  if (score >= 75) return G.green;
  if (score >= 50) return "#d97706";
  return G.textMuted;
}

export default function ContactsPage() {
  const [search, setSearch] = useState("");
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedListId, setSelectedListId] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: () => api.get("/contacts?limit=100").then((r) => r.data),
  });

  const { data: contactLists = [] } = useQuery<ContactList[]>({
    queryKey: ["contact-lists"],
    queryFn: () => api.get("/contact-lists").then((r) => r.data),
    retry: false,
  });

  const deleteListMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/contact-lists/${id}`),
    onSuccess: () => {
      setSelectedListId("");
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      queryClient.invalidateQueries({ queryKey: ["contact-lists"] });
    },
  });

  function handleDeleteList() {
    if (!selectedListId) return;
    const list = contactLists.find((l) => l.id === selectedListId);
    if (!list) return;
    if (!window.confirm(`Удалить список «${list.name}» и все его контакты?`)) return;
    deleteListMutation.mutate(selectedListId);
  }

  const previewMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/contacts/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data as ImportPreview;
    },
    onSuccess: (data) => {
      setPreview(data);
      setImportStatus(`Preview: ${data.stats.valid_rows} contacts detected.${data.stats.would_exceed_trial ? " Trial limit exceeded." : ""}`);
    },
    onError: (err: unknown) => {
      setImportStatus(`Error: ${importErrorMessage(err)}`);
      setTimeout(() => setImportStatus(null), 5000);
    },
  });

  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const listName = file.name.replace(/\.(csv|tsv|xlsx)$/i, "");
      const { data } = await api.post(`/contacts/import?confirmed=true&list_name=${encodeURIComponent(listName)}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      setPreview(null);
      setPendingFile(null);
      setImportStatus(`Imported ${data.saved} contacts into "${data.list_name}"`);
      setTimeout(() => setImportStatus(null), 4000);
    },
    onError: (err: unknown) => {
      setImportStatus(`Error: ${importErrorMessage(err)}`);
      setTimeout(() => setImportStatus(null), 5000);
    },
  });

  function selectImportFile(file: File) {
    setPendingFile(file);
    setPreview(null);
    previewMutation.mutate(file);
  }

  const filtered = search
    ? contacts.filter((c) =>
        (c.full_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
        (c.company_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : contacts;

  const isError = importStatus?.startsWith("Error");

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        height: "52px", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px",
        background: "rgba(255,255,255,0.45)",
        backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Контакты</span>
          <span style={{ fontSize: "13px", color: G.textMuted }}>{contacts.length} записей</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {/* Search */}
          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "0 12px", borderRadius: G.radiusSm, height: "34px",
            background: "rgba(255,255,255,0.60)",
            backdropFilter: "blur(8px)",
            border: G.border,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск..."
              style={{
                border: "none", outline: "none", background: "transparent",
                fontSize: "13px", color: G.textPrimary, fontFamily: "inherit", width: "160px",
              }}
            />
          </div>

          {contactLists.length > 0 && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <select
                value={selectedListId}
                onChange={(e) => setSelectedListId(e.target.value)}
                style={{
                  height: "34px", padding: "0 10px", borderRadius: G.radiusSm,
                  border: G.border, background: "rgba(255,255,255,0.60)",
                  color: G.textSecondary, fontSize: "12.5px", fontFamily: "inherit",
                  outline: "none", cursor: "pointer",
                }}
              >
                <option value="">Выбрать список…</option>
                {contactLists.map((l) => (
                  <option key={l.id} value={l.id}>{l.name} ({l.total_count})</option>
                ))}
              </select>
              <button
                onClick={handleDeleteList}
                disabled={!selectedListId || deleteListMutation.isPending}
                title="Удалить список"
                style={{
                  height: "34px", padding: "0 12px", borderRadius: G.radiusSm,
                  border: `1px solid rgba(192,57,43,0.30)`,
                  background: selectedListId ? G.redBg : "rgba(255,255,255,0.40)",
                  color: selectedListId ? G.red : G.textMuted,
                  fontSize: "12.5px", fontWeight: 500, fontFamily: "inherit",
                  cursor: selectedListId && !deleteListMutation.isPending ? "pointer" : "not-allowed",
                }}
              >
                {deleteListMutation.isPending ? "…" : "Удалить"}
              </button>
            </div>
          )}

          <input ref={fileInputRef} type="file" accept=".csv,.tsv,.xlsx" style={{ display: "none" }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) selectImportFile(f); e.target.value = ""; }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={previewMutation.isPending || importMutation.isPending}
            style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "0 14px", height: "34px", borderRadius: G.radiusSm,
              background: G.navy, color: "white",
              border: "none", fontSize: "13px", fontWeight: 600,
              cursor: previewMutation.isPending || importMutation.isPending ? "not-allowed" : "pointer",
              fontFamily: "inherit", opacity: previewMutation.isPending || importMutation.isPending ? 0.7 : 1,
              boxShadow: G.shadowBtn, transition: "opacity 0.15s",
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            {previewMutation.isPending ? "Reading..." : "Import CSV/XLSX"}
          </button>
        </div>
      </div>

      {/* Import status banner */}
      {importStatus && (
        <div style={{
          padding: "9px 24px", fontSize: "13px", flexShrink: 0,
          background: isError ? G.redBg : G.greenBg,
          color: isError ? G.red : G.green,
          borderBottom: `1px solid ${isError ? "rgba(192,57,43,0.25)" : "rgba(45,122,95,0.25)"}`,
        }}>
          {importStatus}
        </div>
      )}

      <LeadSearchPanel />
      <SearchHistoryPanel />

      {preview && (
        <div style={{
          margin: "14px 24px 0",
          padding: "14px",
          borderRadius: G.radius,
          border: preview.stats.would_exceed_trial ? `1px solid rgba(192,57,43,0.30)` : G.border,
          background: preview.stats.would_exceed_trial ? G.redBg : "rgba(255,255,255,0.50)",
          boxShadow: G.shadowCard,
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "10px" }}>
            <div>
              <div style={{ fontSize: "13.5px", fontWeight: 700, color: G.textPrimary }}>{preview.file_name}</div>
              <div style={{ fontSize: "12px", color: G.textMuted }}>
                {preview.stats.valid_rows} valid rows, {preview.stats.skipped_rows} skipped, {preview.stats.duplicate_emails} duplicate emails
              </div>
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <button
                onClick={() => { setPreview(null); setPendingFile(null); }}
                style={{
                  height: "32px", padding: "0 12px", borderRadius: G.radiusSm,
                  border: G.border, background: "rgba(255,255,255,0.60)",
                  color: G.textSecondary, fontSize: "12.5px", fontFamily: "inherit", cursor: "pointer",
                }}
              >Cancel</button>
              <button
                onClick={() => pendingFile && importMutation.mutate(pendingFile)}
                disabled={!pendingFile || importMutation.isPending || preview.stats.would_exceed_trial}
                style={{
                  height: "32px", padding: "0 12px", borderRadius: G.radiusSm,
                  border: "none",
                  background: preview.stats.would_exceed_trial ? "rgba(26,37,64,0.10)" : G.navy,
                  color: preview.stats.would_exceed_trial ? G.textMuted : "white",
                  fontSize: "12.5px", fontWeight: 600, fontFamily: "inherit",
                  cursor: !pendingFile || importMutation.isPending || preview.stats.would_exceed_trial ? "not-allowed" : "pointer",
                  boxShadow: preview.stats.would_exceed_trial ? "none" : G.shadowBtn,
                }}
              >{importMutation.isPending ? "Importing..." : "Confirm import"}</button>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>{["name", "email", "company", "phone", "city"].map((col) => <th key={col} style={thS}>{col}</th>)}</tr>
              </thead>
              <tbody>
                {preview.preview.map((row, index) => (
                  <tr key={index}>
                    {["name", "email", "company", "phone", "city"].map((col) => (
                      <td key={col} style={tdS}>{row[col] || <span style={{ color: G.textMuted }}>-</span>}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Content */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) selectImportFile(file);
        }}
        style={{
          flex: 1,
          overflow: "auto",
          padding: "20px 24px",
          outline: dragOver ? `2px dashed ${G.navyLight}` : "none",
          outlineOffset: "-10px",
        }}
      >
        {isLoading ? (
          <div style={{ color: G.textMuted, fontSize: "13px", padding: "48px 0", textAlign: "center" }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "80px", gap: "10px" }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4 }}>
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <div style={{ fontSize: "14.5px", fontWeight: 600, color: G.textPrimary }}>Нет контактов</div>
            <div style={{ fontSize: "13px", color: G.textMuted }}>Добавьте через чат с Лидой или импортируйте CSV</div>
          </div>
        ) : (
          <div style={{
            borderRadius: G.radius, border: G.border, overflow: "hidden",
            background: "rgba(255,255,255,0.45)",
            backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
            boxShadow: G.shadowCard,
          }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Имя", "Компания", "Статус", "Email", "Телефон", "Источник", "Score"].map((col) => (
                    <th key={col} style={thS}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr
                    key={c.id}
                    style={{ cursor: "pointer", transition: "background 0.1s" }}
                    onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.55)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "transparent"}
                  >
                    <td style={{ ...tdS, fontWeight: 600 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                        <div style={{
                          width: "28px", height: "28px", borderRadius: "50%",
                          background: G.navy, flexShrink: 0,
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: "10.5px", fontWeight: 700, color: "rgba(255,255,255,0.85)",
                          border: "2px solid rgba(255,255,255,0.55)",
                          boxShadow: "0 1px 4px rgba(26,37,64,0.18)",
                        }}>
                          {(c.full_name ?? "?").split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                        </div>
                        {c.full_name ?? "—"}
                      </div>
                    </td>
                    <td style={{ ...tdS, color: G.textSecondary }}>{c.company_name ?? <span style={{ color: G.textMuted }}>—</span>}</td>
                    <td style={tdS}><StatusBadge status={c.status} /></td>
                    <td style={tdS}>
                      {c.email
                        ? <span style={{ color: G.navyLight }}>{c.email}</span>
                        : <span style={{ color: G.textMuted }}>—</span>}
                    </td>
                    <td style={{ ...tdS, color: G.textSecondary }}>{c.phone ?? <span style={{ color: G.textMuted }}>—</span>}</td>
                    <td style={tdS}><SourceBadge source={c.source} /></td>
                    <td
                      style={{ ...tdS, color: scoreColor(c.lead_score), fontWeight: 600, fontVariantNumeric: "tabular-nums" }}
                      title={c.confidence ?? undefined}
                    >
                      {c.lead_score !== null ? c.lead_score : <span style={{ color: G.textMuted, fontWeight: 400 }}>—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
