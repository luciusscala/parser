"""Configuration and settings management."""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    # Timeout Configuration (in milliseconds)
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "6000"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30000"))
    
    # Prompt file path
    PROMPT_FILE: str = os.getenv("PROMPT_FILE", "prompts/prompt.txt")
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")


# Global settings instance
settings = Settings()

