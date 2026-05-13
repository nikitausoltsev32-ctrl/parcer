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
  message?: string;
  domain?: string | null;
  ts?: string;
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
  const isDone = ["done", "partial", "failed"].includes(progress.stage ?? "");
  const barColor = progress.stage === "failed" ? G.red : progress.stage === "partial" ? G.amber : G.green;

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
    </div>
  );
}
