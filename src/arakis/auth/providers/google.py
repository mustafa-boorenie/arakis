"""Google OAuth provider implementation."""

import urllib.parse

import httpx

from arakis.auth.exceptions import OAuthError
from arakis.auth.providers.base import BaseOAuthProvider
from arakis.auth.schemas import UserInfo
from arakis.config import get_settings

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth 2.0 provider."""

    def __init__(self):
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "google"

    def get_authorization_url(self, state: str, redirect_uri: str | None = None) -> str:
        """
        Get Google OAuth authorization URL.

        Args:
            state: CSRF state token
            redirect_uri: Optional custom redirect URI

        Returns:
            Authorization URL for Google OAuth
        """
        if not self.settings.google_client_id:
            raise OAuthError("google", "Google OAuth not configured")

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": redirect_uri or self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def get_user_info(self, code: str, redirect_uri: str | None = None) -> UserInfo:
        """
        Exchange authorization code for user info.

        Args:
            code: Authorization code from callback
            redirect_uri: Redirect URI used in authorization

        Returns:
            UserInfo with Google user details

        Raises:
            OAuthError: If authentication fails
        """
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise OAuthError("google", "Google OAuth not configured")

        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri or self.settings.google_redirect_uri,
                },
            )

            if token_response.status_code != 200:
                error_data = token_response.json()
                raise OAuthError(
                    "google",
                    f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}",
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise OAuthError("google", "No access token in response")

            # Get user info
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                raise OAuthError("google", "Failed to fetch user info")

            user_data = userinfo_response.json()

            return UserInfo(
                id=user_data["id"],
                email=user_data["email"],
                email_verified=user_data.get("verified_email", False),
                name=user_data.get("name"),
                picture=user_data.get("picture"),
                provider="google",
            )
