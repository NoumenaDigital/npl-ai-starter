import logging

from dotenv import load_dotenv

from agent_worker.config import load_config
from agent_worker.handlers.notification_handler import AgentNotificationHandler
from agent_worker.services.azure_openai_service import AzureOpenAIService
from agent_worker.services.bedrock_service import BedrockService
from client.stream import consume_sse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the agent worker"""
    try:
        load_dotenv()
        config = load_config()

        if config.llm_provider == "bedrock":
            if not config.bedrock:
                raise ValueError("Bedrock configuration is missing")
            llm_service = BedrockService(config.bedrock)
            logger.info("Using Bedrock service")
        elif config.llm_provider == "azure-openai":
            if not config.azure_openai:
                raise ValueError("Azure OpenAI configuration is missing")
            llm_service = AzureOpenAIService(config.azure_openai)
            logger.info("Using Azure OpenAI service")
        else:
            raise ValueError(f"Invalid LLM provider: {config.llm_provider}")

        notification_handler = AgentNotificationHandler(
            config=config,
            llm_service=llm_service
        )

        logger.info("Starting SSE consumer...")
        consume_sse(config.sse_url, notification_handler.process_notification)
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)


if __name__ == "__main__":
    main()
