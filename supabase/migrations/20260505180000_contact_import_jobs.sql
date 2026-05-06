create table if not exists public.contact_import_jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    filename text not null,
    content_type text,
    payload bytea not null,
    status text not null default 'pending',
    created_at timestamptz not null default now(),
    expires_at timestamptz not null
);

create index if not exists idx_contact_import_jobs_user_id
    on public.contact_import_jobs(user_id);

create index if not exists idx_contact_import_jobs_expires_at
    on public.contact_import_jobs(expires_at);
