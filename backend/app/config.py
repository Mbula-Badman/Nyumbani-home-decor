from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Nyumbani Home API"
    app_env: str = "development"
    database_url: str = "sqlite:///./nyumbani.db"
    migration_database_url: str = ""
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000"
    auth_secret: str = ""
    admin_email: str = ""

    # M-Pesa / Daraja. Values come from .env only, never from frontend code.
    mpesa_env: str = "sandbox"
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_passkey: str = ""
    mpesa_shortcode: str = ""
    mpesa_party_b: str = ""
    mpesa_transaction_type: str = "CustomerPayBillOnline"
    mpesa_callback_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def mpesa_missing_variables(self) -> list[str]:
        missing = [
            variable
            for variable, value in (
                ("MPESA_CONSUMER_KEY", self.mpesa_consumer_key),
                ("MPESA_CONSUMER_SECRET", self.mpesa_consumer_secret),
                ("MPESA_PASSKEY", self.mpesa_passkey),
                ("MPESA_SHORTCODE", self.mpesa_shortcode),
                ("MPESA_CALLBACK_URL", self.mpesa_callback_url),
            )
            if not value.strip()
        ]
        if self.mpesa_env.strip() not in ("sandbox", "production"):
            missing.append("MPESA_ENV (sandbox or production)")
        if self.mpesa_transaction_type not in ("CustomerPayBillOnline", "CustomerBuyGoodsOnline"):
            missing.append("MPESA_TRANSACTION_TYPE (CustomerPayBillOnline or CustomerBuyGoodsOnline)")
        if self.mpesa_transaction_type == "CustomerBuyGoodsOnline" and not self.mpesa_party_b.strip():
            missing.append("MPESA_PARTY_B (sandbox Till number)")
        if self.mpesa_callback_url:
            callback = urlparse(self.mpesa_callback_url.strip())
            if callback.scheme != "https" or not callback.hostname or callback.path.rstrip("/") != "/api/mpesa/callback":
                missing.append("MPESA_CALLBACK_URL (public HTTPS URL ending in /api/mpesa/callback)")
        return missing


settings = Settings()
