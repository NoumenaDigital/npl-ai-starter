import logging
from typing import Union

from agent_worker.config import AppConfig
from agent_worker.services.azure_openai_service import AzureOpenAIService, AzureOpenAIError
from agent_worker.services.base_service import BaseLLMService, LLMServiceError
from agent_worker.services.bedrock_service import BedrockService, BedrockError
from client.api import NplApiClient, ApiError
from client.handlers.notification_handler import BaseNotificationHandler
from client.models.notification_models import ApiNotification

logger = logging.getLogger(__name__)

LLMService = Union[AzureOpenAIService, BedrockService]
LLMError = Union[AzureOpenAIError, BedrockError]


class NotificationError(Exception):
    """Base class for notification handling errors."""
    pass


class RequestProcessingError(NotificationError):
    """Error occurred while processing a request."""
    pass


class AgentNotificationHandler(BaseNotificationHandler):
    """Agent-specific notification handler"""

    def __init__(
            self,
            config: AppConfig,
            llm_service: BaseLLMService
    ):
        self.config = config
        self.llm_service = llm_service
        self.api_client = NplApiClient(api_url=config.api_url)
        logger.info(f"AgentNotificationHandler initialized with {config.llm_provider} service")

    def handle_notification(self, notification: ApiNotification) -> None:
        """
        Handle a notification from the NPL platform.
        
        Args:
            notification: The notification data object
            
        Raises:
            NotificationError: If there's an error processing the notification
        """
        try:
            if notification.is_request_submission():
                logger.info(f"Handling request submission: {notification}")
                self._handle_request_submission(notification)
            else:
                logger.debug(f"Ignoring notification with name: {notification.name}")
        except Exception as e:
            logger.error(f"Failed to handle notification: {e}", exc_info=True)
            raise NotificationError(f"Failed to handle notification: {str(e)}") from e

    def _handle_request_submission(self, notification: ApiNotification) -> None:
        """
        Handle a request submission notification by converting the requirements into a structured ticket.
        
        Args:
            notification: The notification data object
            
        Raises:
            RequestProcessingError: If there's an error processing the request
        """
        request = notification.get_request()
        if not request:
            error = "Invalid request notification format"
            logger.error(error)
            raise RequestProcessingError(error)

        try:
            logger.debug(f"Processing request with content: {request.content.text}")
            logger.debug("Parsing requirements into ticket structure...")
            ticket = self.llm_service.parse_requirements_to_ticket(request.content.text)
            logger.debug(f"Parsed ticket: {ticket}")

            formatted_response = (
                f"*Title:*\n{ticket.title}\n\n"
                f"*Implementation Details:*\n```\n{ticket.contents}\n```"
            )
            logger.debug(f"Formatted response: {formatted_response}")

            try:
                logger.debug(f"Attempting to fulfill request {request.ref} with response: {formatted_response}")
                result = self.api_client.fulfill_request(request.ref, formatted_response)
                logger.info(f"Request fulfilled successfully: {result}")
            except ApiError as e:
                error = f"Failed to fulfill request {request.ref}"
                logger.error(f"{error}: {e}")
                self._send_error_response(request.ref, str(e))
                raise RequestProcessingError(error) from e

        except LLMServiceError as e:
            error = f"LLM service error while processing request {request.ref}"
            logger.error(f"{error}: {e}")
            self._send_error_response(request.ref, str(e))
            raise RequestProcessingError(error) from e

        except Exception as e:
            error = f"Unexpected error while processing request {request.ref}"
            logger.error(f"{error}: {e}", exc_info=True)
            self._send_error_response(request.ref, "An unexpected error occurred")
            raise RequestProcessingError(error) from e

    def _send_error_response(self, request_ref: str, error_message: str) -> None:
        """
        Send an error response to the user.
        
        Args:
            request_ref: The request reference
            error_message: The error message to send
        """
        try:
            error_response = f"*Error:* {error_message}"
            self.api_client.fulfill_request(request_ref, error_response)
            logger.info("Sent error message to user")
        except ApiError as e:
            logger.error(f"Failed to send error message: {e}")
            # We don't raise here as this is already error handling code
