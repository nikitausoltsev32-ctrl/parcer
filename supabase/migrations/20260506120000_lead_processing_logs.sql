create table if not exists public.lead_processing_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    contact_list_id uuid references public.contact_lists(id) on delete set null,
    search_query_original text not null default '',
    search_queries_generated jsonb,
    urls_found int not null default 0,
    urls_after_filter int not null default 0,
    urls_crawled int not null default 0,
    pages_crawled_total int not null default 0,
    llm_calls jsonb,
    total_cost_usd numeric(10, 6),
    ai_credits_used int not null default 0,
    outcome text not null default 'success',
    failure_reason text,
    meta jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_lead_processing_logs_user_id_created_at
    on public.lead_processing_logs(user_id, created_at desc);

create index if not exists idx_lead_processing_logs_contact_list_id
    on public.lead_processing_logs(contact_list_id);
