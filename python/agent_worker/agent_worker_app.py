import logging

from dotenv import load_dotenv

from agent_worker.config import load_config
from agent_worker.handlers.notification_handler import AgentNotificationHandler
from agent_worker.services.openai_service import OpenAIService
from client.stream import consume_sse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the agent worker"""
    try:
        load_dotenv()
        config = load_config()
        openai_service = OpenAIService(config.openai)
        notification_handler = AgentNotificationHandler(config, openai_service)

        logger.info("Starting SSE consumer...")
        consume_sse(config.sse_url, notification_handler.process_notification)
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)


if __name__ == "__main__":
    main()
