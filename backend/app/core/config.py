from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

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
    database_ssl_verify: bool = True
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "parcer-dev"

    # LLM providers
    llm_chat_provider: str = "nvidia"
    llm_chat_model: str = "z-ai/glm-5.1"
    llm_letters_provider: str = "nvidia"
    llm_letters_model: str = "z-ai/glm-5.1"
    llm_classify_provider: str = "nvidia"
    llm_classify_model: str = "z-ai/glm-5.1"
    # Enrichment: disabled | qwen | groq | glm | nvidia | claude
    llm_enrich_provider: str = "nvidia"
    llm_enrich_model: str = "z-ai/glm-5.1"
    llm_consent_required: bool = True

    groq_api_key: str = ""
    qwen_api_key: str = ""
    glm_api_key: str = ""
    nvidia_api_key: str = ""
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""

    # Search
    serpapi_key: str = ""
    yandex_maps_api_key: str = ""
    firecrawl_api_key: str = ""
    hunter_api_key: str = ""

    # Transactional email
    transactional_smtp_host: str = ""
    transactional_smtp_port: int = 465
    transactional_smtp_user: str = ""
    transactional_smtp_pass: str = ""
    transactional_from_email: str = "noreply@parcer.ru"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/smtp-accounts/gmail/oauth/callback"

    # Monitoring
    sentry_dsn: str = ""

settings = Settings()
