"""Tests for the authentication module."""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from arakis.auth.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    OAuthError,
    TokenExpiredError,
    TrialLimitError,
    UserNotFoundError,
)
from arakis.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_token,
)
from arakis.auth.schemas import (
    OAuthState,
    RefreshTokenRequest,
    TokenResponse,
    UserInfo,
)

# ============================================================
# Exception Tests
# ============================================================


class TestAuthExceptions:
    """Tests for authentication exceptions."""

    def test_authentication_error_default_message(self):
        error = AuthenticationError()
        assert str(error) == "Authentication failed"

    def test_authentication_error_custom_message(self):
        error = AuthenticationError("Custom error")
        assert str(error) == "Custom error"

    def test_invalid_credentials_error(self):
        error = InvalidCredentialsError()
        assert str(error) == "Invalid credentials"

    def test_token_expired_error(self):
        error = TokenExpiredError()
        assert str(error) == "Token has expired"

    def test_user_not_found_error(self):
        error = UserNotFoundError()
        assert str(error) == "User not found"

    def test_oauth_error_includes_provider(self):
        error = OAuthError("google", "Invalid code")
        assert "google" in str(error)
        assert "Invalid code" in str(error)
        assert error.provider == "google"

    def test_trial_limit_error(self):
        error = TrialLimitError()
        assert "Trial limit" in str(error)


# ============================================================
# JWT Tests
# ============================================================


