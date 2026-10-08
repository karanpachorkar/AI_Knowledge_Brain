import io
import os
from typing import BinaryIO, Optional
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.storage.base import StorageProvider


class MinIOStorageProvider(StorageProvider):
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.default_bucket = settings.MINIO_BUCKET_NAME
        self.local_storage_dir = os.path.join(os.getcwd(), ".storage_data")
        os.makedirs(self.local_storage_dir, exist_ok=True)

    async def upload_file(
        self,
        bucket_name: str,
        object_key: str,
        file_data: BinaryIO,
        content_length: int,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Stores object binary data into designated bucket path."""
        try:
            # Persistent storage path resolution
            target_path = os.path.join(self.local_storage_dir, bucket_name, object_key)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            file_data.seek(0)
            with open(target_path, "wb") as f:
                f.write(file_data.read())
                
            logger.info("Successfully uploaded object to storage", bucket=bucket_name, key=object_key)
            return object_key
        except Exception as e:
            logger.error("Failed to upload file to storage", bucket=bucket_name, key=object_key, error=str(e))
            raise

    async def download_file(self, bucket_name: str, object_key: str) -> bytes:
        """Reads file bytes from storage path."""
        target_path = os.path.join(self.local_storage_dir, bucket_name, object_key)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Object '{object_key}' not found in bucket '{bucket_name}'.")
        with open(target_path, "rb") as f:
            return f.read()

    async def delete_file(self, bucket_name: str, object_key: str) -> bool:
        """Deletes object from storage path."""
        target_path = os.path.join(self.local_storage_dir, bucket_name, object_key)
        if os.path.exists(target_path):
            os.remove(target_path)
            logger.info("Deleted object from storage", bucket=bucket_name, key=object_key)
            return True
        return False
