import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { getToken } from "../lib/auth";
import { streamSSE } from "../lib/sse";

const SAGE = "oklch(0.52 0.10 165)";
const BORDER = "rgba(0,0,0,0.08)";

const MODELS = [
  { id: "llama", label: "Llama 3.3", sub: "по умолчанию" },
  { id: "gpt4o", label: "GPT-4o", sub: "OpenAI" },
  { id: "claude", label: "Claude 3.5", sub: "Anthropic" },
  { id: "gemini", label: "Gemini Pro", sub: "Google" },
  { id: "minimax", label: "MiniMax", sub: "MiniMax" },
];

const HINT_CHIPS = ["Найти компании", "Обогатить контакты", "Создать письмо"];

interface ToolStep {
  id: string;
  label: string;
  done: boolean;
}

interface Msg {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolSteps: ToolStep[];
  pending?: boolean;
}

function ToolProgress({ steps }: { steps: ToolStep[] }) {
  const [expanded, setExpanded] = useState(false);
  const allDone = steps.every((s) => s.done);

  return (
    <div style={{
      borderRadius: "8px",
      border: `1px solid ${BORDER}`,
      overflow: "hidden",
      marginBottom: "4px",
      background: "rgba(0,0,0,0.015)",
    }}>
      <div
        onClick={() => setExpanded((e) => !e)}
        style={{
          display: "flex", alignItems: "center", gap: "8px",
          padding: "9px 12px", cursor: "pointer", userSelect: "none",
        }}
      >
        {allDone ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#48BB78" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#A0AEC0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: "spin 1.5s linear infinite" }}>
            <circle cx="12" cy="12" r="10" strokeDasharray="30 10" />
          </svg>
        )}
        <span style={{ fontSize: "12.5px", color: "#777", flex: 1 }}>
          {allDone ? `Лида выполнила ${steps.length} ${steps.length === 1 ? "шаг" : "шага"}` : "Лида работает…"}
        </span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#BBB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
      {expanded && (
        <div style={{ borderTop: `1px solid rgba(0,0,0,0.05)`, padding: "8px 12px 10px", display: "flex", flexDirection: "column", gap: "6px" }}>
          {steps.map((step) => (
            <div key={step.id} style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
              <div style={{ marginTop: "1px", flexShrink: 0 }}>
                {step.done ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#48BB78" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <div style={{ width: "13px", height: "13px", borderRadius: "50%", border: "2px solid #DDD" }} />
                )}
              </div>
              <span style={{ fontSize: "12px", lineHeight: "1.45", color: step.done ? "#666" : "#AAA" }}>{step.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ModelSelector() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(MODELS[0]);
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
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex", alignItems: "center", gap: "5px",
          padding: "4px 9px", borderRadius: "6px",
          border: `1px solid rgba(0,0,0,0.1)`,
          background: "transparent", color: "#666",
          fontSize: "12px", cursor: "pointer", fontFamily: "inherit",
        }}
      >
        {selected.label}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <div style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: 0,
          background: "#FFF",
          border: `1px solid rgba(0,0,0,0.1)`,
          borderRadius: "9px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
          overflow: "hidden", minWidth: "180px", zIndex: 50,
        }}>
          <div style={{ padding: "6px 10px 4px", fontSize: "10.5px", fontWeight: 600, color: "#AAA", textTransform: "uppercase", letterSpacing: "0.07em" }}>Модель</div>
          {MODELS.map((m) => (
            <div
              key={m.id}
              onClick={() => { setSelected(m); setOpen(false); }}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "8px 12px", cursor: "pointer", gap: "12px",
                background: selected.id === m.id ? `color-mix(in oklch, ${SAGE} 10%, transparent)` : "transparent",
              }}
              onMouseEnter={(e) => { if (selected.id !== m.id) (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.03)"; }}
              onMouseLeave={(e) => { if (selected.id !== m.id) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
            >
              <div>
                <div style={{ fontSize: "13px", fontWeight: 500, color: "#1A1A1A" }}>{m.label}</div>
                <div style={{ fontSize: "11px", color: "#AAA" }}>{m.sub}</div>
              </div>
              {selected.id === m.id && (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={SAGE} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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

interface Tab {
  id: number;
  title: string;
  sessionId: string | null;
  messages: Msg[];
}

export default function ChatPage() {
  const [tabs, setTabs] = useState<Tab[]>([
    { id: 1, title: "Новый разговор", sessionId: null, messages: [] },
  ]);
  const [activeTabId, setActiveTabId] = useState(1);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const activeTab = tabs.find((t) => t.id === activeTabId)!;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeTab?.messages]);

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

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
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

      await streamSSE(
        `/api/v1/chat/sessions/${sid}/message`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: text }),
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
              const toolName = data.name ?? "tool";
              const stepId = String(Date.now());
              const label = toolName.replace(/_/g, " ");
              toolSteps.push({ id: stepId, label, done: true });
              updateTab(currentTabId, (t) => ({
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId ? { ...m, toolSteps: [...toolSteps] } : m
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
          } catch {
            // ignore parse errors
          }
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

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const messages = activeTab?.messages ?? [];

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", background: "#FFF", overflow: "hidden" }}>
      {/* Tabs bar */}
      <div style={{
        height: "42px", display: "flex", alignItems: "stretch",
        borderBottom: `1px solid ${BORDER}`,
        background: "#FAFAF9",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "stretch", flex: 1, overflowX: "auto", overflowY: "hidden" }}>
          {tabs.map((tab) => (
            <div
              key={tab.id}
              onClick={() => setActiveTabId(tab.id)}
              style={{
                display: "flex", alignItems: "center", gap: "7px",
                padding: "0 14px",
                borderRight: `1px solid ${BORDER}`,
                cursor: "pointer",
                background: activeTabId === tab.id ? "#FFF" : "transparent",
                borderBottom: activeTabId === tab.id ? `2px solid ${SAGE}` : "2px solid transparent",
                minWidth: 0, maxWidth: "180px",
                transition: "background 0.1s",
                flexShrink: 0,
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke={activeTabId === tab.id ? SAGE : "#CCC"}
                strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span style={{
                fontSize: "12.5px",
                fontWeight: activeTabId === tab.id ? 500 : 400,
                color: activeTabId === tab.id ? "#1A1A1A" : "#999",
                flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>{tab.title}</span>
              {tabs.length > 1 && (
                <span
                  onClick={(e) => closeTab(tab.id, e)}
                  style={{ fontSize: "14px", lineHeight: 1, color: "#CCC", cursor: "pointer", padding: "0 1px", flexShrink: 0 }}
                >×</span>
              )}
            </div>
          ))}
        </div>
        <button
          onClick={addTab}
          style={{
            width: "42px", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "transparent", border: "none",
            borderLeft: `1px solid ${BORDER}`,
            cursor: "pointer", color: "#AAA",
            fontSize: "18px", fontWeight: 300,
          }}
          title="Новый разговор"
        >+</button>
        <div style={{ display: "flex", alignItems: "center", padding: "0 14px", borderLeft: `1px solid ${BORDER}` }}>
          <div style={{ padding: "4px 10px", borderRadius: "5px", fontSize: "12px", border: `1px solid ${BORDER}`, color: "#AAA", cursor: "pointer" }}>
            История
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: "28px 0", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: "100%", maxWidth: "760px", padding: "0 24px" }}>
          {messages.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingTop: "80px", gap: "10px" }}>
              <svg width="32" height="32" viewBox="0 0 52 52" fill="none" style={{ opacity: 0.25 }}>
                <rect width="52" height="52" rx="13" fill={SAGE} />
                <rect x="13" y="13" width="5.5" height="26" rx="2.5" fill="white" />
                <rect x="13" y="33.5" width="24" height="5.5" rx="2.5" fill="white" />
                <line x1="21" y1="13" x2="37" y2="22" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
              </svg>
              <div style={{ fontSize: "14px", color: "#CCC", fontWeight: 500 }}>Напишите первый запрос</div>
            </div>
          ) : (
            messages.map((msg) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} style={{ display: "flex", justifyContent: "flex-end", marginBottom: "16px" }}>
                    <div style={{
                      maxWidth: "480px",
                      padding: "10px 14px",
                      borderRadius: "12px 12px 2px 12px",
                      background: "#F0F0ED",
                      color: "#1A1A1A",
                      fontSize: "14px", lineHeight: "1.5",
                    }}>
                      {msg.content}
                    </div>
                  </div>
                );
              }

              return (
                <div key={msg.id} style={{ marginBottom: "16px", maxWidth: "640px" }}>
                  {msg.toolSteps.length > 0 && <ToolProgress steps={msg.toolSteps} />}
                  {(msg.content || msg.pending) && (
                    <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                      <div style={{
                        width: "26px", height: "26px", borderRadius: "50%",
                        background: SAGE, flexShrink: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "white", fontSize: "11px", fontWeight: 700, marginTop: "1px",
                      }}>Л</div>
                      <div style={{
                        fontSize: "14px", lineHeight: "1.6",
                        color: "#333", paddingTop: "3px",
                        animation: msg.pending && !msg.content ? "pulse 1.2s ease-in-out infinite" : undefined,
                      }}>
                        {msg.content || (msg.pending ? "…" : "")}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <div style={{ padding: "16px 24px 20px", flexShrink: 0, display: "flex", justifyContent: "center" }}>
        <div style={{
          width: "100%", maxWidth: "760px",
          border: `1px solid rgba(0,0,0,0.12)`,
          borderRadius: "12px",
          background: "#FAFAF9",
          overflow: "hidden",
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
        }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder="Напишите Лиде..."
            rows={1}
            style={{
              width: "100%", border: "none", outline: "none",
              background: "transparent", resize: "none",
              padding: "14px 16px 10px",
              fontSize: "14px", lineHeight: "1.5",
              color: "#1A1A1A", fontFamily: "inherit",
              boxSizing: "border-box",
              opacity: loading ? 0.6 : 1,
            }}
          />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 12px 10px" }}>
            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
              <ModelSelector />
              {HINT_CHIPS.map((hint) => (
                <button
                  key={hint}
                  onClick={() => setInput(hint)}
                  style={{
                    padding: "4px 10px", borderRadius: "5px",
                    border: `1px solid rgba(0,0,0,0.1)`,
                    background: "transparent",
                    color: "#999", fontSize: "12px",
                    cursor: "pointer", fontFamily: "inherit",
                  }}
                >{hint}</button>
              ))}
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              style={{
                width: "32px", height: "32px", borderRadius: "7px",
                background: input.trim() && !loading ? SAGE : "#E5E5E5",
                border: "none",
                cursor: input.trim() && !loading ? "pointer" : "default",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "background 0.15s",
                flexShrink: 0,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke={input.trim() && !loading ? "#FFF" : "#AAA"}
                strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