class TestJWTCreation:
    """Tests for JWT token creation."""

    @patch("arakis.auth.jwt.get_settings")
    def test_create_access_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.access_token_expire_minutes = 30

        token = create_access_token("user-123", "test@example.com")

        assert token is not None
        assert isinstance(token, str)
        # Decode to verify structure
        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    @patch("arakis.auth.jwt.get_settings")
    def test_create_access_token_custom_expiry(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.access_token_expire_minutes = 30

        custom_delta = timedelta(hours=2)
        token = create_access_token("user-123", "test@example.com", expires_delta=custom_delta)

        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        exp = datetime.utcfromtimestamp(payload["exp"])
        iat = datetime.utcfromtimestamp(payload["iat"])
        # Should be approximately 2 hours
        assert (exp - iat).seconds >= 7100  # Allow some tolerance

    @patch("arakis.auth.jwt.get_settings")
    def test_create_refresh_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.refresh_token_expire_days = 30

        token, token_hash = create_refresh_token("user-123")

        assert token is not None
        assert token_hash is not None
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64  # SHA256 hex digest

        # Verify hash matches
        expected_hash = hashlib.sha256(token.encode()).hexdigest()
        assert token_hash == expected_hash

        # Decode to verify structure
        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert "jti" in payload  # Token ID

    @patch("arakis.auth.jwt.get_settings")
    def test_create_refresh_token_custom_expiry(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.refresh_token_expire_days = 30

        custom_delta = timedelta(days=7)
        token, _ = create_refresh_token("user-123", expires_delta=custom_delta)

        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        exp = datetime.utcfromtimestamp(payload["exp"])
        iat = datetime.utcfromtimestamp(payload["iat"])
        # Should be approximately 7 days
        assert (exp - iat).days >= 6


class TestJWTDecoding:
    """Tests for JWT token decoding."""

    @patch("arakis.auth.jwt.get_settings")
    def test_decode_valid_access_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.access_token_expire_minutes = 30

        # Create a valid token
        token = create_access_token("user-123", "test@example.com")

        # Decode it
        payload = decode_access_token(token)

        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    @patch("arakis.auth.jwt.get_settings")
    def test_decode_expired_access_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"

        # Create an expired token
        expired_delta = timedelta(seconds=-1)
        token = create_access_token("user-123", "test@example.com", expires_delta=expired_delta)

        with pytest.raises(TokenExpiredError):
            decode_access_token(token)

    @patch("arakis.auth.jwt.get_settings")
    def test_decode_invalid_access_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"

        with pytest.raises(InvalidCredentialsError):
            decode_access_token("invalid.token.here")

    @patch("arakis.auth.jwt.get_settings")
    def test_decode_wrong_token_type(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.refresh_token_expire_days = 30

        # Create refresh token
        refresh_token, _ = create_refresh_token("user-123")

        # Try to decode as access token
        with pytest.raises(InvalidCredentialsError) as exc_info:
            decode_access_token(refresh_token)
        assert "Invalid token type" in str(exc_info.value)

    @patch("arakis.auth.jwt.get_settings")
    def test_decode_valid_refresh_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.refresh_token_expire_days = 30

        token, _ = create_refresh_token("user-123")
        payload = decode_refresh_token(token)

        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    @patch("arakis.auth.jwt.get_settings")
    def test_decode_expired_refresh_token(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret-key"
        mock_settings.return_value.algorithm = "HS256"

        expired_delta = timedelta(seconds=-1)
        token, _ = create_refresh_token("user-123", expires_delta=expired_delta)

        with pytest.raises(TokenExpiredError):
            decode_refresh_token(token)


class TestHashToken:
    """Tests for token hashing."""

    def test_hash_token_returns_sha256(self):
        token = "test-token-123"
        result = hash_token(token)

        expected = hashlib.sha256(token.encode()).hexdigest()
        assert result == expected
        assert len(result) == 64

    def test_hash_token_deterministic(self):
        token = "test-token-123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

    def test_hash_token_different_inputs(self):
        hash1 = hash_token("token-1")
        hash2 = hash_token("token-2")
        assert hash1 != hash2


# ============================================================
# Schema Tests
# ============================================================


class TestUserInfo:
    """Tests for UserInfo schema."""

    def test_create_user_info(self):
        user_info = UserInfo(
            id="google-123",
            email="test@example.com",
            email_verified=True,
            name="Test User",
            picture="https://example.com/photo.jpg",
            provider="google",
        )

        assert user_info.id == "google-123"
        assert user_info.email == "test@example.com"
        assert user_info.email_verified is True
        assert user_info.name == "Test User"
        assert user_info.picture == "https://example.com/photo.jpg"
        assert user_info.provider == "google"

    def test_user_info_optional_fields(self):
        user_info = UserInfo(
            id="apple-456",
            email="user@icloud.com",
            provider="apple",
        )

        assert user_info.id == "apple-456"
        assert user_info.email == "user@icloud.com"
        assert user_info.email_verified is False  # Default
        assert user_info.name is None
        assert user_info.picture is None


class TestTokenResponse:
    """Tests for TokenResponse schema."""

    def test_create_token_response(self):
        response = TokenResponse(
            access_token="access.token.here",
            refresh_token="refresh.token.here",
            expires_in=1800,
        )

        assert response.access_token == "access.token.here"
        assert response.refresh_token == "refresh.token.here"
        assert response.token_type == "bearer"
        assert response.expires_in == 1800


class TestRefreshTokenRequest:
    """Tests for RefreshTokenRequest schema."""

    def test_create_refresh_request(self):
        request = RefreshTokenRequest(refresh_token="my.refresh.token")
        assert request.refresh_token == "my.refresh.token"


class TestOAuthState:
    """Tests for OAuthState schema."""

    def test_create_oauth_state(self):
        state = OAuthState(
            state="random-state-string",
            redirect_url="/dashboard",
        )

        assert state.state == "random-state-string"
        assert state.redirect_url == "/dashboard"
        assert state.created_at is not None


# ============================================================
# OAuth Provider Tests
# ============================================================


class TestGoogleOAuthProvider:
    """Tests for Google OAuth provider."""

    @patch("arakis.auth.providers.google.get_settings")
    def test_provider_name(self, mock_settings):
        from arakis.auth.providers.google import GoogleOAuthProvider

        mock_settings.return_value.google_client_id = "test-client-id"
        provider = GoogleOAuthProvider()
        assert provider.name == "google"

    @patch("arakis.auth.providers.google.get_settings")
    def test_get_authorization_url(self, mock_settings):
        from arakis.auth.providers.google import GoogleOAuthProvider

        mock_settings.return_value.google_client_id = "test-client-id"
        mock_settings.return_value.google_redirect_uri = "http://localhost:8000/callback"

        provider = GoogleOAuthProvider()
        url = provider.get_authorization_url("state-123")

        assert "accounts.google.com" in url
        assert "client_id=test-client-id" in url
        assert "state=state-123" in url
        assert "response_type=code" in url
        assert "scope=openid" in url

    @patch("arakis.auth.providers.google.get_settings")
    def test_get_authorization_url_not_configured(self, mock_settings):
        from arakis.auth.providers.google import GoogleOAuthProvider

        mock_settings.return_value.google_client_id = ""

        provider = GoogleOAuthProvider()

        with pytest.raises(OAuthError) as exc_info:
            provider.get_authorization_url("state-123")
        assert "not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("arakis.auth.providers.google.get_settings")
    async def test_get_user_info_not_configured(self, mock_settings):
        from arakis.auth.providers.google import GoogleOAuthProvider

        mock_settings.return_value.google_client_id = ""
        mock_settings.return_value.google_client_secret = ""

        provider = GoogleOAuthProvider()

        with pytest.raises(OAuthError) as exc_info:
            await provider.get_user_info("auth-code")
        assert "not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("arakis.auth.providers.google.get_settings")
    @patch("httpx.AsyncClient")
    async def test_get_user_info_success(self, mock_client_class, mock_settings):
        from arakis.auth.providers.google import GoogleOAuthProvider

        mock_settings.return_value.google_client_id = "test-client-id"
        mock_settings.return_value.google_client_secret = "test-secret"
        mock_settings.return_value.google_redirect_uri = "http://localhost/callback"

        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "test-access-token"}

        # Mock userinfo response
        mock_userinfo_response = MagicMock()
        mock_userinfo_response.status_code = 200
        mock_userinfo_response.json.return_value = {
            "id": "google-user-123",
            "email": "user@gmail.com",
            "verified_email": True,
            "name": "Test User",
            "picture": "https://photo.url",
        }

        # Setup async client mock
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_response
        mock_client.get.return_value = mock_userinfo_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        provider = GoogleOAuthProvider()
        user_info = await provider.get_user_info("auth-code")

        assert user_info.id == "google-user-123"
        assert user_info.email == "user@gmail.com"
        assert user_info.email_verified is True
        assert user_info.name == "Test User"
        assert user_info.provider == "google"


class TestAppleOAuthProvider:
    """Tests for Apple OAuth provider."""

    @patch("arakis.auth.providers.apple.get_settings")
    def test_provider_name(self, mock_settings):
        from arakis.auth.providers.apple import AppleOAuthProvider

        mock_settings.return_value.apple_client_id = "test-client-id"
        provider = AppleOAuthProvider()
        assert provider.name == "apple"

    @patch("arakis.auth.providers.apple.get_settings")
    def test_get_authorization_url(self, mock_settings):
        from arakis.auth.providers.apple import AppleOAuthProvider

        mock_settings.return_value.apple_client_id = "com.example.app"
        mock_settings.return_value.frontend_url = "http://localhost:3000"

        provider = AppleOAuthProvider()
        url = provider.get_authorization_url("state-456")

        assert "appleid.apple.com" in url
        assert "client_id=com.example.app" in url
        assert "state=state-456" in url
        assert "response_mode=form_post" in url

    @patch("arakis.auth.providers.apple.get_settings")
    def test_get_authorization_url_not_configured(self, mock_settings):
        from arakis.auth.providers.apple import AppleOAuthProvider

        mock_settings.return_value.apple_client_id = ""

        provider = AppleOAuthProvider()

        with pytest.raises(OAuthError) as exc_info:
            provider.get_authorization_url("state-456")
        assert "not configured" in str(exc_info.value)


# ============================================================
# Auth Service Tests
# ============================================================


class TestAuthService:
    """Tests for AuthService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = "user-123"
        user.email = "test@example.com"
        user.google_id = None
        user.apple_id = None
        user.full_name = None
        user.avatar_url = None
        user.is_active = True
        return user

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_get_or_create_oauth_user_new_user(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        # Mock no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        user_info = UserInfo(
            id="google-123",
            email="new@example.com",
            email_verified=True,
            name="New User",
            picture="https://photo.url",
            provider="google",
        )

        await service.get_or_create_oauth_user(user_info)

        # Should add new user
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_create_tokens(self, mock_settings, mock_db, mock_user):
        from arakis.auth.service import AuthService

        mock_settings.return_value.access_token_expire_minutes = 30
        mock_settings.return_value.refresh_token_expire_days = 30
        mock_settings.return_value.secret_key = "test-secret"
        mock_settings.return_value.algorithm = "HS256"

        service = AuthService(mock_db)
        tokens = await service.create_tokens(mock_user, device_info="Test Browser")

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in == 1800  # 30 minutes

        # Should store refresh token in DB
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_revoke_refresh_token(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        result = await service.revoke_refresh_token("some-token")

        assert result is True
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_revoke_refresh_token_not_found(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        result = await service.revoke_refresh_token("invalid-token")

        assert result is False

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_check_trial_limit_no_existing(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        result = await service.check_trial_limit("session-123")

        assert result is False  # No existing workflow

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_check_trial_limit_existing(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_workflow = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        result = await service.check_trial_limit("session-123")

        assert result is True  # Has existing workflow

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_claim_trial_workflows(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        count = await service.claim_trial_workflows("user-123", "session-456")

        assert count == 2
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_get_user_by_id(self, mock_settings, mock_db, mock_user):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        user = await service.get_user_by_id("user-123")

        assert user == mock_user

    @pytest.mark.asyncio
    @patch("arakis.auth.service.get_settings")
    async def test_get_user_by_id_not_found(self, mock_settings, mock_db):
        from arakis.auth.service import AuthService

        mock_settings.return_value.refresh_token_expire_days = 30

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = AuthService(mock_db)
        user = await service.get_user_by_id("nonexistent")

        assert user is None


# ============================================================
# Integration-style Tests
# ============================================================


class TestTokenRoundTrip:
    """Test complete token creation and validation cycle."""

    @patch("arakis.auth.jwt.get_settings")
    def test_access_token_round_trip(self, mock_settings):
        mock_settings.return_value.secret_key = "integration-test-secret"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.access_token_expire_minutes = 30

        # Create token
        token = create_access_token("user-round-trip", "roundtrip@test.com")

        # Decode and verify
        payload = decode_access_token(token)
        assert payload["sub"] == "user-round-trip"
        assert payload["email"] == "roundtrip@test.com"

    @patch("arakis.auth.jwt.get_settings")
    def test_refresh_token_round_trip(self, mock_settings):
        mock_settings.return_value.secret_key = "integration-test-secret"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.refresh_token_expire_days = 30

        # Create token
        token, token_hash = create_refresh_token("user-round-trip")

        # Decode and verify
        payload = decode_refresh_token(token)
        assert payload["sub"] == "user-round-trip"

        # Verify hash
        assert hash_token(token) == token_hash


class TestTokenSecurity:
    """Test security aspects of tokens."""

    @patch("arakis.auth.jwt.get_settings")
    def test_wrong_secret_key_fails(self, mock_settings):
        mock_settings.return_value.secret_key = "correct-secret"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.access_token_expire_minutes = 30

        token = create_access_token("user-123", "test@test.com")

        # Change secret key
        mock_settings.return_value.secret_key = "wrong-secret"

        with pytest.raises(InvalidCredentialsError):
            decode_access_token(token)

    @patch("arakis.auth.jwt.get_settings")
    def test_tampered_token_fails(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.access_token_expire_minutes = 30

        token = create_access_token("user-123", "test@test.com")

        # Tamper with token
        parts = token.split(".")
        parts[1] = parts[1][:-4] + "XXXX"  # Modify payload
        tampered = ".".join(parts)

        with pytest.raises(InvalidCredentialsError):
            decode_access_token(tampered)

    @patch("arakis.auth.jwt.get_settings")
    def test_refresh_tokens_are_unique(self, mock_settings):
        mock_settings.return_value.secret_key = "test-secret"
        mock_settings.return_value.algorithm = "HS256"
        mock_settings.return_value.refresh_token_expire_days = 30

        # Create multiple refresh tokens
        token1, hash1 = create_refresh_token("user-123")
        token2, hash2 = create_refresh_token("user-123")

        # Should be different (unique jti)
        assert token1 != token2
        assert hash1 != hash2
