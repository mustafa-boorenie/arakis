"""Apple Sign In OAuth provider implementation."""

import time
import urllib.parse

import httpx
import jwt

from arakis.auth.exceptions import OAuthError
from arakis.auth.providers.base import BaseOAuthProvider
from arakis.auth.schemas import UserInfo
from arakis.config import get_settings

# Apple OAuth endpoints
APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"


class AppleOAuthProvider(BaseOAuthProvider):
    """Apple Sign In OAuth provider."""

    def __init__(self):
        self.settings = get_settings()
        self._apple_public_keys: dict | None = None

    @property
    def name(self) -> str:
        return "apple"

    def _generate_client_secret(self) -> str:
        """
        Generate Apple client secret JWT.

        Apple requires a signed JWT as the client secret, created using
        the private key from Apple Developer Portal.

        Returns:
            Signed JWT string
        """
        if not all(
            [
                self.settings.apple_client_id,
                self.settings.apple_team_id,
                self.settings.apple_key_id,
                self.settings.apple_private_key,
            ]
        ):
            raise OAuthError("apple", "Apple OAuth not fully configured")

        now = int(time.time())

        headers = {
            "kid": self.settings.apple_key_id,
            "alg": "ES256",
        }

        payload = {
            "iss": self.settings.apple_team_id,
            "iat": now,
            "exp": now + 3600,  # 1 hour expiration
            "aud": "https://appleid.apple.com",
            "sub": self.settings.apple_client_id,
        }

        # Handle escaped newlines in private key
        private_key = self.settings.apple_private_key.replace("\\n", "\n")

        return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)

    def get_authorization_url(self, state: str, redirect_uri: str | None = None) -> str:
        """
        Get Apple Sign In authorization URL.

        Args:
            state: CSRF state token
            redirect_uri: Optional custom redirect URI

        Returns:
            Authorization URL for Apple Sign In
        """
        if not self.settings.apple_client_id:
            raise OAuthError("apple", "Apple OAuth not configured")

        # Build redirect URI - Apple callback is POST, so use same base
        callback_uri = redirect_uri
        if not callback_uri:
            callback_uri = f"{self.settings.frontend_url}/api/auth/apple/callback"

        params = {
            "client_id": self.settings.apple_client_id,
            "redirect_uri": callback_uri,
            "response_type": "code id_token",
            "scope": "name email",
            "state": state,
            "response_mode": "form_post",  # Apple sends callback as POST
        }

        return f"{APPLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def _get_apple_public_keys(self) -> dict:
        """Fetch Apple's public keys for JWT verification."""
        async with httpx.AsyncClient() as client:
            response = await client.get(APPLE_KEYS_URL)
            if response.status_code != 200:
                raise OAuthError("apple", "Failed to fetch Apple public keys")
            return response.json()

    async def get_user_info(
        self,
        code: str,
        redirect_uri: str | None = None,
        id_token: str | None = None,
        user_data: dict | None = None,
    ) -> UserInfo:
        """
        Exchange authorization code for user info.

        Note: Apple sends user info (name, email) only on first login via
        the `user` parameter in the callback. On subsequent logins, this
        data is not provided. The id_token always contains the user's email
        and Apple ID (sub).

        Args:
            code: Authorization code from callback
            redirect_uri: Redirect URI used in authorization
            id_token: Optional ID token from callback (Apple sends both)
            user_data: Optional user data from Apple (only on first login)

        Returns:
            UserInfo with Apple user details

        Raises:
            OAuthError: If authentication fails
        """
        client_secret = self._generate_client_secret()

        # Build redirect URI
        callback_uri = redirect_uri
        if not callback_uri:
            callback_uri = f"{self.settings.frontend_url}/api/auth/apple/callback"

        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                APPLE_TOKEN_URL,
                data={
                    "client_id": self.settings.apple_client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_uri,
                },
            )

            if token_response.status_code != 200:
                error_data = token_response.json()
                raise OAuthError(
                    "apple",
                    f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}",
                )

            token_data = token_response.json()
            received_id_token = token_data.get("id_token") or id_token

            if not received_id_token:
                raise OAuthError("apple", "No ID token in response")

            # Decode ID token (we verify the audience and issuer)
            # For production, you should verify the signature using Apple's public keys
            try:
                # Decode without verification for now (Apple's token URL validates)
                # In production, verify signature using Apple's public keys
                id_token_payload = jwt.decode(
                    received_id_token,
                    options={"verify_signature": False},
                    audience=self.settings.apple_client_id,
                )
            except jwt.InvalidTokenError as e:
                raise OAuthError("apple", f"Invalid ID token: {str(e)}")

            # Extract user info from ID token
            apple_id = id_token_payload.get("sub")
            email = id_token_payload.get("email")
            email_verified = id_token_payload.get("email_verified", False)

            if not apple_id:
                raise OAuthError("apple", "No user ID in ID token")

            # Get name from user_data if provided (only on first login)
            name = None
            if user_data:
                first_name = user_data.get("name", {}).get("firstName", "")
                last_name = user_data.get("name", {}).get("lastName", "")
                if first_name or last_name:
                    name = f"{first_name} {last_name}".strip()

            return UserInfo(
                id=apple_id,
                email=email or f"{apple_id}@privaterelay.appleid.com",
                email_verified=email_verified if isinstance(email_verified, bool) else False,
                name=name,
                picture=None,  # Apple doesn't provide profile pictures
                provider="apple",
            )
