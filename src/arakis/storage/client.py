"""S3-compatible storage client for PDF and file storage."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from arakis.config import get_settings


@dataclass
class StorageResult:
    """Result of a storage operation."""

    success: bool
    key: str | None = None
    url: str | None = None
    error: str | None = None
    size_bytes: int | None = None


@dataclass
class StorageHealth:
    """Health status of storage connection."""

    connected: bool
    bucket_exists: bool
    bucket_name: str
    endpoint: str | None
    error: str | None = None


class StorageClient:
    """
    S3-compatible storage client for Cloudflare R2, AWS S3, or MinIO.

    Handles PDF storage and retrieval with automatic key generation
    based on paper identifiers.
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_name: str | None = None,
        region: str = "auto",
    ):
        settings = get_settings()

        self.endpoint_url = endpoint_url or settings.s3_endpoint
        self.access_key = access_key or settings.s3_access_key
        self.secret_key = secret_key or settings.s3_secret_key
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.region = region or settings.s3_region

        self._client = None

    @property
    def client(self):
        """Lazy-initialize S3 client."""
        if self._client is None:
            if not all([self.endpoint_url, self.access_key, self.secret_key]):
                raise ValueError(
                    "S3 storage not configured. Set S3_ENDPOINT, S3_ACCESS_KEY, and S3_SECRET_KEY."
                )

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "adaptive"},
                ),
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        """Check if storage is configured."""
        return all([self.endpoint_url, self.access_key, self.secret_key])

    def health_check(self) -> StorageHealth:
        """
        Check storage connection health.

        Returns:
            StorageHealth with connection status
        """
        if not self.is_configured:
            return StorageHealth(
                connected=False,
                bucket_exists=False,
                bucket_name=self.bucket_name,
                endpoint=self.endpoint_url,
                error="Storage not configured",
            )

        try:
            # Try to head the bucket to verify connection and bucket existence
            self.client.head_bucket(Bucket=self.bucket_name)
            return StorageHealth(
                connected=True,
                bucket_exists=True,
                bucket_name=self.bucket_name,
                endpoint=self.endpoint_url,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return StorageHealth(
                    connected=True,
                    bucket_exists=False,
                    bucket_name=self.bucket_name,
                    endpoint=self.endpoint_url,
                    error=f"Bucket '{self.bucket_name}' does not exist",
                )
            return StorageHealth(
                connected=False,
                bucket_exists=False,
                bucket_name=self.bucket_name,
                endpoint=self.endpoint_url,
                error=str(e),
            )
        except NoCredentialsError:
            return StorageHealth(
                connected=False,
                bucket_exists=False,
                bucket_name=self.bucket_name,
                endpoint=self.endpoint_url,
                error="Invalid credentials",
            )
        except Exception as e:
            return StorageHealth(
                connected=False,
                bucket_exists=False,
                bucket_name=self.bucket_name,
                endpoint=self.endpoint_url,
                error=str(e),
            )

    def generate_key(self, paper_id: str, file_type: str = "pdf") -> str:
        """
        Generate a storage key for a paper.

        Args:
            paper_id: Paper identifier (DOI, PMID, etc.)
            file_type: File extension (default: pdf)

        Returns:
            Storage key path
        """
        # Create a safe filename from paper_id
        safe_id = hashlib.sha256(paper_id.encode()).hexdigest()[:16]
        # Also keep a readable prefix
        readable = "".join(c if c.isalnum() else "_" for c in paper_id[:50])
        return f"papers/{readable}_{safe_id}.{file_type}"

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/pdf",
        metadata: dict | None = None,
    ) -> StorageResult:
        """
        Upload bytes to storage.

        Args:
            data: File content as bytes
            key: Storage key/path
            content_type: MIME type
            metadata: Optional metadata dict

        Returns:
            StorageResult with success status and URL
        """
        if not self.is_configured:
            return StorageResult(
                success=False,
                error="Storage not configured",
            )

        try:
            extra_args: dict[str, Any] = {"ContentType": content_type}
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_fileobj(
                io.BytesIO(data),
                self.bucket_name,
                key,
                ExtraArgs=extra_args,
            )

            # Generate URL
            url = f"{self.endpoint_url}/{self.bucket_name}/{key}"

            return StorageResult(
                success=True,
                key=key,
                url=url,
                size_bytes=len(data),
            )
        except Exception as e:
            return StorageResult(
                success=False,
                key=key,
                error=str(e),
            )

    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/pdf",
        metadata: dict | None = None,
    ) -> StorageResult:
        """
        Upload a file object to storage.

        Args:
            file_obj: File-like object
            key: Storage key/path
            content_type: MIME type
            metadata: Optional metadata dict

        Returns:
            StorageResult with success status and URL
        """
        if not self.is_configured:
            return StorageResult(
                success=False,
                error="Storage not configured",
            )

        try:
            extra_args: dict[str, Any] = {"ContentType": content_type}
            if metadata:
                extra_args["Metadata"] = metadata

            # Get file size
            file_obj.seek(0, 2)
            size = file_obj.tell()
            file_obj.seek(0)

            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args,
            )

            url = f"{self.endpoint_url}/{self.bucket_name}/{key}"

            return StorageResult(
                success=True,
                key=key,
                url=url,
                size_bytes=size,
            )
        except Exception as e:
            return StorageResult(
                success=False,
                key=key,
                error=str(e),
            )

    def upload_paper_pdf(
        self,
        paper_id: str,
        pdf_content: bytes,
        metadata: dict | None = None,
    ) -> StorageResult:
        """
        Upload a paper's PDF to storage.

        Args:
            paper_id: Paper identifier (DOI, PMID, etc.)
            pdf_content: PDF file content as bytes
            metadata: Optional metadata (title, source, etc.)

        Returns:
            StorageResult with success status and URL
        """
        key = self.generate_key(paper_id, "pdf")

        # Add paper_id to metadata
        meta = metadata or {}
        meta["paper_id"] = paper_id
        meta["uploaded_at"] = datetime.now(timezone.utc).isoformat()

        return self.upload_bytes(
            data=pdf_content,
            key=key,
            content_type="application/pdf",
            metadata=meta,
        )

    def download_bytes(self, key: str) -> tuple[bytes | None, StorageResult]:
        """
        Download file content from storage.

        Args:
            key: Storage key/path

        Returns:
            Tuple of (content bytes or None, StorageResult)
        """
        if not self.is_configured:
            return None, StorageResult(
                success=False,
                error="Storage not configured",
            )

        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            content = response["Body"].read()
            size = response.get("ContentLength", len(content))

            return content, StorageResult(
                success=True,
                key=key,
                size_bytes=size,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            return None, StorageResult(
                success=False,
                key=key,
                error=f"Download failed: {error_code}",
            )
        except Exception as e:
            return None, StorageResult(
                success=False,
                key=key,
                error=str(e),
            )

    def download_paper_pdf(self, paper_id: str) -> tuple[bytes | None, StorageResult]:
        """
        Download a paper's PDF from storage.

        Args:
            paper_id: Paper identifier

        Returns:
            Tuple of (PDF bytes or None, StorageResult)
        """
        key = self.generate_key(paper_id, "pdf")
        return self.download_bytes(key)

    def exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            key: Storage key/path

        Returns:
            True if file exists
        """
        if not self.is_configured:
            return False

        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def paper_pdf_exists(self, paper_id: str) -> bool:
        """
        Check if a paper's PDF exists in storage.

        Args:
            paper_id: Paper identifier

        Returns:
            True if PDF exists
        """
        key = self.generate_key(paper_id, "pdf")
        return self.exists(key)

    def delete(self, key: str) -> StorageResult:
        """
        Delete a file from storage.

        Args:
            key: Storage key/path

        Returns:
            StorageResult with success status
        """
        if not self.is_configured:
            return StorageResult(
                success=False,
                error="Storage not configured",
            )

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return StorageResult(
                success=True,
                key=key,
            )
        except Exception as e:
            return StorageResult(
                success=False,
                key=key,
                error=str(e),
            )

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        """
        Generate a presigned URL for temporary access.

        Args:
            key: Storage key/path
            expires_in: URL validity in seconds (default: 1 hour)

        Returns:
            Presigned URL or None if failed
        """
        if not self.is_configured:
            return None

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception:
            return None

    def list_papers(self, prefix: str = "papers/", limit: int = 100) -> list[str]:
        """
        List paper PDFs in storage.

        Args:
            prefix: Key prefix to filter
            limit: Maximum number of results

        Returns:
            List of storage keys
        """
        if not self.is_configured:
            return []

        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=limit,
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception:
            return []


@lru_cache
def get_storage_client() -> StorageClient:
    """Get cached storage client instance."""
    return StorageClient()
