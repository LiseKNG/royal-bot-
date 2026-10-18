from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/community_suite"
    app_secret: str = "CHANGE_ME"
    web_admin_token: str = "CHANGE_ME_TOO"
    public_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def async_database_url(self) -> str:
        # Railway's DATABASE_URL is often postgres:// or postgresql://.
        # SQLAlchemy async needs the asyncpg dialect.
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

settings = Settings()
