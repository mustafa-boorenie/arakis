"""S3-compatible object storage module for Arakis."""

from arakis.storage.client import StorageClient, get_storage_client

__all__ = ["StorageClient", "get_storage_client"]
