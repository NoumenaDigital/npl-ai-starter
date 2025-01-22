from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, TypeVar, Generic, Callable

T = TypeVar('T')

@dataclass
class ApiValue:
    """Represents an NPL value as defined in the API spec"""
    nplType: str
    value: Any
    typeName: Optional[str] = None
    prototypeId: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'ApiValue':
        if not isinstance(data, dict) or 'nplType' not in data:
            raise ValueError("Invalid NPL value format")
            
        npl_type = data['nplType']
        value = data.get('value')
        
        if npl_type == 'struct':
            if isinstance(value, dict):
                parsed_value = {}
                for key, val in value.items():
                    if isinstance(val, dict) and 'nplType' in val:
                        parsed_value[key] = ApiValue.from_dict(val)
                    else:
                        parsed_value[key] = val
                value = parsed_value
        elif npl_type == 'dateTime' and isinstance(value, str):
            # Parse datetime strings but keep as string to maintain original format
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError as e:
                raise ValueError(f"Invalid datetime format: {value}") from e
        elif npl_type == 'number':
            try:
                value = float(str(value)) if value is not None else None
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid number format: {value}") from e
        
        return cls(
            nplType=npl_type,
            value=value,
            typeName=data.get('typeName'),
            prototypeId=data.get('prototypeId')
        )
    
    def get_value_as(self, expected_type: str, transform: Optional[Callable[[Any], T]] = None) -> Optional[T]:
        """
        Get the value if it matches the expected type, optionally transforming it.
        
        Args:
            expected_type: The expected NPL type
            transform: Optional function to transform the value
        """
        if self.nplType != expected_type:
            return None
            
        if transform and self.value is not None:
            return transform(self.value)
        return self.value
    
    def get_text(self) -> Optional[str]:
        """Get the value if this is a text type"""
        return self.get_value_as('text', str)
    
    def get_number(self) -> Optional[float]:
        """Get the value if this is a number type"""
        return self.get_value_as('number', float)
    
    def get_struct(self) -> Optional[Dict[str, 'ApiValue']]:
        """Get the value if this is a struct type"""
        return self.get_value_as('struct')
    
    def get_reference(self) -> Optional[str]:
        """Get the value if this is a protocol reference"""
        return self.get_value_as('protocolReference')

@dataclass
class ApiAgent:
    """Represents an agent as defined in the API spec"""
    id: str
    party: str

@dataclass
class NotificationContent(Generic[T]):
    """Generic container for notification content with type-safe access"""
    ref: str
    content: T

@dataclass
class RequestContent:
    """Content of a request notification"""
    text: str

@dataclass
class ResponseContent:
    """Content of a response notification"""
    title: str
    contents: str

@dataclass
class ApiNotification:
    """Represents a notification as defined in the API spec"""
    name: str
    arguments: List[ApiValue]
    type: str = "notify"
    refId: Optional[str] = None
    protocolVersion: Optional[str] = None
    created: Optional[str] = None
    callback: Optional[str] = None
    id: Optional[int] = None
    agents: Optional[List[ApiAgent]] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ApiNotification':
        if not isinstance(data, dict):
            raise ValueError("Invalid notification format")
            
        return cls(
            name=data.get('name', ''),
            arguments=[ApiValue.from_dict(arg) for arg in data.get('arguments', [])],
            type=data.get('type', 'notify'),
            refId=data.get('refId'),
            protocolVersion=data.get('protocolVersion'),
            created=data.get('created'),
            callback=data.get('callback'),
            id=data.get('id'),
            agents=[ApiAgent(**agent) for agent in data.get('agents', [])] if data.get('agents') else None
        )
    
    def is_request_submission(self) -> bool:
        """Check if this is a request submission notification"""
        return self.name.endswith('requestSubmitted')
        
    def is_request_fulfilled(self) -> bool:
        """Check if this is a request fulfilled notification"""
        return self.name.endswith('requestFulfilled')
    
    def get_request(self) -> Optional[NotificationContent[RequestContent]]:
        """Get the request content if this is a request submission"""
        if not self.is_request_submission() or len(self.arguments) < 2:
            return None
            
        ref = self.arguments[0].get_reference()
        text = self.arguments[1].get_text()
        
        if not ref or not text:
            return None
            
        return NotificationContent(
            ref=ref,
            content=RequestContent(text=text)
        )
    
    def get_response(self) -> Optional[NotificationContent[ResponseContent]]:
        """Get the response content if this is a request fulfilled notification"""
        if not self.is_request_fulfilled() or len(self.arguments) < 2:
            return None
            
        ref = self.arguments[0].get_reference()
        ticket = self.arguments[1].get_struct()
        
        if not ref or not ticket:
            return None
            
        title = ticket.get('title')
        contents = ticket.get('contents')
        
        if not title or not contents:
            return None
            
        return NotificationContent(
            ref=ref,
            content=ResponseContent(
                title=title.get_text() or '',
                contents=contents.get_text() or ''
            )
        )

@dataclass
class ApiNotificationPackage:
    """Represents a notification package as defined in the API spec"""
    payloadType: str
    notification: Optional[ApiNotification] = None
    id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ApiNotificationPackage':
        if not isinstance(data, dict):
            raise ValueError("Invalid notification package format")
            
        notification_data = data.get('notification')
        return cls(
            payloadType=data.get('payloadType', ''),
            notification=ApiNotification.from_dict(notification_data) if notification_data else None,
            id=data.get('id')
        )
    
    def is_notification(self) -> bool:
        """Check if this is a notification payload"""
        return self.payloadType == 'notify' 
