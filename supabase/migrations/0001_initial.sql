-- parcer initial schema
-- Generated from docs/PROJECT.md §6

create extension if not exists "pgcrypto";
create extension if not exists "citext";

-- ===== users =====
create table public.users (
    id uuid primary key default gen_random_uuid(),
    email citext not null unique,
    password_hash text not null,
    email_verified_at timestamptz,
    full_name text,
    business_profile jsonb,
    llm_consent_at timestamptz,
    plan text not null default 'trial',
    leads_quota int not null default 50,
    sends_quota int not null default 50,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ===== companies =====
create table public.companies (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    name text not null,
    website text,
    industry text,
    city text,
    size text,
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index on public.companies(user_id);

-- ===== contact_lists =====
create table public.contact_lists (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    name text not null,
    source text not null,
    source_meta jsonb,
    total_count int not null default 0,
    created_at timestamptz not null default now()
);
create index on public.contact_lists(user_id);

-- ===== contacts =====
create table public.contacts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    company_id uuid references public.companies(id) on delete set null,
    list_id uuid references public.contact_lists(id) on delete set null,
    contact_name text,
    email citext,
    phone text,
    position text,
    status text not null default 'new',
    next_step text,
    next_step_at timestamptz,
    email_valid bool,
    enrichment jsonb,
    raw jsonb,
    created_at timestamptz not null default now()
);
create index on public.contacts(user_id, status);
create index on public.contacts(company_id);
create index on public.contacts(email) where email is not null;

-- ===== smtp_accounts =====
create table public.smtp_accounts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    provider text not null,
    from_email citext not null,
    from_name text,
    host text not null,
    port int not null,
    username text not null,
    password_encrypted bytea not null,
    imap_host text,
    imap_port int,
    last_verified_at timestamptz,
    daily_limit int not null default 30,
    is_active bool not null default true
);
create index on public.smtp_accounts(user_id);

-- ===== suppressions =====
create table public.suppressions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    email citext not null,
    reason text not null,
    created_at timestamptz not null default now(),
    unique (user_id, email)
);

-- ===== templates =====
create table public.templates (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.users(id) on delete cascade,  -- null = built-in
    name text not null,
    template_id text not null,
    tone text not null default 'friendly',
    language text not null default 'ru',
    custom_instruction text
);
create index on public.templates(user_id);

-- ===== campaigns =====
create table public.campaigns (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    list_id uuid not null references public.contact_lists(id),
    template_id uuid not null references public.templates(id),
    smtp_account_id uuid not null references public.smtp_accounts(id),
    llm_provider text not null,
    llm_model text not null,
    send_rate_per_hour int not null default 30,
    scheduled_at timestamptz,
    status text not null default 'draft',
    stats jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index on public.campaigns(user_id, status);

-- ===== campaign_messages =====
create table public.campaign_messages (
    id uuid primary key default gen_random_uuid(),
    campaign_id uuid not null references public.campaigns(id) on delete cascade,
    contact_id uuid not null references public.contacts(id),
    subject text,
    body text,
    body_edited bool not null default false,
    status text not null default 'pending',
    tracking_id uuid not null unique default gen_random_uuid(),
    sent_at timestamptz,
    opened_at timestamptz,
    clicked_at timestamptz,
    replied_at timestamptz,
    error text
);
create index on public.campaign_messages(campaign_id, status);

-- ===== activities =====
create table public.activities (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    contact_id uuid references public.contacts(id) on delete cascade,
    company_id uuid references public.companies(id) on delete cascade,
    type text not null,
    body text,
    meta jsonb,
    created_at timestamptz not null default now()
);
create index on public.activities(contact_id, created_at desc);
create index on public.activities(user_id, created_at desc);

-- ===== inbox_messages =====
create table public.inbox_messages (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    smtp_account_id uuid not null references public.smtp_accounts(id) on delete cascade,
    campaign_id uuid references public.campaigns(id) on delete set null,
    contact_id uuid references public.contacts(id) on delete set null,
    message_id text,
    from_email citext,
    subject text,
    body_text text,
    received_at timestamptz,
    classification text,
    classification_confidence float,
    raw jsonb,
    created_at timestamptz not null default now()
);
create index on public.inbox_messages(user_id, received_at desc);
create index on public.inbox_messages(campaign_id);

-- ===== chat_sessions / chat_messages =====
create table public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    title text,
    started_at timestamptz not null default now(),
    last_message_at timestamptz
);
create index on public.chat_sessions(user_id, last_message_at desc);

create table public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.chat_sessions(id) on delete cascade,
    role text not null,
    content text,
    tool_calls jsonb,
    tool_results jsonb,
    created_at timestamptz not null default now()
);
create index on public.chat_messages(session_id, created_at);

-- ===== reminders =====
create table public.reminders (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    contact_id uuid not null references public.contacts(id) on delete cascade,
    remind_at timestamptz not null,
    action text not null,
    status text not null default 'pending',
    created_at timestamptz not null default now()
);
create index on public.reminders(remind_at) where status = 'pending';

-- ===== events =====
create table public.events (
    id bigserial primary key,
    message_id uuid references public.campaign_messages(id) on delete set null,
    campaign_id uuid references public.campaigns(id) on delete set null,
    user_id uuid references public.users(id) on delete set null,
    type text not null,
    meta jsonb,
    created_at timestamptz not null default now()
);
create index on public.events(campaign_id);
create index on public.events(user_id, created_at desc);

-- ===== llm_cache =====
create table public.llm_cache (
    key text primary key,
    output jsonb not null,
    created_at timestamptz not null default now()
);
