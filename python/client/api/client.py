import logging
import os
from typing import Any, List, Optional, cast

from openapi_client.api.default_api import DefaultApi
from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration
from openapi_client.models.party import Party
from openapi_client.models.request import Request
from openapi_client.models.request_create import RequestCreate
from openapi_client.models.request_fulfill_command import RequestFulfillCommand
from openapi_client.models.request_parties import RequestParties
from openapi_client.models.ticket import Ticket
from openapi_client.exceptions import ApiException

from client.auth import fetch_access_token
from .errors import ApiError

logger = logging.getLogger(__name__)

class NplApiClient:
    """Client for the NPL API."""
    
    def __init__(self, api_url: Optional[str] = None):
        """Initialize the API client."""
        self.api_url = api_url or os.getenv("API_URL")
        if not self.api_url:
            raise ApiError("API_URL must be set")
        
        try:
            self.config = self._create_config()
            self.api_client = ApiClient(self.config)
            self.api = DefaultApi(self.api_client)
            logger.info("API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            raise ApiError(f"Failed to initialize API client: {str(e)}") from e

    def _create_config(self) -> Configuration:
        """Create API configuration."""
        try:
            access_token = fetch_access_token()
            config = Configuration(
                host=self.api_url,
                access_token=access_token
            )
            return config
        except Exception as e:
            logger.error(f"Failed to create API configuration: {e}")
            raise ApiError(f"Failed to create API configuration: {str(e)}") from e

    def _create_party(self, email: str) -> Party:
        """Create a party object."""
        return Party(
            entity={"email": [email]},
            access={}
        )

    def create_request(self, contents: str, user_email: str, chatbot_email: str) -> Request:
        """
        Create a new request.
        
        Args:
            contents: The request contents
            user_email: The user's email
            chatbot_email: The chatbot's email
        Returns:
            Request: The created request
            
        Raises:
            ApiError: If the request creation fails
        """
        try:
            parties = RequestParties(
                user=self._create_party(user_email),
                slack=self._create_party(chatbot_email),
                worker=self._create_party("ai.agent.worker@noumenadigital.com")
            )
            
            request_create = RequestCreate(
                contents=contents,
                **{"@parties": parties}
            )
            
            response = self.api.create_request(request_create)
            logger.info(f"Created request: {response}")
            return response
        except ApiException as e:
            error = f"Failed to create request: {e}"
            logger.error(error)
            raise ApiError(error) from e
        except Exception as e:
            error = f"Unexpected error creating request: {e}"
            logger.error(error)
            raise ApiError(error) from e

    def get_requests(self) -> List[Request]:
        """
        Get all requests.
        
        Returns:
            List[Request]: List of requests
            
        Raises:
            ApiError: If fetching requests fails
        """
        try:
            response = self.api.get_request_list()
            return [cast(Request, r) for r in response]
        except ApiException as e:
            error = f"Failed to get requests: {e}"
            logger.error(error)
            raise ApiError(error) from e
        except Exception as e:
            error = f"Unexpected error getting requests: {e}"
            logger.error(error)
            raise ApiError(error) from e

    def fulfill_request(self, ref: str, response: str) -> Any:
        """
        Fulfill a request with a response.
        
        Args:
            ref: The request reference
            response: The response text
            
        Returns:
            Any: The API response
            
        Raises:
            ApiError: If fulfilling the request fails
        """
        try:
            ticket = Ticket(title="Response", contents=response)
            command = RequestFulfillCommand(ticket=ticket)
            result = self.api.request_fulfill(id=ref, request_fulfill_command=command)
            logger.info(f"Fulfilled request {ref}")
            return result
        except ApiException as e:
            error = f"Failed to fulfill request {ref}: {e}"
            logger.error(error)
            raise ApiError(error) from e
        except Exception as e:
            error = f"Unexpected error fulfilling request {ref}: {e}"
            logger.error(error)
            raise ApiError(error) from e 