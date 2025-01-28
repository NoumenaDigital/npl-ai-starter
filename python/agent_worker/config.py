from dataclasses import dataclass
from dotenv import load_dotenv
import os
from urllib.parse import urljoin
from typing import Optional, Literal
from pydantic import BaseModel

LLMProvider = Literal["azure-openai", "bedrock"]

@dataclass
class AzureOpenAIConfig:
    deployment_name: str
    temperature: float
    max_retries: int
    api_version: str

class BedrockConfig(BaseModel):
    """Configuration for AWS Bedrock."""
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    temperature: float = 0.0
    max_tokens: Optional[int] = None

@dataclass
class AppConfig:
    api_url: str
    llm_provider: LLMProvider
    azure_openai: Optional[AzureOpenAIConfig] = None
    bedrock: Optional[BedrockConfig] = None

    @property
    def sse_url(self) -> str:
        return urljoin(self.api_url, "/api/streams/notifications")

def load_config() -> AppConfig:
    load_dotenv()
    
    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("API_URL environment variable is not set")

    llm_provider = os.getenv("LLM_PROVIDER", "bedrock").lower()
    if llm_provider not in ("bedrock", "azure-openai"):
        raise ValueError("LLM_PROVIDER must be either 'azure-openai' or 'bedrock'")

    config_args = {
        "api_url": api_url,
        "llm_provider": llm_provider
    }

    if llm_provider == "bedrock":
        config_args["bedrock"] = BedrockConfig(
            model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
            temperature=float(os.getenv("BEDROCK_TEMPERATURE", "0")),
            max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "0")) or None
        )
    elif llm_provider == "azure-openai":
        config_args["azure-openai"] = AzureOpenAIConfig(
            deployment_name=os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")
        )

    return AppConfig(**config_args) 
