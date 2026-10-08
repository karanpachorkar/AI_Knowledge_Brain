import hashlib
from typing import BinaryIO, Tuple
from fastapi import HTTPException, status

ALLOWED_MIME_TYPES = {
    "application/pdf": [b"%PDF"],
    "text/plain": [],
    "text/markdown": [],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK"],
    "application/msword": [b"\xd0\xcf\x11\xe0"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class FileValidationService:
    @staticmethod
    def calculate_checksum_and_validate(
        file_stream: BinaryIO,
        file_name: str,
        mime_type: str
    ) -> Tuple[str, int]:
        """Validates file signature, size limit, and calculates SHA-256 checksum."""
        file_stream.seek(0, 2)
        file_size = file_stream.tell()
        file_stream.seek(0)

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file_name}' exceeds maximum allowed size of 50MB."
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file_name}' is empty."
            )

        # Magic Bytes Signature Verification where applicable
        header_bytes = file_stream.read(16)
        file_stream.seek(0)

        if mime_type in ALLOWED_MIME_TYPES and ALLOWED_MIME_TYPES[mime_type]:
            valid_signature = False
            for expected_sig in ALLOWED_MIME_TYPES[mime_type]:
                if header_bytes.startswith(expected_sig):
                    valid_signature = True
                    break
            if not valid_signature:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File signature for '{file_name}' does not match declared MIME type '{mime_type}'."
                )

        # Calculate SHA-256 checksum
        hasher = hashlib.sha256()
        while chunk := file_stream.read(8192):
            hasher.update(chunk)
        file_stream.seek(0)

        checksum = hasher.hexdigest()
        return checksum, file_size
