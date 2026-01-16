"""Authentication service for user management and OAuth handling."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.auth.exceptions import UserNotFoundError
from arakis.auth.jwt import create_access_token, create_refresh_token, hash_token
from arakis.auth.schemas import TokenResponse, UserInfo
from arakis.config import get_settings
from arakis.database.models import RefreshToken, User, Workflow


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_or_create_oauth_user(self, user_info: UserInfo) -> User:
        """
        Get existing user or create new one from OAuth info.

        Args:
            user_info: User information from OAuth provider

        Returns:
            User model instance
        """
        user = None

        # Try to find by provider ID
        if user_info.provider == "google":
            result = await self.db.execute(
                select(User).where(User.google_id == user_info.id)
            )
            user = result.scalar_one_or_none()
        elif user_info.provider == "apple":
            result = await self.db.execute(
                select(User).where(User.apple_id == user_info.id)
            )
            user = result.scalar_one_or_none()

        # If not found by provider ID, try email
        if user is None:
            result = await self.db.execute(
                select(User).where(User.email == user_info.email)
            )
            user = result.scalar_one_or_none()

            if user:
                # Link existing account to OAuth provider
                if user_info.provider == "google":
                    user.google_id = user_info.id
                elif user_info.provider == "apple":
                    user.apple_id = user_info.id

                # Update user info from OAuth
                if user_info.name and not user.full_name:
                    user.full_name = user_info.name
                if user_info.picture and not user.avatar_url:
                    user.avatar_url = user_info.picture
                if user_info.email_verified:
                    user.email_verified = True

        # Create new user if not found
        if user is None:
            user = User(
                id=str(uuid4()),
                email=user_info.email,
                full_name=user_info.name,
                avatar_url=user_info.picture,
                email_verified=user_info.email_verified,
                auth_provider=user_info.provider,
                is_active=True,
            )

            if user_info.provider == "google":
                user.google_id = user_info.id
            elif user_info.provider == "apple":
                user.apple_id = user_info.id

            self.db.add(user)

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def create_tokens(self, user: User, device_info: str | None = None) -> TokenResponse:
        """
        Create access and refresh tokens for a user.

        Args:
            user: User model instance
            device_info: Optional device information

        Returns:
            TokenResponse with access and refresh tokens
        """
        # Create access token
        access_token = create_access_token(user.id, user.email)

        # Create refresh token
        refresh_token, token_hash = create_refresh_token(user.id)

        # Store refresh token in database
        db_refresh_token = RefreshToken(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=token_hash,
            device_info=device_info,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_token_expire_days),
        )
        self.db.add(db_refresh_token)
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

    async def refresh_tokens(
        self,
        user_id: str,
        old_token: str,
        device_info: str | None = None,
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            user_id: User ID from decoded refresh token
            old_token: The old refresh token
            device_info: Optional device information

        Returns:
            New TokenResponse

        Raises:
            UserNotFoundError: If user not found
        """
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise UserNotFoundError()

        # Revoke old refresh token
        old_token_hash = hash_token(old_token)
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == old_token_hash)
            .values(revoked_at=datetime.now(timezone.utc))
        )

        # Create new tokens
        return await self.create_tokens(user, device_info)

    async def revoke_refresh_token(self, token: str) -> bool:
        """
        Revoke a refresh token (logout).

        Args:
            token: The refresh token to revoke

        Returns:
            True if token was revoked
        """
        token_hash = hash_token(token)
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def validate_refresh_token(self, token: str) -> bool:
        """
        Check if refresh token is valid and not revoked.

        Args:
            token: The refresh token to validate

        Returns:
            True if token is valid
        """
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none() is not None

    async def claim_trial_workflows(self, user_id: str, session_id: str) -> int:
        """
        Claim anonymous trial workflows for authenticated user.

        Args:
            user_id: The authenticated user's ID
            session_id: The anonymous session ID

        Returns:
            Number of workflows claimed
        """
        result = await self.db.execute(
            update(Workflow)
            .where(Workflow.session_id == session_id, Workflow.user_id.is_(None))
            .values(user_id=user_id, session_id=None)
        )
        await self.db.commit()
        return result.rowcount

    async def get_user_by_id(self, user_id: str) -> User | None:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User model or None
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def check_trial_limit(self, session_id: str) -> bool:
        """
        Check if session has reached trial limit.

        Args:
            session_id: The session ID to check

        Returns:
            True if trial limit reached (has existing workflows)
        """
        result = await self.db.execute(
            select(Workflow).where(Workflow.session_id == session_id).limit(1)
        )
        return result.scalar_one_or_none() is not None
