import os
import logging
from dataclasses import dataclass
from typing import Optional

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

@dataclass
class AuthConfig:
    """Authentication configuration."""
    auth_url: str
    client_id: str
    client_secret: Optional[str]
    username: str
    password: str

    @classmethod
    def from_env(cls) -> 'AuthConfig':
        """Create AuthConfig from environment variables."""
        auth_url = os.getenv("AUTH_URL")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")

        if not all([auth_url, client_id, username, password]):
            raise ValueError(
                "Missing required environment variables. Required: "
                "AUTH_URL, CLIENT_ID, USERNAME, PASSWORD"
            )

        # We can safely cast here because we've checked for None values above
        return cls(
            auth_url=str(auth_url),
            client_id=str(client_id),
            client_secret=client_secret,
            username=str(username),
            password=str(password)
        )

def fetch_access_token() -> str:
    """
    Fetch an access token from the auth server.

    Returns:
        str: The access token

    Raises:
        ValueError: If required environment variables are not set
        RequestException: If the token request fails
    """
    try:
        config = AuthConfig.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    url = f"{config.auth_url}/protocol/openid-connect/token"

    data = {
        "grant_type": "password",
        "client_id": config.client_id,
        "client_secret": config.client_secret or "",
        "username": config.username,
        "password": config.password
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    logger.info(f"Requesting token from auth server")
    logger.debug(f"Auth URL: {url}")

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to fetch access token: {e}")
        raise

    token_data = response.json()

    if "access_token" not in token_data:
        error = f"Invalid token response: {token_data}"
        logger.error(error)
        raise ValueError(error)

    logger.info("Successfully retrieved access token")
    return token_data["access_token"]
