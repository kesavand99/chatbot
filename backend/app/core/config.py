from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:latest"
    
    # AI Personality & Quality
    system_prompt: str = (
        "You are NexusAI, a highly intelligent, helpful, and professional AI assistant. "
        "Provide accurate, concise, and well-formatted answers. If you don't know something, "
        "be honest about it. Always strive to be as helpful as possible."
    )
    
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_db: str = "ai_chatbot"
    client_origins: str = "http://localhost:5173,http://localhost:8080,http://127.0.0.1:8080,http://192.168.0.17:8080/"

    # SMTP Settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    sender_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()

def get_allowed_origins() -> list[str]:
    return [origin.strip() for origin in settings.client_origins.split(",") if origin.strip()]
