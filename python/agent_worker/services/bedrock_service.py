import logging
from langchain_aws import ChatBedrock

from agent_worker.services.base_service import BaseLLMService, LLMServiceError

logger = logging.getLogger(__name__)


class BedrockError(LLMServiceError):
    """Bedrock-specific service errors."""
    pass


class BedrockService(BaseLLMService):
    def _initialize_llm(self):
        """Initialize the Bedrock LLM client."""
        try:
            self.llm = ChatBedrock(
                model=self.config.model_id,
                model_kwargs={
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                }
            )
            logger.info("Bedrock service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock service: {e}")
            raise BedrockError(f"Failed to initialize Bedrock service: {str(e)}") from e
