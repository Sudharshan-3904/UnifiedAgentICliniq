import os
from pydantic_settings import BaseSettings
import dotenv
dotenv.load_dotenv()


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AGENT_MODEL: str = os.getenv("AGENT_MODEL")
    SAFETY_MODEL: str = os.getenv("SAFETY_MODEL")
    
    # External APIs
    NCBI_API_KEY: str = os.getenv("NCBI_API_KEY")
    NCBI_EMAIL: str = os.getenv("NCBI_EMAIL")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    LOG_LEVEL: str = "INFO"
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR: str = os.path.join(BASE_DIR, "logs")

    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env

settings = Settings()
