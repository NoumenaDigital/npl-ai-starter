import os
import threading
import signal
import sys
from typing import Optional, Dict, Any
from urllib.parse import urljoin
import logging
from dataclasses import dataclass

from slack_bolt import App
from client.stream import consume_sse
from client.api import NplApiClient
from dotenv import load_dotenv
from handlers.notification_handler import SlackNotificationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SlackConfig:
    api_url: str
    port: int = 8000

    @property
    def sse_url(self) -> str:
        return urljoin(self.api_url, "/api/streams/notifications")

class SlackApp:
    def __init__(self, config: SlackConfig):
        self.config = config
        self.channel: Optional[str] = None
        self.shutdown_event = threading.Event()
        self.sse_thread: Optional[threading.Thread] = None
        self.app_thread: Optional[threading.Thread] = None
        
        self.app = App()
        self.api_client = NplApiClient(api_url=config.api_url)
        self.notification_handler = SlackNotificationHandler(self.app)
        
        self._setup_message_handler()
        
    def _setup_message_handler(self) -> None:
        @self.app.event("message")
        def handle_im(event: Dict[str, Any]) -> None:
            logger.info(f"Received a message: {event}")
            user_info = self.app.client.users_info(user=event["user"])
            email = user_info["user"]["profile"]["email"]
            self.api_client.create_request(event["text"], email, "slackbot@noumenadigital.com")
            self.notification_handler.set_channel(event["channel"])
            logger.info(f"Updated notification handler channel: {event['channel']}")

    def start_sse(self) -> None:
        try:
            consume_sse(self.config.sse_url, self.notification_handler.process_notification)
        except Exception as e:
            if not self.shutdown_event.is_set():
                logger.error(f"SSE stream error: {e}")
                self.shutdown_event.set()

    def start_app(self) -> None:
        try:
            self.app.start(port=self.config.port)
        except Exception as e:
            if not self.shutdown_event.is_set():
                logger.error(f"Slack app error: {e}")
                self.shutdown_event.set()

    def cleanup(self) -> None:
        """Cleanup and shutdown the application."""
        logger.info("Starting cleanup...")
        self.shutdown_event.set()
        
        # Stop the Slack app first to prevent new incoming messages
        if hasattr(self.app, 'stop'):
            logger.info("Stopping Slack app...")
            self.app.stop()
        
        # Give threads a chance to finish gracefully
        if self.sse_thread and self.sse_thread.is_alive():
            logger.info("Waiting for SSE thread to finish...")
            self.sse_thread.join(timeout=2)
            if self.sse_thread.is_alive():
                logger.warning("SSE thread did not finish gracefully")
        
        if self.app_thread and self.app_thread.is_alive():
            logger.info("Waiting for app thread to finish...")
            self.app_thread.join(timeout=2)
            if self.app_thread.is_alive():
                logger.warning("App thread did not finish gracefully")
        
        logger.info("Cleanup completed")

    def start(self) -> None:
        """Start the Slack app and SSE consumer."""
        self.sse_thread = threading.Thread(target=self.start_sse, name="SSEThread", daemon=True)
        self.app_thread = threading.Thread(target=self.start_app, name="SlackAppThread", daemon=True)

        self.sse_thread.start()
        self.app_thread.start()

        try:
            self.shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.cleanup()

def main() -> None:
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    
    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("API_URL environment variable is not set")
    
    port = int(os.getenv("PORT", "8000"))
    config = SlackConfig(api_url=api_url, port=port)
    
    slack_app = SlackApp(config)
    
    def signal_handler(sig: int, frame: Any) -> None:
        logger.info("Received shutdown signal...")
        slack_app.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    slack_app.start()

if __name__ == "__main__":
    main()
