# App Cleanup + Settings + Template Outreach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the broken "Компании" section, give users a working Settings page for their business profile, and ensure every saved lead gets at least a starter outreach message.

**Architecture:** Three independent slices. (1) Frontend route/nav removal + file deletion — fixes the `/app/companies` white screen. (2) A real `SettingsPage` form wired to the existing `GET/PATCH /me` endpoint, mirroring `SetupWizard` fields. (3) A deterministic, no-LLM `template_outreach()` for light/basic leads in the lead pipeline, so leads that never reach Deep AI still ship a personalized-by-facts message (matches CLAUDE.md §8 "шаблонное" outreach for lower tiers).

**Tech Stack:** Frontend — React 18 + TypeScript + Vite + TanStack Query (verification via `npm run build` typecheck + `npm run lint`; no frontend unit-test runner exists). Backend — Python 3.12, pytest + pytest-asyncio.

---

## Progress (2026-05-31)

Executing via subagent-driven-development.

- **Task 1 — Remove Companies: ✅ DONE.** Commit `df97c94` removed `CompaniesPage`/`CompanyPage` imports+routes (App.tsx), the "Компании" nav item (AppLayout.tsx), deleted both page files, and repointed a dangling `/app/companies/:id` navigate in `ContactPage.tsx` to `/app/contacts`. Spec review confirmed the removal is correct. Known caveat: because App.tsx/AppLayout.tsx already had pre-session WIP (Landing/Kanban/Campaign wiring), the whole-file `git add` bundled that WIP into the commit — accepted on a dev branch (interactive `git add -p` unavailable here).
- **Task 2 — Settings page: ⏳ NOT STARTED.** Full file content for `frontend/src/pages/SettingsPage.tsx` is in Task 2 below, ready to paste. Before building, verify `G` tokens (`shadowCard`, `radiusSm`, `green`) exist in `frontend/src/lib/design.ts`; substitute nearest existing token if missing.
- **Task 3 — Template outreach: ⏳ NOT STARTED.** Code + tests ready in Task 3 below.

**To resume:** re-enter `superpowers:subagent-driven-development`, dispatch implementer for Task 2 then Task 3 from the text below.

---

### Task 1: Remove the "Компании" section

The working-copy `CompaniesPage.tsx` is truncated/broken (empty `useMemo()`, no `return`) → white screen at `/app/companies`. Per product decision, the section is removed during development. Data lives in Contacts/Kanban.

**Files:**
- Modify: `frontend/src/App.tsx` (remove imports + routes)
- Modify: `frontend/src/components/AppLayout.tsx:21` (remove nav item)
- Delete: `frontend/src/pages/CompaniesPage.tsx`
- Delete: `frontend/src/pages/CompanyPage.tsx`

- [ ] **Step 1: Remove route imports and routes in App.tsx**

Remove these two import lines:

```tsx
import CompaniesPage from "./pages/CompaniesPage";
```
```tsx
import CompanyPage from "./pages/CompanyPage";
```

Remove these two `<Route>` lines from inside `<Route path="/app" element={<AppShell />}>`:

```tsx
        <Route path="companies" element={<CompaniesPage />} />
        <Route path="companies/:id" element={<CompanyPage />} />
```

- [ ] **Step 2: Remove the Компании nav item in AppLayout.tsx**

Delete this entry from the `NAV_ITEMS` array (currently line 21):

```tsx
  { to: "/app/companies", label: "Компании", icon: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg> },
```

`BOTTOM_NAV_ITEMS = NAV_ITEMS.slice(0, 5)` automatically picks the new top-5 (Чат, Контакты, Канбан, Кампании, Входящие) — no further change needed.

- [ ] **Step 3: Delete the two page files**

```bash
git rm frontend/src/pages/CompaniesPage.tsx frontend/src/pages/CompanyPage.tsx
```

(`CompanyPage.tsx` is currently untracked per git status — if `git rm` errors on it, use `del "frontend\src\pages\CompanyPage.tsx"` in PowerShell instead.)

- [ ] **Step 4: Verify no dangling references remain**

