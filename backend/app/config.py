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
    mpesa_shortcode: str = ""  # TODO (CLIENT): Till Number or Paybill Number
    mpesa_transaction_type: str = "CustomerBuyGoodsOnline"  # Paybill: CustomerPayBillOnline
    mpesa_callback_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
