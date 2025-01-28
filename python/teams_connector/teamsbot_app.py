import logging
import os
import signal
import sys
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import uvicorn
from botbuilder.core import BotFrameworkAdapter, TurnContext
from botbuilder.core.bot_framework_adapter import BotFrameworkAdapterSettings
from botbuilder.schema import Activity
from dotenv import load_dotenv
from fastapi import FastAPI, Request

from client.api import NplApiClient
from client.stream import consume_sse
from teams_connector.handlers.notification_handler import TeamsNotificationHandler

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclass
class TeamsConfig:
    api_url: str
    port: int = 3978
    app_id: Optional[str] = None
    app_password: Optional[str] = None

    @property
    def sse_url(self) -> str:
        return urljoin(self.api_url, "/api/streams/notifications")


class TeamsApp:
    def __init__(self, config: TeamsConfig):
        self.config = config
        self.shutdown_event = threading.Event()
        self.sse_thread: Optional[threading.Thread] = None

        # For local development with Bot Framework Emulator, we can skip credentials
        settings = BotFrameworkAdapterSettings(
            app_id=config.app_id or "",
            app_password=config.app_password or ""
        )
        self.adapter = BotFrameworkAdapter(settings)
        self.api_client = NplApiClient(api_url=config.api_url)

        # Create a notification handler with the bot adapter and app ID
        self.notification_handler = TeamsNotificationHandler(self.adapter, config.app_id or "default-bot-id")

        # Setup FastAPI
        self.app = FastAPI()
        self.setup_routes()

    def setup_routes(self) -> None:
        @self.app.post("/api/messages")
        async def messages(req: Request):
            body = await req.json()
            response = await self.process_activity(body, dict(req.headers))
            return response or {}

    async def _handle_message_activity(self, turn_context: TurnContext) -> None:
        """Handle incoming message activity."""
        message = turn_context.activity.text
        # For emulator, we'll use a default email or extract from activity
        user_email = getattr(turn_context.activity.from_property, 'email', 'default@local.dev')

        conversation_reference = TurnContext.get_conversation_reference(turn_context.activity)

        conversation_id = getattr(turn_context.activity.conversation, 'id', 'unknown')
        channel_id = getattr(turn_context.activity, 'channel_id', 'unknown')
        logger.debug(f"Activity details: channel_id={channel_id}, conversation_id={conversation_id}")
        logger.debug(f"Conversation reference: {conversation_reference.as_dict()}")

        if not conversation_reference.conversation or not conversation_reference.conversation.id:
            logger.error("Invalid conversation reference - missing conversation ID")
            await turn_context.send_activity("Sorry, I'm having trouble processing your request. Please try again.")
            return

        self.notification_handler.set_conversation_reference(conversation_reference.as_dict())

        self.api_client.create_request(message, user_email, chatbot_email="teamsbot@noumenadigital.com")
        logger.info(f"Created request for user: {user_email}")

        await turn_context.send_activity("I'm processing your request...")

    async def _handle_conversation_update(self, turn_context: TurnContext) -> None:
        """Handle conversation update activity."""
        if turn_context.activity.members_added:
            for member in turn_context.activity.members_added:
                # Check if member and recipient exist and have IDs before comparing
                if (member and turn_context.activity.recipient and
                        member.id and turn_context.activity.recipient.id and
                        member.id != turn_context.activity.recipient.id):
                    await turn_context.send_activity("Hello! I'm your NPL assistant. How can I help you today?")

    def start_sse(self) -> None:
        """Start consuming SSE stream."""
        try:
            logger.info("Starting SSE stream...")
            consume_sse(self.config.sse_url, self.notification_handler.process_notification)
        except Exception as e:
            if not self.shutdown_event.is_set():
                logger.error(f"SSE stream error: {e}")
                self.shutdown_event.set()

    async def process_activity(self, req_body: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Process incoming activity from Teams/Emulator.
        """
        activity = Activity().deserialize(req_body)
        auth_header = headers.get("Authorization", "")

        response: Dict[str, Any] = {}
        try:
            async def callback(turn_context):
                if turn_context.activity.type == "message":
                    await self._handle_message_activity(turn_context)
                elif turn_context.activity.type == "conversationUpdate":
                    await self._handle_conversation_update(turn_context)

            await self.adapter.process_activity(activity, auth_header, callback)
        except Exception as e:
            logger.error(f"Error processing activity: {e}", exc_info=True)
            response = {"error": str(e)}

        return response

    def cleanup(self) -> None:
        """Cleanup and shutdown the application."""
        logger.info("Starting cleanup...")
        self.shutdown_event.set()

        if self.sse_thread and self.sse_thread.is_alive():
            logger.info("Waiting for SSE thread to finish...")
            self.sse_thread.join(timeout=2)
            if self.sse_thread.is_alive():
                logger.warning("SSE thread did not finish gracefully")

        logger.info("Cleanup completed")

    def start(self) -> None:
        """Start the Teams app and SSE consumer."""
        # Start SSE consumer in a background thread
        self.sse_thread = threading.Thread(target=self.start_sse, name="SSEThread", daemon=True)
        self.sse_thread.start()
        logger.info("SSE thread started")

        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.config.port,
            log_level="info"
        )


def main() -> None:
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("API_URL environment variable is required")

    port = int(os.getenv("PORT", "3978"))

    # These are optional when using the emulator
    app_id = os.getenv("MICROSOFT_APP_ID")
    app_password = os.getenv("MICROSOFT_APP_PASSWORD")

    config = TeamsConfig(
        api_url=api_url,
        app_id=app_id,
        app_password=app_password,
        port=port
    )

    teams_app = TeamsApp(config)

    def signal_handler(sig: int, frame: Any) -> None:
        logger.info("Received shutdown signal...")
        teams_app.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    teams_app.start()


if __name__ == "__main__":
    main()
