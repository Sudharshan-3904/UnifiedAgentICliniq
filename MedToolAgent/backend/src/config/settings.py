import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AGENT_MODEL: str = "gemma3"
    SAFETY_MODEL: str = "gemma3"
    
    # External APIs
    NCBI_API_KEY: str = ""
    NCBI_EMAIL: str = ""
    GOOGLE_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR: str = os.path.join(BASE_DIR, "logs")

    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env

settings = Settings()