Run (from repo root):
```bash
grep -rn "CompaniesPage\|CompanyPage\|/app/companies" frontend/src
```
Expected: no matches. If any match remains (e.g. a stray `navigate("/app/companies")`), remove or repoint it to `/app/contacts`.

- [ ] **Step 5: Typecheck + lint**

Run (from `frontend/`):
```bash
npm run build
npm run lint
```
Expected: build succeeds with no TS errors about missing modules; lint passes.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/AppLayout.tsx
git commit -m "feat(ui): remove Companies section (data lives in Contacts/Kanban)"
```

---

### Task 2: Working Settings page (business profile)

Replace the `SettingsPage` "в разработке" stub with a real form for the business profile (`business`, `offer`, `city`, `tone_default`, `full_name`), wired to `useMe` / `useUpdateMe`. Show plan + quota read-only. Fields and tone options mirror `SetupWizard` so the chat agent and lead pipeline (`user.business_profile`) read consistent data.

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx` (full replace)

Backend already supports this — `PATCH /me` accepts `{ full_name, business_profile: { business, offer, city, tone_default } }` (`backend/app/api/v1/users.py:17`, `backend/app/schemas/user.py:28`). No backend change.

- [ ] **Step 1: Replace SettingsPage.tsx with a working form**

```tsx
import { useEffect, useState } from "react";
import { useMe, useUpdateMe } from "../features/auth/hooks";
import { G } from "../lib/design";

const TONES = [
  { id: "friendly", label: "Дружелюбный" },
  { id: "formal", label: "Деловой" },
  { id: "direct", label: "Прямой" },
];

const inputStyle: React.CSSProperties = {
  width: "100%", borderRadius: "8px", border: "1.5px solid rgba(0,0,0,0.12)",
  padding: "10px 12px", fontSize: "14px", fontFamily: "inherit",
  color: G.textPrimary, outline: "none", boxSizing: "border-box",
};
const labelStyle: React.CSSProperties = {
  fontSize: "12.5px", fontWeight: 600, color: G.textSecondary,
  display: "block", marginBottom: "6px",
};

export default function SettingsPage() {
  const { data: me } = useMe();
  const update = useUpdateMe();
  const [fullName, setFullName] = useState("");
  const [business, setBusiness] = useState("");
  const [offer, setOffer] = useState("");
  const [city, setCity] = useState("");
  const [tone, setTone] = useState("friendly");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!me) return;
    setFullName(me.full_name ?? "");
    setBusiness(me.business_profile?.business ?? "");
    setOffer(me.business_profile?.offer ?? "");
    setCity(me.business_profile?.city ?? "");
    setTone(me.business_profile?.tone_default ?? "friendly");
  }, [me]);

  async function save() {
    await update.mutateAsync({
      full_name: fullName || undefined,
      business_profile: { business, offer, city, tone_default: tone },
    });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <div style={{
        height: "52px", display: "flex", alignItems: "center", padding: "0 24px",
        background: "rgba(255,255,255,0.45)", backdropFilter: G.blur, WebkitBackdropFilter: G.blur,
        borderBottom: G.borderSubtle, flexShrink: 0,
      }}>
        <span style={{ fontSize: "14px", fontWeight: 700, color: G.textPrimary }}>Настройки</span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        <div style={{ maxWidth: "560px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "16px" }}>

          <div style={{ borderRadius: G.radius, border: G.border, background: "rgba(255,255,255,0.50)", backdropFilter: G.blur, boxShadow: G.shadowCard, padding: "20px 24px" }}>
            <div style={{ fontSize: "15px", fontWeight: 700, color: G.textPrimary, marginBottom: "16px" }}>Профиль бизнеса</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label htmlFor="fullName" style={labelStyle}>Ваше имя</label>
                <input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Иван Иванов" style={inputStyle} />
              </div>
              <div>
                <label htmlFor="city" style={labelStyle}>Город / регион</label>
                <input id="city" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Москва" style={inputStyle} />
              </div>
              <div>
                <label htmlFor="business" style={labelStyle}>Чем занимается ваш бизнес?</label>
                <textarea id="business" value={business} onChange={(e) => setBusiness(e.target.value)} rows={3} placeholder="Разрабатываем сайты для малого бизнеса" style={{ ...inputStyle, resize: "none" }} />
              </div>
              <div>
                <label htmlFor="offer" style={labelStyle}>Что предлагаете клиентам?</label>
                <textarea id="offer" value={offer} onChange={(e) => setOffer(e.target.value)} rows={3} placeholder="Лендинг под ключ за 2 недели" style={{ ...inputStyle, resize: "none" }} />
              </div>
              <div>
                <label htmlFor="tone" style={labelStyle}>Тон писем</label>
                <select id="tone" value={tone} onChange={(e) => setTone(e.target.value)} style={inputStyle}>
                  {TONES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "20px" }}>
              <button
                onClick={save}
                disabled={update.isPending}
                style={{
                  height: "38px", padding: "0 18px", borderRadius: G.radiusSm, border: "none",
                  background: G.navy, color: "white", fontSize: "13.5px", fontWeight: 600,
                  cursor: update.isPending ? "default" : "pointer", fontFamily: "inherit",
                  boxShadow: G.shadowBtn, opacity: update.isPending ? 0.6 : 1,
                }}
              >
                {update.isPending ? "Сохраняем…" : "Сохранить"}
              </button>
              {saved && <span style={{ fontSize: "13px", color: G.green }}>Сохранено</span>}
            </div>
          </div>

          <div style={{ borderRadius: G.radius, border: G.border, background: "rgba(255,255,255,0.50)", backdropFilter: G.blur, boxShadow: G.shadowCard, padding: "20px 24px" }}>
            <div style={{ fontSize: "15px", fontWeight: 700, color: G.textPrimary, marginBottom: "12px" }}>Тариф</div>
            <div style={{ display: "flex", gap: "24px", fontSize: "13px", color: G.textSecondary }}>
              <div><span style={{ color: G.textMuted }}>План: </span><b style={{ color: G.textPrimary }}>{me?.plan ?? "—"}</b></div>
              <div><span style={{ color: G.textMuted }}>Лиды: </span><b style={{ color: G.textPrimary }}>{me?.leads_quota ?? "—"}</b></div>
              <div><span style={{ color: G.textMuted }}>Отправки: </span><b style={{ color: G.textPrimary }}>{me?.sends_quota ?? "—"}</b></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + lint**

Run (from `frontend/`):
```bash
npm run build
npm run lint
```
Expected: build + lint pass. If `G.shadowCard` / `G.radiusSm` / `G.green` are missing from `lib/design`, check the exports in `frontend/src/lib/design.ts` and use the existing nearest token (e.g. `G.shadow`, `G.radius`) — do not invent new tokens.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx
git commit -m "feat(ui): working Settings page for business profile"
```

