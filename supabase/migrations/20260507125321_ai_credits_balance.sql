-- Add ai_credits_balance to users
-- Separate from leads_quota/sends_quota — tracks LLM operation credits per CLAUDE.md §7

alter table public.users
    add column if not exists ai_credits_balance int not null default 0;

comment on column public.users.ai_credits_balance is
    'AI operation credits. Costs: light_ai=1, deep_ai=5, premium=15, outreach=3. See CLAUDE.md §7';
