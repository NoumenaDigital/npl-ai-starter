import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

import requests

from client.auth import fetch_access_token

logger = logging.getLogger(__name__)

@dataclass
class ServerSentEvent:
    """Represents a Server-Sent Event with its fields."""
    def __init__(self):
        self.event: Optional[str] = None
        self.data: Optional[str] = None

def parse_sse(line: str) -> Optional[tuple[str, str]]:
    """Parse a line of SSE data into field name and value."""
    if not line or ':' not in line:
        return None
        
    field, _, value = line.partition(':')
    if value.startswith(' '):
        value = value[1:]
    return field, value

def consume_sse(url: str, callback: Callable[[str], None]) -> None:
    """
    Consume Server-Sent Events from the given URL.
    
    Args:
        url (str): The URL to connect to
        callback: Function to call with each event data
        
    Raises:
        requests.RequestException: If the connection fails
        ValueError: If authentication fails
    """
    try:
        access_token = fetch_access_token()
        
        headers = {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {access_token}"
        }
        
        logger.debug(f"Connecting to SSE stream at {url}")
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        logger.debug("Connected to SSE stream")
        
        current_event = ServerSentEvent()
        
        for line in response.iter_lines():
            if not line:
                # Empty line means dispatch the event
                if current_event.data and current_event.event != 'tick':
                    logger.debug(f"Processing SSE event: {current_event}")
                    callback(current_event.data)
                current_event = ServerSentEvent()
                continue
            
            parsed = parse_sse(line.decode('utf-8'))
            if parsed:
                field, value = parsed
                if field == 'event':
                    current_event.event = value
                elif field == 'data':
                    current_event.data = value
                    
    except requests.RequestException as e:
        logger.error(f"SSE connection error: {e}")
        raise
    except ValueError as e:
        logger.error(f"Authentication error: {e}")
        raise
