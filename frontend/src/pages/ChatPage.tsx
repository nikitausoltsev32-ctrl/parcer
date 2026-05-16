import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { getToken } from "../lib/auth";
import { streamSSE } from "../lib/sse";
import { G, SOURCE_BADGE } from "../lib/design";
import { LeadReportList, type LeadReportItem } from "../components/LeadReportList";
import { LeadSearchProgress, type LeadSearchEvent, type LeadSearchProgressData } from "../components/LeadSearchProgress";
import { Save } from "lucide-react";

interface ChatModel {
  id: string;
  label: string;
  sub: string;
}

const DEFAULT_MODELS: ChatModel[] = [
  { id: "nvidia/z-ai/glm-5.1", label: "GLM 5.1", sub: "NVIDIA" },
  { id: "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", label: "Nemotron 3 Nano Omni 30B", sub: "NVIDIA reasoning" },
];

interface ToolStep {
  id: string;
  label: string;
  done: boolean;
  warning?: boolean;
}

interface Company extends LeadReportItem {
  id: number | string;
  name: string;
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

interface LeadSearchJob {
  logId: string;
  status: "pending" | "success" | "partial" | "failed";
  saved?: number;
  listName?: string | null;
  error?: string | null;
  progress?: LeadSearchProgressData | null;
  events?: LeadSearchEvent[];
}

interface Msg {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolSteps: ToolStep[];
  companies?: Company[];
  leadSearch?: LeadSearchJob;
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

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

function LeadResultsCard({ companies, onSaveRequest }: { companies: Company[]; onSaveRequest: () => void }) {
  const sources = [...new Set(companies.map((c) => c.source).filter(Boolean))] as string[];
  const scores = companies
    .map((c) => (typeof c.score === "number" ? c.score : typeof c.lead_fit?.score === "number" ? c.lead_fit.score : null))
    .filter((score): score is number => score !== null);
  const avgScore = scores.length > 0 ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : null;
  const highScoreCount = scores.filter((score) => score >= 70).length;
  const scoreColor = avgScore === null ? G.textMuted : avgScore >= 70 ? G.green : avgScore >= 45 ? G.amber : G.red;
  const scoreBg = avgScore === null ? "rgba(26,37,64,0.07)" : avgScore >= 70 ? G.greenBg : avgScore >= 45 ? G.amberBg : G.redBg;

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
      <div style={{
        padding: "12px 16px",
        background: "rgba(255,255,255,0.35)",
        borderBottom: G.borderSubtle,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "12px",
        flexWrap: "wrap",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "13.5px", fontWeight: 700, color: G.textPrimary }}>Найденные лиды</span>
          <span style={{
            fontSize: "11px",
            fontWeight: 600,
            background: "rgba(26,37,64,0.08)",
            color: G.textSecondary,
            padding: "1px 8px",
            borderRadius: "20px",
          }}>{companies.length}</span>
          <span style={{
            fontSize: "11px",
            fontWeight: 700,
            background: scoreBg,
            color: scoreColor,
            padding: "2px 8px",
            borderRadius: "20px",
            border: `1px solid ${avgScore === null ? "rgba(26,37,64,0.12)" : scoreColor}`,
          }}>
            Score {avgScore ?? "-"}
          </span>
          <span style={{
            fontSize: "11px",
            fontWeight: 600,
            background: "rgba(26,37,64,0.06)",
            color: G.textSecondary,
            padding: "2px 8px",
            borderRadius: "20px",
          }}>
            оценено {scores.length}/{companies.length}
          </span>
          {highScoreCount > 0 && (
            <span style={{
              fontSize: "11px",
              fontWeight: 600,
              background: G.greenBg,
              color: G.green,
              padding: "2px 8px",
              borderRadius: "20px",
            }}>
              high {highScoreCount}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
          {sources.map((s) => <SourceBadge key={s} source={s} />)}
        </div>
      </div>

      <div style={{ padding: "12px 16px" }}>
        <LeadReportList leads={companies} compact />
      </div>

      <div style={{
        padding: "10px 16px",
        borderTop: G.borderSubtle,
        background: "rgba(255,255,255,0.30)",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        flexWrap: "wrap",
      }}>
        <button
          onClick={onSaveRequest}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "6px 12px",
            borderRadius: G.radiusSm,
            background: G.navy,
            color: "white",
            border: "none",
            fontSize: "12.5px",
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "inherit",
            boxShadow: G.shadowBtn,
            transition: "all 0.15s",
          }}
        >
          <Save size={12} strokeWidth={2} />
          Сохранить через чат
        </button>
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
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 640);
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
    const handler = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  useEffect(() => {
    let alive = true;
    api.get<ChatModel[]>("/chat/models")
      .then((res) => {
        if (!alive) return;
        const next = Array.isArray(res.data) && res.data.length > 0 ? res.data : DEFAULT_MODELS;
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

  async function pollLeadSearch(logId: string, assistantId: string, tabId: number) {
    let lastLeads: Company[] = [];
    let lastSaved = 0;
    let lastListName: string | null = null;
    let lastProgress: LeadSearchProgressData | null = null;
    let lastEvents: LeadSearchEvent[] = [];

    for (let attempt = 0; attempt < 240; attempt += 1) {
      await sleep(2500);
      try {
        const { data } = await api.get(`/lead-search/${logId}`);
        const status = data.status as LeadSearchJob["status"];
        const saved = typeof data.saved === "number" ? data.saved : 0;
        const listName = typeof data.list_name === "string" ? data.list_name : null;
        const progress = data.progress && typeof data.progress === "object" ? data.progress as LeadSearchProgressData : null;
        const events = Array.isArray(data.events) ? data.events as LeadSearchEvent[] : [];
        lastSaved = saved;
        lastListName = listName;
        if (progress) lastProgress = progress;
        if (events.length > 0) lastEvents = events;

        const rawLeads = Array.isArray(data.leads) ? data.leads : [];
        if (rawLeads.length > 0) {
          lastLeads = rawLeads.map((lead: object, index: number) => ({ id: index, ...lead })) as Company[];
        }

        if (status === "pending") {
          updateTab(tabId, (t) => ({
            ...t,
            messages: t.messages.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    pending: true,
                    content: lastProgress?.label || (saved > 0 ? `Обрабатываю, уже сохранено ${saved}.` : "Запускаю AI-поиск."),
                    companies: lastLeads.length > 0 ? lastLeads : m.companies,
                    leadSearch: { logId, status, saved, listName, progress: lastProgress, events: lastEvents },
                  }
                : m
            ),
          }));
          continue;
        }

        if (status === "success" || status === "partial") {
          updateTab(tabId, (t) => ({
            ...t,
            messages: t.messages.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    pending: false,
                    content: saved > 0
                      ? `${status === "partial" ? "Частично готово" : "Готово"}: сохранено ${saved} лидов${listName ? ` в "${listName}"` : ""}.`
                      : "Готово, но подходящих компаний не найдено. Статьи и подборки отфильтрованы.",
                    companies: lastLeads,
                    leadSearch: { logId, status, saved, listName, progress: lastProgress, events: lastEvents },
                  }
                : m
            ),
          }));
          return;
        }

        updateTab(tabId, (t) => ({
          ...t,
          messages: t.messages.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  pending: false,
                  content: data.failure_reason || "Поиск завершился с ошибкой.",
                  leadSearch: { logId, status: "failed", saved, listName, error: data.failure_reason, progress: lastProgress, events: lastEvents },
                }
              : m
          ),
        }));
        return;
      } catch {
        if (attempt >= 239) {
          updateTab(tabId, (t) => ({
            ...t,
            messages: t.messages.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    pending: false,
                    content: "Не удалось получить статус AI-поиска. Попробуйте открыть результаты позже в контактах.",
                    leadSearch: { logId, status: "failed", error: "status_poll_failed", progress: lastProgress, events: lastEvents },
                  }
                : m
            ),
          }));
        }
      }
    }

    // Loop ended (240 attempts ≈ 10 minutes) — show whatever we accumulated
    updateTab(tabId, (t) => ({
      ...t,
      messages: t.messages.map((m) =>
        m.id === assistantId
          ? {
              ...m,
              pending: false,
              content: lastLeads.length > 0
                ? `Найдено ${lastSaved} компаний${lastListName ? ` в "${lastListName}"` : ""}. Поиск может продолжаться в фоне.`
                : "Поиск занял слишком много времени. Результаты могут появиться позже в разделе Контакты.",
              companies: lastLeads.length > 0 ? lastLeads : undefined,
              leadSearch: {
                logId,
                status: lastLeads.length > 0 ? "partial" : "failed" as LeadSearchJob["status"],
                saved: lastSaved,
                listName: lastListName,
                progress: lastProgress,
                events: lastEvents,
              },
            }
          : m
      ),
    }));
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
      let leadSearch: LeadSearchJob | undefined;
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
                  m.id === assistantId
                    ? { ...m, content: accumulated, pending: false, ...(leadSearch ? { leadSearch } : {}) }
                    : m
                ),
              }));
            } else if (data.event === "tool_result") {
              const toolName: string = data.name ?? "tool";
              const stepId = String(Date.now());
              const label = toolName.replace(/_/g, " ");
              toolSteps.push({ id: stepId, label, done: true });

              const payload = data.result as ({ companies?: unknown } | unknown[] | undefined);
              const resultObject = data.result as Record<string, unknown> | undefined;
              if (
                toolName === "search_companies"
                && resultObject
                && resultObject.status === "pending"
                && typeof resultObject.log_id === "string"
              ) {
                leadSearch = {
                  logId: resultObject.log_id,
                  status: "pending",
                  progress: {
                    stage: "queued",
                    label: "Поиск поставлен в очередь",
                    percent: 1,
                    found: 0,
                    filtered: 0,
                    crawled: 0,
                    saved: 0,
                    target: typeof resultObject.limit === "number" ? resultObject.limit : 5,
                    pages_crawled: 0,
                    llm_calls: 0,
                    current_domain: null,
                  },
                  events: [],
                };
                updateTab(currentTabId, (t) => ({
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          pending: true,
                          content: "Поиск поставлен в очередь.",
                          toolSteps: [...toolSteps],
                          leadSearch,
                        }
                      : m
                  ),
                }));
                void pollLeadSearch(resultObject.log_id, assistantId, currentTabId);
                return;
              }

              // Extract companies from the legacy search tool contract.
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
                  m.id === assistantId ? { ...m, toolSteps: [...toolSteps], companies, leadSearch, importResult } : m
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
      <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column", alignItems: "center", padding: isEmpty ? "0" : isMobile ? "12px 0" : "28px 0" }}>
        {isEmpty ? (
          /* ── Empty state ── */
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            width: "100%", padding: isMobile ? "0 16px" : "0 24px",
            animation: "fadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both",
          }}>
            <div style={{ marginBottom: isMobile ? "14px" : "20px" }}><LidaLogo size={isMobile ? 40 : 52} /></div>

            <h1 style={{
              fontSize: isMobile ? "22px" : "28px", fontWeight: 700,
              color: G.textPrimary, letterSpacing: "-0.6px",
              margin: "0 0 8px", textAlign: "center",
            }}>Чем могу помочь?</h1>
            <p style={{
              fontSize: isMobile ? "13.5px" : "15px", color: G.textMuted,
              margin: isMobile ? "0 0 24px" : "0 0 36px", textAlign: "center", lineHeight: "1.55",
              maxWidth: "400px",
            }}>Лида найдёт компании, напишет письма<br />и будет вести их до ответа</p>

            {/* Large centered input */}
            <div style={{
              width: "100%", maxWidth: "680px",
              background: "rgba(255,255,255,0.72)",
              backdropFilter: G.blurHeavy, WebkitBackdropFilter: G.blurHeavy,
              border: "1px solid rgba(255,255,255,0.85)",
              borderRadius: isMobile ? "16px" : "20px",
              boxShadow: "0 8px 40px rgba(20,40,80,0.12), 0 2px 8px rgba(20,40,80,0.06)",
              overflow: "hidden",
              marginBottom: "12px",
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
                  padding: isMobile ? "14px 16px 8px" : "18px 20px 10px",
                  fontSize: isMobile ? "14px" : "15px", lineHeight: "1.55",
                  color: G.textPrimary, fontFamily: "inherit",
                  boxSizing: "border-box", minHeight: isMobile ? "46px" : "54px",
                }}
              />
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: isMobile ? "2px 10px 10px" : "4px 14px 12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  {!isMobile && <ModelSelector models={models} value={selectedModel} onChange={setSelectedModel} />}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                    aria-label="Import contacts"
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
                  aria-label="Send message"
                  title="Send message"
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

            {/* Quick action chips */}
            <div style={{
              display: "grid",
              gridTemplateColumns: isMobile ? "repeat(2, 1fr)" : "repeat(2, 1fr)",
              gap: isMobile ? "8px" : "10px",
              width: "100%", maxWidth: "680px",
            }}>
              {QUICK_CHIPS.slice(0, isMobile ? 4 : 4).map((chip) => (
                <button
                  key={chip.label}
                  onClick={() => setInput(chip.label)}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: isMobile ? "8px" : "11px",
                    padding: isMobile ? "10px 12px" : "14px 16px", borderRadius: "14px",
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
                    width: isMobile ? "26px" : "32px", height: isMobile ? "26px" : "32px",
                    borderRadius: "9px", flexShrink: 0,
                    background: G.navyXLight, border: G.borderDark,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: G.navy,
                  }}>{chip.icon}</div>
                  <div>
                    <div style={{ fontSize: isMobile ? "12.5px" : "13.5px", fontWeight: 600, color: G.textPrimary, marginBottom: "2px" }}>{chip.label}</div>
                    {!isMobile && <div style={{ fontSize: "12px", color: G.textMuted }}>{chip.sub}</div>}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ── Messages ── */
          <div style={{ width: "100%", maxWidth: "780px", padding: isMobile ? "0 12px" : "0 24px" }}>
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
                        onSaveRequest={() => setInput("Сохрани найденные компании в новый список контактов. Название списка: Найденные компании.")}
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
                  {msg.leadSearch?.progress && (
                    <div style={{ maxWidth: "620px", marginTop: "10px" }}>
                      <LeadSearchProgress progress={msg.leadSearch.progress} events={msg.leadSearch.events} />
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
                  aria-label="Import contacts"
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
                aria-label="Send message"
                title="Send message"
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
