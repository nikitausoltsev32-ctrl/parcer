from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = "development"
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # Security
    secret_key: str = "dev-secret-change-me"
    fernet_key: str = ""
    tracking_secret: str = "dev-tracking-secret-change-me"

    # Database / Storage
    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"
    # Direct (non-pooler) URL for procrastinate worker — required for LISTEN/NOTIFY.
    # If not set, falls back to database_url (polling mode, works with pgbouncer).
    worker_database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "parcer-dev"

    # LLM providers
    llm_chat_provider: str = "groq"
    llm_chat_model: str = "llama-3.3-70b-versatile"
    llm_letters_provider: str = "qwen"
    llm_letters_model: str = "qwen2.5-72b-instruct"
    llm_classify_provider: str = "groq"
    llm_classify_model: str = "llama-3.1-8b-instant"
    # Enrichment: disabled | qwen | groq | glm | claude
    llm_enrich_provider: str = "disabled"
    llm_enrich_model: str = "qwen2.5-72b-instruct"
    llm_consent_required: bool = True

    groq_api_key: str = ""
    qwen_api_key: str = ""
    glm_api_key: str = ""
    anthropic_api_key: str = ""

    # Search
    twogis_api_key: str = ""
    serpapi_key: str = ""
    firecrawl_api_key: str = ""

    # Transactional email
    transactional_smtp_host: str = ""
    transactional_smtp_port: int = 465
    transactional_smtp_user: str = ""
    transactional_smtp_pass: str = ""
    transactional_from_email: str = "noreply@parcer.ru"

    # Monitoring
    sentry_dsn: str = ""

    @property
    def effective_worker_database_url(self) -> str:
        """Plain postgres:// URL for procrastinate (strips asyncpg driver prefix)."""
        url = self.worker_database_url or self.database_url
        return url.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()
