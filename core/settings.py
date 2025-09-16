from datetime import timedelta
from authx import AuthX, AuthXConfig
from fastapi import FastAPI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REQURV_", env_file=".env", env_file_encoding="utf-8"
    )

    requrv_database_url: str = Field("")
    requrv_hive_endpoint: str = Field("")
    requrv_master_key: str = Field("")
    requrv_secret_key: str = Field("")
    requrv_smtp_server: str = Field("")
    requrv_smtp_user: str = Field("")
    requrv_smtp_key: str = Field("")
    requrv_otp_key: str = Field("")
    requrv_lago_endpoint: str = Field("")
    requrv_lago_api_key: str = Field("")
    requrv_lago_webhook_secret: str = Field("")
    requrv_brave_api_key: str = Field("")
    requrv_aws_access_key_id: str = Field("")
    requrv_aws_secret_access_key: str = Field("")
    requrv_aws_endpoint: str = Field("")
    requrv_aws_region: str = Field("")
    requrv_aws_bucket: str = Field("")
    
    # OAuth2 settings
    requrv_google_client_id: str = Field("")
    requrv_google_client_secret: str = Field("")
    requrv_google_redirect_uri: str = Field("http://localhost:8000/auth/google")

    requrv_github_client_id: str = Field("")
    requrv_github_client_secret: str = Field("")
    requrv_github_redirect_uri: str = Field("http://localhost:8000/auth/github/callback")
    
    requrv_apple_client_id: str = Field("")
    requrv_apple_key_id: str = Field("")
    requrv_apple_team_id: str = Field("")
    requrv_apple_private_key: str = Field("")
    # requrv_apple_client_secret: str = Field("")
    # requrv_apple_redirect_uri: str = Field("http://localhost:8000/auth/apple/callback")
    
    requrv_fe_url: str = Field("http://localhost:3000")
    requrv_fe_auth_callback: str = Field("http://localhost:3000/auth/callback")

    # Session middleware secret (for OAuth state management)
    requrv_session_secret: str = Field("")
    



settings = Settings()

jwt_secret = settings.model_dump()["requrv_secret_key"]

auth_config = AuthXConfig(
    JWT_ALGORITHM="HS256",
    JWT_SECRET_KEY=jwt_secret,
    JWT_TOKEN_LOCATION=["headers"],
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=300),
)
auth = AuthX(config=auth_config)


def config_auth(app: FastAPI):
    auth.handle_errors(app)
