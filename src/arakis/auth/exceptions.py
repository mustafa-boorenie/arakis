"""Authentication exceptions for Arakis."""


class AuthenticationError(Exception):
    """Base authentication error."""

    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)


class UserNotFoundError(AuthenticationError):
    """Raised when a user is not found."""

    def __init__(self, message: str = "User not found"):
        super().__init__(message)


class OAuthError(AuthenticationError):
    """Raised when OAuth authentication fails."""

    def __init__(self, provider: str, message: str = "OAuth authentication failed"):
        self.provider = provider
        super().__init__(f"{provider}: {message}")


class TrialLimitError(AuthenticationError):
    """Raised when trial limit is reached."""

    def __init__(self, message: str = "Trial limit reached. Please sign in to continue."):
        super().__init__(message)
