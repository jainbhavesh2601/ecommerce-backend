from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENVIRONMENT: str = "development"
    
    # Email configuration
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str | None = None
    EMAIL_PASSWORD: str | None = None
    EMAIL_FROM: str = "noreply@artisansalley.com"
    EMAIL_USE_TLS: bool = True
    
    # Frontend URL for email verification links
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Payment configuration
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    
    # PayPal
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # 'sandbox' or 'live'
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    
    # Manual payments
    MANUAL_PAYMENT_AUTO_APPROVE: bool = False
    
    # Payment simulation mode (True = mock providers, False = real providers)
    PAYMENT_SIMULATION_MODE: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

Config = Settings()