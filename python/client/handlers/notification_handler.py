import json
import logging
from abc import ABC, abstractmethod

from client.models.notification_models import ApiNotificationPackage, ApiNotification

logger = logging.getLogger(__name__)

class BaseNotificationHandler(ABC):
    """Base class for notification handlers"""
    
    def process_notification(self, notification_data: str) -> None:
        """
        Process an incoming notification.
        
        Args:
            notification_data (str): Raw notification data as JSON string
        """
        try:
            logger.debug(f"Processing notification data: {notification_data}")
            data = json.loads(notification_data)
            
            try:
                payload = ApiNotificationPackage.from_dict(data)
            except ValueError as e:
                logger.error(f"Invalid notification format: {e}")
                return
            
            if not payload.is_notification():
                logger.debug(f"Ignoring non-notification payload: {payload.payloadType}")
                return
            
            if not payload.notification:
                logger.error("Missing notification data in payload")
                return
                
            self.handle_notification(payload.notification)
                
        except json.JSONDecodeError:
            logger.error(f"Error decoding notification data: {notification_data}")
        except Exception as e:
            logger.error(f"Error processing notification: {e}", exc_info=True)
    
    @abstractmethod
    def handle_notification(self, notification: ApiNotification) -> None:
        """
        Handle a notification. This method should be implemented by subclasses.
        
        Args:
            notification: The notification data object
        """
        pass 
