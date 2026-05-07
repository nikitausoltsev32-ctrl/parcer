import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { getToken } from "../lib/auth";
import { streamSSE } from "../lib/sse";
import { G, SOURCE_BADGE } from "../lib/design";

interface ChatModel {
  id: string;
  label: string;
  sub: string;
}

const DEFAULT_MODELS: ChatModel[] = [
  { id: "groq/llama-3.3-70b-versatile", label: "Llama 3.3", sub: "Groq" },
  { id: "openrouter/minimax/minimax-m2.5:free", label: "MiniMax M2", sub: "OpenRouter" },
];

interface ToolStep {
  id: string;
  label: string;
  done: boolean;
  warning?: boolean;
}

interface Company {
  id: number | string;
  name: string;
  website?: string;
  summary?: string | null;
  website_summary?: string | null;
  description?: string | null;
  city?: string;
  address?: string | null;
  industry?: string;
  source?: string;
  email?: string | null;
  phone?: string | null;
  confidence?: string;
}

interface ImportToolResult {
  status: string;
  file_name?: string;
  file_url?: string | null;
  list_name?: string;
  saved?: number;
  preview?: Array<Record<string, string | null>>;
  stats?: {
    valid_rows: number;
    skipped_rows: number;
    duplicate_emails: number;
    would_exceed_trial: boolean;
    remaining_contacts: number | null;
  };
  error?: string;
  message?: string;
}

interface Msg {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolSteps: ToolStep[];
  companies?: Company[];
  importResult?: ImportToolResult;
  pending?: boolean;
}

interface Tab {
  id: number;
  title: string;
  sessionId: string | null;
  messages: Msg[];
}

// ── Source badge ──────────────────────────────────────────────
function SourceBadge({ source }: { source?: string }) {
  if (!source) return null;
  const s = SOURCE_BADGE[source] ?? { bg: "rgba(26,37,64,0.07)", text: "#4a5568", border: "rgba(26,37,64,0.15)" };
  return (
    <span style={{
      fontSize: "10.5px", fontWeight: 600,
      padding: "2px 7px", borderRadius: "20px",
      background: s.bg, color: s.text,
      border: `1px solid ${s.border}`,
      whiteSpace: "nowrap",
    }}>{source}</span>
  );
}

// ── Confidence badge ──────────────────────────────────────────
function ConfidenceBadge({ state }: { state?: string }) {
  const map: Record<string, { label: string; color: string; bg: string; border: string }> = {
    verified: { label: "Verified", color: G.green, bg: G.greenBg, border: "rgba(45,122,95,0.25)" },
    inferred: { label: "Inferred", color: G.amber, bg: G.amberBg, border: "rgba(176,125,42,0.25)" },
    failed:   { label: "Failed",   color: G.red,   bg: G.redBg,   border: "rgba(192,57,43,0.25)"  },
  };
  const c = map[state ?? ""] ?? { label: state ?? "—", color: G.textMuted, bg: "rgba(26,37,64,0.06)", border: "rgba(26,37,64,0.12)" };
  return (
    <span style={{
      fontSize: "10.5px", fontWeight: 600,
      padding: "2px 7px", borderRadius: "20px",
      background: c.bg, color: c.color,
      border: `1px solid ${c.border}`,
      whiteSpace: "nowrap",
    }}>{c.label}</span>
  );
}

