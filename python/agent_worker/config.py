from dataclasses import dataclass
from dotenv import load_dotenv
import os
from urllib.parse import urljoin

@dataclass
class OpenAIConfig:
    deployment_name: str
    temperature: float
    max_retries: int
    api_version: str

@dataclass
class AppConfig:
    api_url: str
    openai: OpenAIConfig

    @property
    def sse_url(self) -> str:
        return urljoin(self.api_url, "/api/streams/notifications")

def load_config() -> AppConfig:
    load_dotenv()
    
    openai_config = OpenAIConfig(
        deployment_name=os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
        api_version=os.getenv("OPENAI_API_VERSION", "2024-08-01-preview")
    )
    
    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("API_URL environment variable is not set")
    
    return AppConfig(
        api_url=api_url,
        openai=openai_config
    ) 