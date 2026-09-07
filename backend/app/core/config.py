from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Agent Bank"
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECRET_KEY_IN_PRODUCTION"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # DEMO MODE: the app must run with zero external keys. When enabled (or left
    # blank) we use the mock AI provider, the demo service marketplace, mock
    # payment (simulated USDC) and deterministic demo tasks. Every simulated
    # transaction is explicitly labelled and never misrepresented.
    #   DEMO_MODE=true  -> demo components on
    #   DEMO_MODE=false -> real components only (requires keys)
    #   DEMO_MODE=      -> demo components on (safe default for a hackathon)
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").strip().lower() not in (
        "false",
        "0",
        "off",
        "no",
    )

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "aibank")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    @property
    def assembled_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    DATABASE_URL: Optional[str] = None

    # Solana
    # Blank by default. Set SOLANA_RPC_URL + SOLANA_PRIVATE_KEY to enable the
    # real payment path (USE_REAL_PAYMENT=true). Blank RPC = MOCK MODE.
    SOLANA_RPC_URL: str = os.getenv("SOLANA_RPC_URL", "")
    SOLANA_NETWORK: str = os.getenv("SOLANA_NETWORK", "devnet")
    SOLANA_USDC_MINT: str = os.getenv("SOLANA_USDC_MINT", "")
    SOLANA_PRIVATE_KEY: str = os.getenv("SOLANA_PRIVATE_KEY", "")
    NEXT_PUBLIC_SOLANA_RPC_URL: str = os.getenv("NEXT_PUBLIC_SOLANA_RPC_URL", "")
    USE_REAL_PAYMENT: bool = os.getenv("USE_REAL_PAYMENT", "false").lower() == "true"

    # AI API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY", "")

    # Fernet key (urlsafe base64 of 32 bytes) used to encrypt end-user-supplied
    # LLM API keys at rest. If blank we derive a stable key from SECRET_KEY so
    # the feature works out of the box — set a real value in production.
    LLM_KEY_ENCRYPTION_KEY: str = os.getenv("LLM_KEY_ENCRYPTION_KEY", "")

    # Other services
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    HELIUS_API_KEY: str = os.getenv("HELIUS_API_KEY", "")
    X402_API_KEY: str = os.getenv("X402_API_KEY", "")

    # Supabase (not used but kept for compatibility)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # Backend CORS origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    @property
    def resolved_database_url(self) -> str:
        """Return the DATABASE_URL if provided, otherwise construct from parts."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return self.assembled_database_url


settings = Settings()
