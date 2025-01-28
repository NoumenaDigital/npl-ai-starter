import logging
import os

from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from agent_worker.services.base_service import BaseLLMService, LLMServiceError

logger = logging.getLogger(__name__)


class AzureOpenAIError(LLMServiceError):
    """Azure OpenAI-specific service errors."""
    pass


class AzureOpenAIService(BaseLLMService):
    def _initialize_llm(self):
        """Initialize the Azure OpenAI LLM client."""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if not endpoint or not api_key:
            logger.error("Missing Azure OpenAI credentials")
            raise AzureOpenAIError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

        try:
            self.llm = AzureChatOpenAI(
                azure_deployment=self.config.deployment_name,
                temperature=self.config.temperature,
                max_tokens=None,
                max_retries=self.config.max_retries,
                api_version=self.config.api_version,
                azure_endpoint=endpoint,
                api_key=SecretStr(api_key)
            )
            logger.info("Azure OpenAI service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI service: {e}")
            raise AzureOpenAIError(f"Failed to initialize Azure OpenAI service: {str(e)}") from e
