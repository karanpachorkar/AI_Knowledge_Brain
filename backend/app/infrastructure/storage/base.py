from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class StorageProvider(ABC):
    @abstractmethod
    async def upload_file(
        self,
        bucket_name: str,
        object_key: str,
        file_data: BinaryIO,
        content_length: int,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Uploads a file stream to object storage and returns object key."""
        pass

    @abstractmethod
    async def download_file(self, bucket_name: str, object_key: str) -> bytes:
        """Downloads file content bytes from object storage."""
        pass

    @abstractmethod
    async def delete_file(self, bucket_name: str, object_key: str) -> bool:
        """Deletes an object from object storage."""
        pass
