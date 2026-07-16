from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "GovTracker RD"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://govtracker:govtracker2024@db:5432/govtracker_rd"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://govtracker:govtracker2024@db:5432/govtracker_rd"

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # AI
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Security
    SECRET_KEY: str = "govtracker-rd-secret-key-change-in-production-2024"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # DGCP API
    DGCP_API_BASE: str = "https://api.dgcp.gob.do/api"
    DGCP_PORTAL_URL: str = "https://www.dgcp.gob.do"

    # Hacienda
    HACIENDA_API_BASE: str = "https://www.hacienda.gob.do"
    HACIENDA_DATOS_ABIERTOS: str = "https://datos.hacienda.gob.do"

    # Cámara de Cuentas
    CAMARA_CUENTAS_URL: str = "https://www.camaradecuentas.gob.do"

    # Crédito Público
    CREDITO_PUBLICO_URL: str = "https://www.creditopublico.gob.do"

    # Scraper
    SCRAPER_DELAY: float = 1.5
    SCRAPER_MAX_RETRIES: int = 3
    USER_AGENT: str = "Mozilla/5.0 (compatible; GovTrackerRD/1.0; +https://govtracker.rd)"

    # Storage
    DOCUMENTS_PATH: str = "/app/data/documents"
    EXPORTS_PATH: str = "/app/data/exports"

    # Alerts
    ALERT_CONTRACT_THRESHOLD: float = 100_000_000  # RD$100M
    ALERT_COMPANY_CONTRACT_COUNT: int = 20
    ALERT_ADDENDUM_COUNT: int = 3
    ALERT_PRICE_INCREASE_PCT: float = 25.0
    ALERT_ANOMALY_THRESHOLD: float = 5_000_000_000  # RD$5,000M — solo 15 contratos en 10 años cruzan esta línea
    ALERT_CAPTIVE_CONCENTRATION_PCT: float = 90.0
    ALERT_CAPTIVE_MIN_MONTO: float = 50_000_000  # RD$50M
    ALERT_CONCENTRACION_MIN_MONTO: float = 20_000_000  # ver Task 12 — umbral calibrado con datos reales

    # Notificaciones
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    GMAIL_USER: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None
    ALERT_EMAIL_TO: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
