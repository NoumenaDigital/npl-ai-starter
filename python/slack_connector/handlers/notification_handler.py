import logging
from typing import Optional

from slack_bolt import App
from client.handlers.notification_handler import BaseNotificationHandler
from client.models.notification_models import ApiNotification

logger = logging.getLogger(__name__)

class SlackNotificationHandler(BaseNotificationHandler):
    """Slack-specific notification handler"""
    
    def __init__(self, app: App):
        self.app = app
        self.channel: Optional[str] = None
        logger.info("SlackNotificationHandler initialized")
    
    def set_channel(self, channel: str) -> None:
        """Set the current active Slack channel"""
        self.channel = channel
        logger.info(f"Updated active channel to: {channel}")
    
    def handle_notification(self, notification: ApiNotification) -> None:
        """
        Handle a notification from the NPL platform.
        
        Args:
            notification: The notification data object
        """
        if notification.is_request_fulfilled():
            logger.info(f"Handling request fulfillment: {notification}")
            self._handle_request_fulfillment(notification)
        else:
            logger.debug(f"Ignoring notification with name: {notification.name}")
    
    def _handle_request_fulfillment(self, notification: ApiNotification) -> None:
        """
        Handle a request fulfillment notification.
        
        Args:
            notification: The notification data object
        """
        try:
            response = notification.get_response()
            if not response:
                logger.error("Invalid response notification format")
                return
            
            if not self.channel:
                logger.error(f"No active channel found for request ref: {response.ref}")
                return
                
            self.app.client.chat_postMessage(
                channel=self.channel,
                text=response.content.contents
            )
            logger.info(f"Sent response to channel {self.channel}")
            
        except Exception as e:
            logger.error(f"Error handling request fulfillment: {e}", exc_info=True) 