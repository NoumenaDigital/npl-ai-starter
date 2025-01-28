import asyncio
import logging
from typing import Optional

from botbuilder.core import TurnContext, BotAdapter
from botbuilder.core.bot_framework_adapter import BotFrameworkAdapter
from botbuilder.schema import Activity, ActivityTypes, ConversationAccount

from client.handlers.notification_handler import BaseNotificationHandler
from client.models.notification_models import ApiNotification

logger = logging.getLogger(__name__)


class TeamsNotificationHandler(BaseNotificationHandler):
    """Teams-specific notification handler"""

    def __init__(self, adapter: Optional[BotAdapter] = None, bot_id: str = "default-bot-id"):
        self.adapter = adapter
        self.bot_id = bot_id
        self.conversation_reference: Optional[dict] = None
        logger.info("TeamsNotificationHandler initialized")

    def update_adapter(self, adapter: BotAdapter) -> None:
        """Update the bot adapter for this handler"""
        self.adapter = adapter

    def set_conversation_reference(self, conversation_reference: dict) -> None:
        """Set the current active Teams conversation reference"""
        # Validate the conversation reference has required fields
        if not conversation_reference.get('conversation', {}).get('id'):
            logger.error("Cannot set conversation reference - missing conversation ID")
            return

        self.conversation_reference = conversation_reference
        logger.info(f"Updated active conversation reference with ID: {conversation_reference['conversation']['id']}")

    def handle_notification(self, notification: ApiNotification) -> None:
        """
        Handle a notification from the NPL platform.
        
        Args:
            notification: The notification data object
        """
        if notification.is_request_fulfilled():
            logger.info(f"Handling request fulfillment: {notification}")
            if not self.conversation_reference or not self.conversation_reference.get('conversation', {}).get('id'):
                logger.error("No valid conversation reference found - cannot handle notification")
                return
            asyncio.run(self._handle_request_fulfillment(notification))
        else:
            logger.debug(f"Ignoring notification with name: {notification.name}")

    async def _handle_request_fulfillment(self, notification: ApiNotification) -> None:
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

            if not self.conversation_reference:
                logger.error(f"No conversation reference found for request ref: {response.ref}")
                return

            if not isinstance(self.adapter, BotFrameworkAdapter):
                logger.error("Adapter must be a BotFrameworkAdapter")
                return

            logger.debug(f"Sending response using conversation reference: {self.conversation_reference}")

            conversation = ConversationAccount(
                id=self.conversation_reference['conversation']['id'],
                name=self.conversation_reference['conversation'].get('name'),
                conversation_type=self.conversation_reference['conversation'].get('conversationType'),
                tenant_id=self.conversation_reference['conversation'].get('tenantId')
            )

            activity = Activity(
                type=ActivityTypes.message,
                text=response.content.contents,
                channel_id=self.conversation_reference['channel_id'],
                service_url=self.conversation_reference['service_url'],
                from_property=self.conversation_reference['bot'],
                recipient=self.conversation_reference['user'],
                conversation=conversation
            )

            turn_context = TurnContext(self.adapter, activity)

            connector_client = await self.adapter.create_connector_client(activity.service_url)
            turn_context.turn_state[BotAdapter.BOT_CONNECTOR_CLIENT_KEY] = connector_client

            await self.adapter.send_activities(turn_context, [activity])
            logger.info("Sent response to Teams conversation")

        except Exception as e:
            logger.error(f"Error handling request fulfillment: {e}", exc_info=True)