---

### Task 3: Template outreach for light/basic leads

Today only Deep-AI leads with score ≥ 50 get an outreach message; most leads stay `ai=light` with no message. Add a deterministic, no-LLM, anti-hallucination `template_outreach()` that builds a starter message from facts already on the lead. Wire it as a fallback so every saved lead gets a message when outreach is requested — without spending credits.

**Files:**
- Modify: `backend/app/services/leads/outreach.py` (add `template_outreach`)
- Modify: `backend/app/services/leads/pipeline.py:32` (import) and `:1101` (wire fallback)
- Test: `backend/tests/test_outreach_template.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_outreach_template.py`:

```python
from app.services.leads.outreach import template_outreach


def test_template_outreach_uses_company_and_service():
    out = template_outreach(
        service_offered="разработка сайтов",
        company_name="Улыбка",
        industry="стоматология",
        description=None,
        reason_to_contact=None,
    )
    assert out["email_subject"]
    assert "Улыбка" in out["email_body"]
    assert "разработка сайтов" in out["email_body"]
    assert out["telegram_message"]
    assert out["regeneration_count"] == 0
    # anti-hallucination: no leaked placeholders or None
    assert "None" not in out["email_body"]
    assert "{" not in out["email_body"]


def test_template_outreach_handles_missing_company():
    out = template_outreach(
        service_offered="SEO",
        company_name=None,
        industry=None,
        description=None,
        reason_to_contact=None,
    )
    assert out["email_subject"]
    assert out["email_body"]
    assert "None" not in out["email_subject"]
    assert "None" not in out["email_body"]
    assert out["telegram_message"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `backend/`):
```bash
python -m pytest tests/test_outreach_template.py -v
```
Expected: FAIL with `ImportError: cannot import name 'template_outreach'`.

- [ ] **Step 3: Implement template_outreach**

Append to `backend/app/services/leads/outreach.py`:

```python
def template_outreach(
    *,
    service_offered: str,
    company_name: str | None,
    industry: str | None,
    description: str | None,
    reason_to_contact: str | None,
) -> dict:
    """Deterministic outreach for light/basic leads. No LLM, no credits.

    Uses only the facts passed in — never invents company details.
    """
    name = (company_name or "").strip()
    service = (service_offered or "услуги").strip()
    addressee = name or "вашей компании"

    subject = f"Предложение для {addressee}"

    intro = f"Здравствуйте! Изучил сайт {name}" if name else "Здравствуйте! Посмотрел ваш сайт"
    industry_part = (industry or "").strip()
    industry_clause = f" — вижу, вы работаете в нише «{industry_part}»." if industry_part else "."
    reason_part = (reason_to_contact or "").strip()
    reason_clause = f" {reason_part}" if reason_part else ""
    offer_clause = f" Я занимаюсь: {service}."
    cta = " Если интересно, подскажите — удобно ли коротко созвониться?"
    email_body = f"{intro}{industry_clause}{reason_clause}{offer_clause}{cta}"

    tg_name = f" {name}" if name else ""
    telegram = f"Здравствуйте! Посмотрел сайт{tg_name}. Я занимаюсь: {service}. Удобно коротко обсудить?"

    return {
        "email_subject": subject,
        "email_body": email_body,
        "telegram_message": telegram,
        "regeneration_count": 0,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run (from `backend/`):
```bash
python -m pytest tests/test_outreach_template.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Import template_outreach in the pipeline**

In `backend/app/services/leads/pipeline.py`, change line 32 from:

```python
from app.services.leads.outreach import generate_outreach
```
to:
```python
from app.services.leads.outreach import generate_outreach, template_outreach
```

- [ ] **Step 6: Wire the fallback after the Deep-AI outreach block**

In `backend/app/services/leads/pipeline.py`, immediately AFTER the existing Deep-AI outreach block (the `try/except` ending around line 1099, where `outreach_data = {}` on failure) and BEFORE the `# Build Lead record` comment (~line 1101), insert:

```python
        # Template fallback — light/basic leads still get a starter message (no credits)
        if generate_outreach_messages and not outreach_data:
            outreach_data = template_outreach(
                service_offered=service_offered,
                company_name=deep_data.get("company_name") or raw.get("name"),
                industry=deep_data.get("industry") or (light_result.industry if light_result else None),
                description=description,
                reason_to_contact=deep_data.get("reason_to_contact") or (light_result.hook if light_result else None),
            )
```

Note: `outreach_data` starts as `{}` (truthy-empty). It is only non-empty when Deep-AI outreach already ran, so `not outreach_data` correctly limits the template to light/basic leads. When `generate_outreach_messages` is False, nothing changes.

- [ ] **Step 7: Run the full backend suite to confirm no regressions**

Run (from `backend/`):
```bash
python -m pytest tests/test_outreach_template.py tests/test_lead_pipeline.py tests/test_lead_search_api.py -q
```
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/leads/outreach.py backend/app/services/leads/pipeline.py backend/tests/test_outreach_template.py
git commit -m "feat(leads): template outreach fallback for light leads"
```

---

## Self-Review

- **Spec coverage:** Task 1 = remove Companies (chosen). Task 2 = Settings page (chosen). Task 3 = more leads get outreach text (chosen). CompanyPage card (earlier multi-select) is superseded by the "remove Companies" decision.
- **Type consistency:** `template_outreach` returns the same keys as `generate_outreach` (`email_subject`, `email_body`, `telegram_message`, `regeneration_count`) so the downstream `personalized_outreach` field stays uniform. `useUpdateMe` payload shape matches `UserUpdate` / `BusinessProfile`.
- **No placeholders:** all steps contain full code and exact commands.
