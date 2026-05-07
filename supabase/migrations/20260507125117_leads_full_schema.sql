-- Full leads schema per CLAUDE.md §6 Lead JSON Schema
-- Creates lead_lists and leads tables (were only Python models, never in SQL)

create extension if not exists citext with schema extensions;

create table if not exists public.lead_lists (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    name text not null,
    source text not null default 'search',
    source_meta jsonb,
    total_count int not null default 0,
    created_at timestamptz not null default now()
);
create index if not exists idx_lead_lists_user_id on public.lead_lists(user_id);

create table if not exists public.leads (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    list_id uuid references public.lead_lists(id) on delete cascade,
    campaign_id uuid references public.campaigns(id) on delete set null,

    -- Identity
    domain text,
    website text,
    company_name text,
    city text,
    region text,
    address text,
    industry text,
    description text,
    services jsonb,

    -- Contacts
    email citext,
    phone text,
    telegram text,
    whatsapp text,
    vk text,
    instagram text,
    has_contact_form bool not null default false,

    -- Decision maker
    decision_maker jsonb,

    -- Website quality
    website_quality jsonb,

    -- Lead scoring
    lead_fit jsonb,
    pain_points jsonb,
    reason_to_contact text,

    -- Outreach
    personalized_outreach jsonb,

    -- Processing metadata
    processing jsonb,

    -- Cache invalidation fields
    content_hash text,
    last_scraped_at timestamptz,
    cache_valid bool not null default true,

    created_at timestamptz not null default now()
);
create index if not exists idx_leads_user_id on public.leads(user_id);
create index if not exists idx_leads_list_id on public.leads(list_id);
create index if not exists idx_leads_domain on public.leads(domain) where domain is not null;
create index if not exists idx_leads_email on public.leads(email) where email is not null;
create unique index if not exists uq_leads_user_domain on public.leads(user_id, domain) where domain is not null;

alter table public.lead_lists enable row level security;
alter table public.leads enable row level security;

create policy "lead_lists_owner" on public.lead_lists
    using (user_id = auth.uid());

create policy "leads_owner" on public.leads
    using (user_id = auth.uid());