// ── Tool run status ───────────────────────────────────────────
function ToolRunStatus({ steps }: { steps: ToolStep[] }) {
  const [expanded, setExpanded] = useState(false);
  const allDone = steps.every((s) => s.done);

  return (
    <div style={{
      borderRadius: G.radius,
      border: G.borderSubtle,
      overflow: "hidden",
      marginBottom: "6px",
      background: "rgba(255,255,255,0.35)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
    }}>
      <div
        onClick={() => setExpanded((e) => !e)}
        style={{ display: "flex", alignItems: "center", gap: "9px", padding: "10px 14px", cursor: "pointer", userSelect: "none" }}
      >
        {allDone ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={G.green} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <div style={{ width: "14px", height: "14px", borderRadius: "50%", border: `2px solid ${G.navyLight}`, borderTopColor: "transparent", animation: "spin 0.8s linear infinite" }} />
        )}
        <span style={{ fontSize: "12.5px", color: G.textSecondary, flex: 1 }}>
          {allDone ? `Выполнено ${steps.length} ${steps.length === 1 ? "шаг" : steps.length < 5 ? "шага" : "шагов"}` : "Лида работает…"}
        </span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={G.textMuted} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
      {expanded && (
        <div style={{
          borderTop: G.borderSubtle, padding: "10px 14px 12px",
          display: "flex", flexDirection: "column", gap: "7px",
          background: "rgba(255,255,255,0.15)",
        }}>
          {steps.map((step) => (
            <div key={step.id} style={{ display: "flex", alignItems: "flex-start", gap: "9px" }}>
              <div style={{ marginTop: "1px", flexShrink: 0 }}>
                {step.warning ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={G.amber} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                ) : (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={G.green} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </div>
              <span style={{ fontSize: "12px", color: step.warning ? G.amber : G.textSecondary, lineHeight: "1.45" }}>{step.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Lead results card ─────────────────────────────────────────
const thS: React.CSSProperties = {
  padding: "9px 14px", textAlign: "left",
  fontSize: "10.5px", fontWeight: 700,
  color: G.textMuted, textTransform: "uppercase",
  letterSpacing: "0.07em", borderBottom: G.borderSubtle,
  whiteSpace: "nowrap",
};
const tdS: React.CSSProperties = {
  padding: "10px 14px", fontSize: "12.5px",
  color: G.textPrimary, borderBottom: G.borderSubtle,
  whiteSpace: "nowrap", overflow: "hidden",
  textOverflow: "ellipsis", maxWidth: "180px",
};

function LeadResultsCard({ companies, onSaveRequest }: { companies: Company[]; onSaveRequest: () => void }) {
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set());
  const [hovRow, setHovRow] = useState<string | number | null>(null);

  function toggle(id: string | number, e: React.MouseEvent) {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  const sources = [...new Set(companies.map((c) => c.source).filter(Boolean))] as string[];

  return (
    <div style={{
      borderRadius: G.radius,
      border: G.border,
      overflow: "hidden",
      background: "rgba(255,255,255,0.45)",
      backdropFilter: G.blur,
      WebkitBackdropFilter: G.blur,
      boxShadow: G.shadowCard,
      marginBottom: "4px",
    }}>
      {/* Header */}
      <div style={{
        padding: "12px 16px",
        background: "rgba(255,255,255,0.35)",
        borderBottom: G.borderSubtle,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "13.5px", fontWeight: 700, color: G.textPrimary }}>Найденные компании</span>
          <span style={{
            fontSize: "11px", fontWeight: 600,
            background: "rgba(26,37,64,0.08)", color: G.textSecondary,
            padding: "1px 8px", borderRadius: "20px",
          }}>{companies.length}</span>
        </div>
        <div style={{ display: "flex", gap: "5px" }}>
          {sources.map((s) => <SourceBadge key={s} source={s} />)}
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "rgba(255,255,255,0.25)" }}>
              <th style={thS}></th>
              <th style={thS}>Компания</th>
              <th style={{ ...thS, minWidth: "260px" }}>Описание</th>
              <th style={thS}>Сайт</th>
              <th style={thS}>Город / адрес</th>
              <th style={thS}>Телефон</th>
              <th style={thS}>Email</th>
              <th style={thS}>Источник</th>
              <th style={thS}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((c) => {
              const sel = selectedIds.has(c.id);
              const hov = hovRow === c.id;
              const summary = c.summary ?? c.description ?? c.website_summary ?? c.industry ?? "";
              const location = [c.city, c.address].filter(Boolean).join(" / ");
              return (
                <tr
                  key={c.id}
                  onMouseEnter={() => setHovRow(c.id)}
                  onMouseLeave={() => setHovRow(null)}
                  style={{ background: sel ? "rgba(26,37,64,0.08)" : hov ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.35)", transition: "background 0.1s" }}
                >
                  <td style={{ ...tdS, width: "36px", paddingLeft: "14px" }}>
                    <div
                      onClick={(e) => toggle(c.id, e)}
                      style={{
                        width: "15px", height: "15px", borderRadius: "4px",
                        border: `1.5px solid ${sel ? G.navy : "rgba(26,37,64,0.25)"}`,
                        background: sel ? G.navy : "transparent",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        cursor: "pointer", flexShrink: 0,
                      }}
                    >
                      {sel && <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>}
                    </div>
                  </td>
                  <td style={{ ...tdS, fontWeight: 600, color: G.textPrimary }}>{c.name}</td>
                  <td style={{
                    ...tdS,
                    minWidth: "260px",
                    maxWidth: "340px",
                    whiteSpace: "normal",
                    lineHeight: "1.42",
                    color: summary ? G.textSecondary : G.textMuted,
                  }}>
                    {summary || "—"}
                  </td>
                  <td style={tdS}>
                    {c.website
                      ? <a href="#" onClick={(e) => e.preventDefault()} style={{ color: G.navyLight, textDecoration: "none", fontSize: "12.5px" }}>{c.website}</a>
                      : <span style={{ color: G.textMuted }}>—</span>}
                  </td>
                  <td style={{ ...tdS, color: location ? G.textSecondary : G.textMuted }}>{location || "—"}</td>
                  <td style={tdS}>
                    {c.phone
                      ? <span style={{ color: G.textSecondary, fontSize: "12.5px" }}>{c.phone}</span>
                      : <span style={{ color: G.textMuted }}>—</span>}
                  </td>
                  <td style={tdS}>
                    {c.email
                      ? <span style={{ color: G.navyLight, fontSize: "12.5px" }}>{c.email}</span>
                      : <span style={{ color: G.textMuted }}>—</span>}
                  </td>
                  <td style={tdS}><SourceBadge source={c.source} /></td>
                  <td style={tdS}><ConfidenceBadge state={c.confidence} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Action bar */}
      <div style={{
        padding: "10px 16px", borderTop: G.borderSubtle,
        background: "rgba(255,255,255,0.30)",
        display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap",
      }}>
        {selectedIds.size > 0 && (
          <span style={{ fontSize: "12px", color: G.textMuted, marginRight: "4px" }}>Выбрано: {selectedIds.size}</span>
        )}
        <button
          onClick={onSaveRequest}
          style={{
            display: "flex", alignItems: "center", gap: "6px",
            padding: "6px 12px", borderRadius: G.radiusSm,
            background: G.navy,
            color: "white",
            border: "none",
            fontSize: "12.5px", fontWeight: 600,
            cursor: "pointer", fontFamily: "inherit",
            boxShadow: G.shadowBtn,
            transition: "all 0.15s",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          Сохранить через чат
        </button>
        {[
          { label: "Обогатить", icon: <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> },
          { label: "Создать кампанию", icon: <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> },
        ].map(({ label, icon }) => (
          <button key={label} style={{
            display: "flex", alignItems: "center", gap: "6px",
            padding: "6px 12px", borderRadius: G.radiusSm,
            background: "rgba(255,255,255,0.60)",
            backdropFilter: "blur(8px)",
            color: G.textSecondary, border: G.border,
            fontSize: "12.5px", fontWeight: 500,
            cursor: "pointer", fontFamily: "inherit",
            transition: "background 0.12s",
          }}
            onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.85)"}
            onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.60)"}
          >{icon}{label}</button>
        ))}
      </div>
    </div>
  );
}

function ImportResultCard({ result, onConfirm }: { result: ImportToolResult; onConfirm: (fileUrl: string) => void }) {
  const isPreview = result.status === "preview";
  const blocked = !!result.stats?.would_exceed_trial;
  return (
    <div style={{
      borderRadius: G.radius,
      border: blocked ? `1px solid rgba(192,57,43,0.30)` : G.border,
      overflow: "hidden",
      background: blocked ? G.redBg : "rgba(255,255,255,0.45)",
      boxShadow: G.shadowCard,
      marginBottom: "12px",
    }}>
      <div style={{ padding: "12px 16px", borderBottom: G.borderSubtle, display: "flex", justifyContent: "space-between", gap: "12px" }}>
        <div>
          <div style={{ fontSize: "13.5px", fontWeight: 700, color: G.textPrimary }}>
            {isPreview ? "Contact import preview" : "Contacts imported"}
          </div>
          <div style={{ fontSize: "12px", color: G.textMuted }}>
            {result.file_name || result.list_name || "contacts"} · {result.stats?.valid_rows ?? result.saved ?? 0} contacts
          </div>
        </div>
        {isPreview && result.file_url && (
          <button
            onClick={() => onConfirm(result.file_url!)}
            disabled={blocked}
            style={{
              height: "32px", padding: "0 12px", borderRadius: G.radiusSm,
              border: "none", background: blocked ? "rgba(26,37,64,0.10)" : G.navy,
              color: blocked ? G.textMuted : "white",
              fontSize: "12.5px", fontWeight: 600, fontFamily: "inherit",
              cursor: blocked ? "not-allowed" : "pointer",
              boxShadow: blocked ? "none" : G.shadowBtn,
            }}
          >Confirm</button>
        )}
      </div>
      {result.preview && result.preview.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>{["name", "email", "company", "phone", "city"].map((col) => <th key={col} style={thS}>{col}</th>)}</tr>
            </thead>
            <tbody>
              {result.preview.map((row, index) => (
                <tr key={index}>
                  {["name", "email", "company", "phone", "city"].map((col) => (
                    <td key={col} style={tdS}>{row[col] || <span style={{ color: G.textMuted }}>-</span>}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {blocked && (
        <div style={{ padding: "10px 16px", fontSize: "12.5px", color: G.red }}>
          Trial limit reached. Import fewer contacts or upgrade the plan.
        </div>
      )}
    </div>
  );
}

// ── Model selector ────────────────────────────────────────────
function ModelSelector({ models, value, onChange }: {
  models: ChatModel[];
  value: ChatModel | null;
  onChange: (m: ChatModel) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function close(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => { if (value && models.length > 0) setOpen((o) => !o); }}
        disabled={!value || models.length === 0}
        style={{
          display: "flex", alignItems: "center", gap: "5px",
          padding: "5px 10px", borderRadius: G.radiusXs,
          border: G.border,
          background: "rgba(255,255,255,0.50)",
          backdropFilter: "blur(8px)",
          color: G.textSecondary,
          fontSize: "12px", cursor: value && models.length > 0 ? "pointer" : "default",
          fontFamily: "inherit", opacity: value && models.length > 0 ? 1 : 0.65,
        }}
      >
        {value ? value.label : "Модели не настроены"}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && value && (
        <div style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: 0,
          background: "rgba(245,248,252,0.92)",
          backdropFilter: G.blurHeavy, WebkitBackdropFilter: G.blurHeavy,
          border: G.border, borderRadius: G.radiusSm,
          boxShadow: G.shadowModal,
          overflow: "hidden", minWidth: "190px", zIndex: 50,
        }}>
          <div style={{ padding: "8px 12px 4px", fontSize: "10px", fontWeight: 700, color: G.textMuted, textTransform: "uppercase", letterSpacing: "0.08em" }}>Модель</div>
          {models.map((m) => (
            <div
              key={m.id}
              onClick={() => { onChange(m); setOpen(false); }}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "8px 12px", cursor: "pointer", gap: "12px",
                background: value.id === m.id ? G.navyXLight : "transparent",
                transition: "background 0.1s",
              }}
              onMouseEnter={(e) => { if (value.id !== m.id) (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.35)"; }}
              onMouseLeave={(e) => { if (value.id !== m.id) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
            >
              <div>
                <div style={{ fontSize: "13px", fontWeight: value.id === m.id ? 600 : 400, color: G.textPrimary }}>{m.label}</div>
                <div style={{ fontSize: "11px", color: G.textMuted }}>{m.sub}</div>
              </div>
              {value.id === m.id && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={G.navy} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── LidaLogo ──────────────────────────────────────────────────
function LidaLogo({ size = 52 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none">
      <rect width="52" height="52" rx="13" fill={G.navy} />
      <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
      <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
      <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}

const QUICK_CHIPS = [
  { icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>, label: "Найти компании", sub: "в нужном городе и нише" },
  { icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>, label: "Написать письмо", sub: "холодное или тёплое" },
  { icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>, label: "Создать кампанию", sub: "авто-последовательность" },
  { icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>, label: "Обогатить контакты", sub: "email, телефон, сайт" },
];

export default function ChatPage() {
  const [tabs, setTabs] = useState<Tab[]>([
    { id: 1, title: "Новый разговор", sessionId: null, messages: [] },
  ]);
  const [activeTabId, setActiveTabId] = useState(1);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ChatModel[]>(DEFAULT_MODELS);
  const [selectedModel, setSelectedModel] = useState<ChatModel | null>(DEFAULT_MODELS[0]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeTab = tabs.find((t) => t.id === activeTabId)!;
  const messages = activeTab?.messages ?? [];
  const isEmpty = messages.length === 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeTab?.messages]);

  useEffect(() => {
    if (taRef.current) {
      taRef.current.style.height = "auto";
      taRef.current.style.height = Math.min(taRef.current.scrollHeight, 140) + "px";
    }
  }, [input]);

  useEffect(() => {
    let alive = true;
    api.get<ChatModel[]>("/chat/models")
      .then((res) => {
        if (!alive) return;
        const next = Array.isArray(res.data) ? res.data : [];
        setModels(next);
        setSelectedModel((current) => next.find((m) => m.id === current?.id) ?? next[0] ?? null);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  function updateTab(id: number, updater: (t: Tab) => Tab) {
    setTabs((prev) => prev.map((t) => (t.id === id ? updater(t) : t)));
  }

  function addTab() {
    const newId = Date.now();
    setTabs((prev) => [...prev, { id: newId, title: "Новый разговор", sessionId: null, messages: [] }]);
    setActiveTabId(newId);
  }

  function closeTab(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (tabs.length === 1) return;
    const idx = tabs.findIndex((t) => t.id === id);
    const next = tabs[idx > 0 ? idx - 1 : 1];
    setTabs((prev) => prev.filter((t) => t.id !== id));
    if (activeTabId === id) setActiveTabId(next.id);
  }

  async function getOrCreateSession(tabId: number): Promise<string> {
    const tab = tabs.find((t) => t.id === tabId);
    if (tab?.sessionId) return tab.sessionId;
    const res = await api.post("/chat/sessions", {});
    const sid: string = res.data.id;
    updateTab(tabId, (t) => ({ ...t, sessionId: sid }));
    return sid;
  }

  async function sendMessage(textOverride?: string) {
    const text = (textOverride ?? input).trim();
    if (!text || loading || !selectedModel) return;
    if (!textOverride) setInput("");
    setLoading(true);

    const msgId = String(Date.now());
    const userMsg: Msg = { id: msgId, role: "user", content: text, toolSteps: [] };
    const assistantId = String(Date.now() + 1);
    const assistantMsg: Msg = { id: assistantId, role: "assistant", content: "", toolSteps: [], pending: true };

    const currentTabId = activeTabId;

    updateTab(currentTabId, (t) => ({
      ...t,
      title: t.messages.length === 0 ? text.slice(0, 30) : t.title,
      messages: [...t.messages, userMsg, assistantMsg],
    }));

    try {
      const sid = await getOrCreateSession(currentTabId);
      const token = getToken();
      let accumulated = "";
      const toolSteps: ToolStep[] = [];
      let companies: Company[] | undefined;
      let importResult: ImportToolResult | undefined;

      await streamSSE(
        `/api/v1/chat/sessions/${sid}/message`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: text, model: selectedModel.id }),
        },
        (ev) => {
          try {
            const data = JSON.parse(ev.data);
            if (data.event === "text") {
              accumulated += data.content;
              updateTab(currentTabId, (t) => ({
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: accumulated, pending: false } : m
                ),
              }));
            } else if (data.event === "tool_result") {
              const toolName: string = data.name ?? "tool";
              const stepId = String(Date.now());
              const label = toolName.replace(/_/g, " ");
              toolSteps.push({ id: stepId, label, done: true });

              // Extract companies from the search tool contract.
              const payload = data.result as ({ companies?: unknown } | unknown[] | undefined);
              const rawCompanies = Array.isArray(payload)
                ? payload
                : payload && typeof payload === "object" && Array.isArray(payload.companies)
                  ? payload.companies
                  : undefined;
              if (rawCompanies && rawCompanies.length > 0 && typeof rawCompanies[0] === "object" && rawCompanies[0] !== null && "name" in rawCompanies[0]) {
                companies = rawCompanies.map((c, i) => ({ id: i, ...(c as object) })) as Company[];
              }
              if (toolName === "import_contacts" && data.result && typeof data.result === "object") {
                importResult = data.result as ImportToolResult;
              }

              updateTab(currentTabId, (t) => ({
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId ? { ...m, toolSteps: [...toolSteps], companies, importResult } : m
                ),
              }));
            } else if (data.event === "error") {
              updateTab(currentTabId, (t) => ({
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: `Ошибка: ${data.message}`, pending: false } : m
                ),
              }));
            }
          } catch { /* ignore parse errors */ }
        }
      );
    } catch {
      updateTab(currentTabId, (t) => ({
        ...t,
        messages: t.messages.map((m) =>
          m.id === assistantId ? { ...m, content: "Не удалось получить ответ. Попробуйте снова.", pending: false } : m
        ),
      }));
    } finally {
      setLoading(false);
    }
  }

  async function uploadContactFileInChat(file: File) {
    if (loading) return;
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/contacts/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const fileUrl = data.file_url;
      if (!fileUrl) {
        setInput(`Could not prepare ${file.name} for import.`);
        return;
      }
      await sendMessage(`Import contacts from ${file.name}. file_url=${fileUrl}. confirmed=false. Show preview.`);
    } catch {
      setInput(`Could not read ${file.name}. Check that it is CSV, TSV or XLSX.`);
    }
  }

  function confirmImportInChat(fileUrl: string) {
    void sendMessage(`Confirm import. file_url=${fileUrl}. confirmed=true.`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.tsv,.xlsx"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void uploadContactFileInChat(file);
          e.target.value = "";
        }}
      />

      {/* Tabs bar — only when messages exist or multiple tabs */}
      {(!isEmpty || tabs.length > 1) && (
        <div style={{
          height: "44px", flexShrink: 0,
          display: "flex", alignItems: "stretch",
          background: "rgba(255,255,255,0.45)",
          backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
          borderBottom: G.borderSubtle,
          overflow: "hidden",
        }}>
          <div style={{ display: "flex", alignItems: "stretch", flex: 1, overflowX: "auto", overflowY: "hidden" }}>
            {tabs.map((tab) => {
              const active = activeTabId === tab.id;
              return (
                <div
                  key={tab.id}
                  onClick={() => setActiveTabId(tab.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: "7px",
                    padding: "0 14px", borderRight: G.borderSubtle,
                    cursor: "pointer",
                    background: active ? "rgba(255,255,255,0.55)" : "transparent",
                    borderBottom: active ? `2px solid ${G.navy}` : "2px solid transparent",
                    minWidth: 0, maxWidth: "180px",
                    transition: "background 0.1s", flexShrink: 0,
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={active ? G.navy : G.textMuted} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                  <span style={{
                    fontSize: "12.5px", fontWeight: active ? 600 : 400,
                    color: active ? G.textPrimary : G.textMuted,
                    flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>{tab.title}</span>
                  {tabs.length > 1 && (
                    <span onClick={(e) => closeTab(tab.id, e)} style={{ color: G.textMuted, cursor: "pointer", fontSize: "15px", lineHeight: 1, flexShrink: 0, padding: "0 1px" }}>×</span>
                  )}
                </div>
              );
            })}
          </div>
          <button
            onClick={addTab}
            style={{
              width: "44px", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "transparent", border: "none", borderLeft: G.borderSubtle,
              cursor: "pointer", color: G.textMuted, fontSize: "20px",
              transition: "color 0.12s",
            }}
            onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.color = G.navy}
            onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.color = G.textMuted}
          >+</button>
        </div>
      )}

      {/* Content area */}
      <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column", alignItems: "center", padding: isEmpty ? "0" : "28px 0" }}>
        {isEmpty ? (
          /* ── Empty state: ChatGPT style ── */
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            width: "100%", padding: "0 24px",
            animation: "fadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both",
          }}>
            <div style={{ marginBottom: "20px" }}><LidaLogo size={52} /></div>

            <h1 style={{
              fontSize: "28px", fontWeight: 700,
              color: G.textPrimary, letterSpacing: "-0.6px",
              margin: "0 0 8px", textAlign: "center",
            }}>Чем могу помочь?</h1>
            <p style={{
              fontSize: "15px", color: G.textMuted,
              margin: "0 0 36px", textAlign: "center", lineHeight: "1.55",
              maxWidth: "400px",
            }}>Лида найдёт компании, напишет письма<br />и будет вести их до ответа</p>

            {/* Large centered input */}
            <div style={{
              width: "100%", maxWidth: "680px",
              background: "rgba(255,255,255,0.72)",
              backdropFilter: G.blurHeavy, WebkitBackdropFilter: G.blurHeavy,
              border: "1px solid rgba(255,255,255,0.85)",
              borderRadius: "20px",
              boxShadow: "0 8px 40px rgba(20,40,80,0.12), 0 2px 8px rgba(20,40,80,0.06)",
              overflow: "hidden",
              marginBottom: "16px",
            }}>
              <textarea
                ref={taRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                placeholder="Напишите Лиде…"
                rows={1}
                style={{
                  width: "100%", border: "none", outline: "none",
                  background: "transparent", resize: "none",
                  padding: "18px 20px 10px",
                  fontSize: "15px", lineHeight: "1.55",
                  color: G.textPrimary, fontFamily: "inherit",
                  boxSizing: "border-box", minHeight: "54px",
                }}
              />
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 14px 12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ModelSelector models={models} value={selectedModel} onChange={setSelectedModel} />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                    title="Import contacts"
                    style={{
                      width: "32px", height: "32px", borderRadius: "9px",
                      border: G.border, background: "rgba(255,255,255,0.50)",
                      color: G.textMuted, cursor: loading ? "default" : "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: "inherit",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                  </button>
                </div>
                <button
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || loading || !selectedModel}
                  style={{
                    width: "36px", height: "36px", borderRadius: "10px",
                    background: input.trim() && !loading && selectedModel ? G.navy : "rgba(26,37,64,0.08)",
                    border: "none", cursor: input.trim() && !loading && selectedModel ? "pointer" : "default",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    transition: "background 0.15s",
                    boxShadow: input.trim() && !loading && selectedModel ? G.shadowBtn : "none",
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                    stroke={input.trim() && !loading && selectedModel ? "white" : G.textMuted}
                    strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Quick action chips 2×2 */}
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(2, 1fr)",
              gap: "10px", width: "100%", maxWidth: "680px",
            }}>
              {QUICK_CHIPS.map((chip) => (
                <button
                  key={chip.label}
                  onClick={() => setInput(chip.label)}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: "11px",
                    padding: "14px 16px", borderRadius: "14px",
                    border: "1px solid rgba(255,255,255,0.75)",
                    background: "rgba(255,255,255,0.50)",
                    backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
                    cursor: "pointer", textAlign: "left",
                    transition: "background 0.13s, box-shadow 0.13s",
                    boxShadow: "0 2px 10px rgba(20,40,80,0.06)",
                    fontFamily: "inherit",
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.75)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 20px rgba(20,40,80,0.10)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.50)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 2px 10px rgba(20,40,80,0.06)"; }}
                >
                  <div style={{
                    width: "32px", height: "32px", borderRadius: "9px", flexShrink: 0,
                    background: G.navyXLight, border: G.borderDark,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: G.navy,
                  }}>{chip.icon}</div>
                  <div>
                    <div style={{ fontSize: "13.5px", fontWeight: 600, color: G.textPrimary, marginBottom: "2px" }}>{chip.label}</div>
                    <div style={{ fontSize: "12px", color: G.textMuted }}>{chip.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ── Messages ── */
          <div style={{ width: "100%", maxWidth: "780px", padding: "0 24px" }}>
            {messages.map((msg) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} style={{ display: "flex", justifyContent: "flex-end", marginBottom: "14px" }}>
                    <div style={{
                      maxWidth: "460px", padding: "10px 15px",
                      borderRadius: "14px 14px 3px 14px",
                      background: G.navy,
                      color: "rgba(255,255,255,0.92)",
                      fontSize: "14px", lineHeight: "1.55",
                      boxShadow: G.shadowBtn,
                    }}>
                      {msg.content}
                    </div>
                  </div>
                );
              }

              return (
                <div key={msg.id} style={{ marginBottom: "16px" }}>
                  {msg.toolSteps.length > 0 && (
                    <div style={{ maxWidth: "620px", marginBottom: "8px" }}>
                      <ToolRunStatus steps={msg.toolSteps} />
                    </div>
                  )}
                  {msg.companies && msg.companies.length > 0 && (
                    <div style={{ width: "100%", marginBottom: "12px" }}>
                      <LeadResultsCard
                        companies={msg.companies}
                        onSaveRequest={() => sendMessage("Сохрани найденные компании в новый список контактов.")}
                      />
                    </div>
                  )}
                  {msg.importResult && (
                    <div style={{ width: "100%", marginBottom: "12px" }}>
                      <ImportResultCard result={msg.importResult} onConfirm={confirmImportInChat} />
                    </div>
                  )}
                  {(msg.content || msg.pending) && (
                    <div style={{ display: "flex", gap: "10px", alignItems: "flex-start", maxWidth: "620px" }}>
                      <div style={{
                        width: "28px", height: "28px", borderRadius: "50%",
                        background: G.navy, flexShrink: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "white", fontSize: "11px", fontWeight: 700, marginTop: "1px",
                        boxShadow: G.shadowBtn,
                        border: "2px solid rgba(255,255,255,0.5)",
                      }}>Л</div>
                      <div style={{
                        fontSize: "14px", lineHeight: "1.6",
                        color: G.textPrimary, paddingTop: "3px",
                        whiteSpace: "pre-wrap", wordBreak: "break-word",
                        animation: msg.pending && !msg.content ? "pulse 1.2s ease-in-out infinite" : undefined,
                      }}>
                        {msg.content || (msg.pending ? "…" : "")}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Bottom input — only when messages exist */}
      {!isEmpty && (
        <div style={{ padding: "14px 24px 20px", flexShrink: 0, display: "flex", justifyContent: "center" }}>
          <div style={{
            width: "100%", maxWidth: "780px",
            background: "rgba(255,255,255,0.60)",
            backdropFilter: G.blurHeavy, WebkitBackdropFilter: G.blurHeavy,
            border: G.border, borderRadius: "16px",
            boxShadow: G.shadow, overflow: "hidden",
          }}>
            <textarea
              ref={taRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder="Напишите Лиде…"
              rows={1}
              style={{
                width: "100%", border: "none", outline: "none",
                background: "transparent", resize: "none",
                padding: "14px 16px 8px",
                fontSize: "14px", lineHeight: "1.55",
                color: G.textPrimary, fontFamily: "inherit",
                boxSizing: "border-box", minHeight: "44px",
                opacity: loading ? 0.6 : 1,
              }}
            />
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 12px 10px" }}>
              <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                <ModelSelector models={models} value={selectedModel} onChange={setSelectedModel} />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                  title="Import contacts"
                  style={{
                    width: "28px", height: "28px", borderRadius: "8px",
                    border: G.borderSubtle, background: "rgba(255,255,255,0.40)",
                    color: G.textMuted, cursor: loading ? "default" : "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: "inherit",
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </button>
                {["Найти компании", "Написать письмо", "Обогатить"].map((hint) => (
                  <button key={hint} onClick={() => setInput(hint)} style={{
                    padding: "4px 10px", borderRadius: "6px",
                    border: G.borderSubtle,
                    background: "rgba(255,255,255,0.40)",
                    color: G.textMuted, fontSize: "12px",
                    cursor: "pointer", fontFamily: "inherit",
                    transition: "background 0.1s",
                  }}
                    onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.70)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.40)"}
                  >{hint}</button>
                ))}
              </div>
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading || !selectedModel}
                style={{
                  width: "34px", height: "34px", borderRadius: "9px",
                  background: input.trim() && !loading && selectedModel ? G.navy : "rgba(26,37,64,0.10)",
                  border: "none", cursor: input.trim() && !loading && selectedModel ? "pointer" : "default",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 0.15s",
                  boxShadow: input.trim() && !loading && selectedModel ? G.shadowBtn : "none",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke={input.trim() && !loading && selectedModel ? "white" : G.textMuted}
                  strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
