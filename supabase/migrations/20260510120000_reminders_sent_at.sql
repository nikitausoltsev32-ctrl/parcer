alter table public.reminders
    add column if not exists sent_at timestamptz;

create index if not exists reminders_due_unsent_idx
    on public.reminders(remind_at)
    where sent_at is null and status = 'pending';
