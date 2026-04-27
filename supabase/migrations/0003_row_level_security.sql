-- Row Level Security: each table with user_id is isolated per authenticated user.
-- Note: our app uses its own JWT (not Supabase Auth), so RLS relies on a request-time
-- setting (`request.jwt.claim.sub`). The backend sets this via `set_config` per request.
-- When using `service_role_key` (backend-only), RLS is bypassed — this is intentional.

-- Helper function: returns the current user_id from JWT or null.
create or replace function public.current_user_id() returns uuid
language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

-- Enable RLS
alter table public.users enable row level security;
alter table public.companies enable row level security;
alter table public.contact_lists enable row level security;
alter table public.contacts enable row level security;
alter table public.smtp_accounts enable row level security;
alter table public.suppressions enable row level security;
alter table public.templates enable row level security;
alter table public.campaigns enable row level security;
alter table public.campaign_messages enable row level security;
alter table public.activities enable row level security;
alter table public.inbox_messages enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.reminders enable row level security;
alter table public.events enable row level security;

-- Policies: user sees only own rows
create policy user_own on public.users for all using (id = public.current_user_id());
create policy user_own on public.companies for all using (user_id = public.current_user_id());
create policy user_own on public.contact_lists for all using (user_id = public.current_user_id());
create policy user_own on public.contacts for all using (user_id = public.current_user_id());
create policy user_own on public.smtp_accounts for all using (user_id = public.current_user_id());
create policy user_own on public.suppressions for all using (user_id = public.current_user_id());
create policy user_own on public.templates for all using (user_id is null or user_id = public.current_user_id());
create policy user_own on public.campaigns for all using (user_id = public.current_user_id());
create policy user_own on public.activities for all using (user_id = public.current_user_id());
create policy user_own on public.inbox_messages for all using (user_id = public.current_user_id());
create policy user_own on public.chat_sessions for all using (user_id = public.current_user_id());
create policy user_own on public.reminders for all using (user_id = public.current_user_id());
create policy user_own on public.events for all using (user_id = public.current_user_id());

-- campaign_messages and chat_messages are child tables — join through parent
create policy user_own on public.campaign_messages for all using (
  exists (select 1 from public.campaigns c where c.id = campaign_id and c.user_id = public.current_user_id())
);
create policy user_own on public.chat_messages for all using (
  exists (select 1 from public.chat_sessions s where s.id = session_id and s.user_id = public.current_user_id())
);
