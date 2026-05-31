import { G } from "../lib/design";

export interface LeadSearchProgressData {
  stage?: string;
  label?: string;
  percent?: number;
  found?: number;
  filtered?: number;
  crawled?: number;
  saved?: number;
  target?: number;
  pages_crawled?: number;
  llm_calls?: number;
  current_domain?: string | null;
}

export interface LeadSearchEvent {
  stage?: string;
  status?: string;
  api?: string | null;
  provider?: string | null;
  actor?: string | null;
  agent?: string | null;
  subagent?: string | null;
  message?: string;
  domain?: string | null;
  current_domain?: string | null;
  ts?: string;
}

function eventStatus(event: LeadSearchEvent) {
  return event.status || event.stage || "pending";
}

function statusColor(status: string) {
  if (["success", "done", "completed"].includes(status)) return G.green;
  if (["failed", "error"].includes(status)) return G.red;
  if (["partial", "warning"].includes(status)) return G.amber;
  return G.navyLight;
}

function shortTime(ts?: string) {
  if (!ts) return "";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function LeadSearchProgress({
  progress,
  events = [],
}: {
  progress?: LeadSearchProgressData | null;
  events?: LeadSearchEvent[];
}) {
  if (!progress) return null;

  const percent = Math.max(0, Math.min(100, Math.round(progress.percent ?? 0)));
  const saved = progress.saved ?? 0;
  const target = progress.target ?? 0;
  const lastEvent = events.length > 0 ? events[events.length - 1] : null;
  const isDone = ["done", "success", "partial", "failed"].includes(progress.stage ?? "");
  const barColor = progress.stage === "failed" ? G.red : progress.stage === "partial" ? G.amber : G.green;
  const timeline = events.slice(-6);

  const counters = [
    ["найдено", progress.found ?? 0],
    ["после фильтра", progress.filtered ?? 0],
    ["сайтов", progress.crawled ?? 0],
    ["страниц", progress.pages_crawled ?? 0],
    ["AI", progress.llm_calls ?? 0],
  ];

  return (
    <div
      style={{
        borderRadius: G.radius,
        border: G.border,
        background: "rgba(255,255,255,0.50)",
        boxShadow: G.shadowCard,
        padding: "12px 14px",
        marginBottom: "10px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "baseline" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: "13.5px", fontWeight: 700, color: G.textPrimary, lineHeight: 1.35 }}>
            {progress.label || "Идет поиск лидов"}
          </div>
          <div style={{ fontSize: "12px", color: G.textMuted, marginTop: "3px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {progress.current_domain || lastEvent?.domain || lastEvent?.message || "Подготовка"}
          </div>
        </div>
        <div style={{ fontSize: "12px", fontWeight: 700, color: barColor, whiteSpace: "nowrap" }}>
          {saved}/{target || "-"}
        </div>
      </div>

      <div style={{ height: "8px", borderRadius: "999px", background: "rgba(26,37,64,0.08)", overflow: "hidden", marginTop: "10px" }}>
        <div
          style={{
            width: `${percent}%`,
            minWidth: percent > 0 ? "8px" : 0,
            height: "100%",
            borderRadius: "999px",
            background: barColor,
            transition: "width 240ms ease",
          }}
        />
      </div>

      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "10px" }}>
        {counters.map(([label, value]) => (
          <span
            key={label}
            style={{
              fontSize: "11px",
              color: G.textSecondary,
              background: "rgba(26,37,64,0.06)",
              border: G.borderDark,
              borderRadius: G.radiusXs,
              padding: "3px 7px",
              whiteSpace: "nowrap",
            }}
          >
            {label}: {value}
          </span>
        ))}
        <span
          style={{
            fontSize: "11px",
            color: isDone ? barColor : G.textSecondary,
            background: isDone ? "rgba(45,122,95,0.08)" : "rgba(26,37,64,0.06)",
            border: G.borderDark,
            borderRadius: G.radiusXs,
            padding: "3px 7px",
            whiteSpace: "nowrap",
          }}
        >
          {percent}%
        </span>
      </div>

      {timeline.length > 0 && (
        <div style={{ marginTop: "10px", borderTop: G.borderSubtle, paddingTop: "9px", display: "flex", flexDirection: "column", gap: "7px" }}>
          {timeline.map((event, index) => {
            const status = eventStatus(event);
            const color = statusColor(status);
            const api = event.api || event.provider;
            const actor = event.actor || event.subagent || event.agent;
            const domain = event.current_domain || event.domain;
            const message = event.message || event.stage || "Обновление";
            const time = shortTime(event.ts);

            return (
              <div
                key={`${event.ts || "event"}-${event.stage || status}-${index}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "12px minmax(0, 1fr)",
                  columnGap: "8px",
                  alignItems: "start",
                  minWidth: 0,
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "999px",
                    background: color,
                    marginTop: "5px",
                    boxShadow: `0 0 0 3px ${color}18`,
                  }}
                />
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "5px", flexWrap: "wrap", minWidth: 0 }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color, textTransform: "uppercase", lineHeight: 1.3 }}>
                      {status}
                    </span>
                    {api && (
                      <span style={{
                        fontSize: "10.5px",
                        fontWeight: 700,
                        color: G.textSecondary,
                        background: "rgba(26,37,64,0.06)",
                        border: G.borderDark,
                        borderRadius: G.radiusXs,
                        padding: "1px 5px",
                        lineHeight: 1.35,
                        maxWidth: "120px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}>
                        {api}
                      </span>
                    )}
                    {actor && (
                      <span style={{ fontSize: "11px", color: G.textMuted, lineHeight: 1.35, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "150px" }}>
                        {actor}
                      </span>
                    )}
                    {time && (
                      <span style={{ fontSize: "10.5px", color: G.textMuted, lineHeight: 1.35, marginLeft: "auto" }}>
                        {time}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "12px", color: G.textSecondary, lineHeight: 1.4, marginTop: "2px", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {domain ? `${domain}: ${message}` : message}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
