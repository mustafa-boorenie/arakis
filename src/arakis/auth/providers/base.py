"""Base OAuth provider class."""

from abc import ABC, abstractmethod

from arakis.auth.schemas import UserInfo


class BaseOAuthProvider(ABC):
    """Abstract base class for OAuth providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'google', 'apple')."""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str | None = None) -> str:
        """
        Get the OAuth authorization URL.

        Args:
            state: CSRF state token
            redirect_uri: Optional custom redirect URI

        Returns:
            Authorization URL to redirect user to
        """
        pass

    @abstractmethod
    async def get_user_info(self, code: str, redirect_uri: str | None = None) -> UserInfo:
        """
        Exchange authorization code for user info.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization request

        Returns:
            UserInfo with user details from provider

        Raises:
            OAuthError: If token exchange or user info retrieval fails
        """
        pass
