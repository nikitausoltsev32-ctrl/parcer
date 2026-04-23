from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    fernet_key: str = ""

    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"
    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "parcer-dev"

    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    yandex_gpt_api_key: str = ""
    yandex_gpt_folder_id: str = ""
    gigachat_client_id: str = ""
    gigachat_client_secret: str = ""

    transactional_smtp_host: str = ""
    transactional_smtp_port: int = 465
    transactional_smtp_user: str = ""
    transactional_smtp_pass: str = ""
    transactional_from_email: str = "noreply@parcer.ru"


settings = Settings()
