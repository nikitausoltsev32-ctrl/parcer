from app.workers.main import _psycopg_conninfo


def test_psycopg_conninfo_uses_database_url_without_asyncpg_driver_or_pgbouncer_flag():
    conninfo = _psycopg_conninfo(
        "postgresql+asyncpg://user:pass@example.supabase.com:5432/postgres?pgbouncer=true"
    )

    assert conninfo == "postgresql://user:pass@example.supabase.com:5432/postgres?sslmode=require"
