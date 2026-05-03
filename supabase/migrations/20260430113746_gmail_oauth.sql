-- smtp_accounts: make SMTP fields nullable for OAuth accounts, add OAuth token columns
alter table public.smtp_accounts
    alter column password_encrypted drop not null,
    alter column host drop not null,
    alter column port drop not null,
    alter column username drop not null;

alter table public.smtp_accounts
    add column if not exists oauth_refresh_token text,
    add column if not exists oauth_access_token  text,
    add column if not exists oauth_expires_at     timestamptz;
