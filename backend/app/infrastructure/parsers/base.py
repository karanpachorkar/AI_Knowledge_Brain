from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ParsedSection(BaseModel):
    title: Optional[str] = None
    content: str
    page_number: Optional[int] = None
    is_table: bool = False
    metadata: Dict = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    title: str
    sections: List[ParsedSection]
    full_text: str
    metadata: Dict = Field(default_factory=dict)


class DocumentParser(ABC):
    @abstractmethod
    def supports(self, mime_type: str) -> bool:
        """Returns True if the parser supports the given MIME type."""
        pass

    @abstractmethod
    async def parse(self, file_bytes: bytes, file_name: str, mime_type: str) -> ParsedDocument:
        """Parses document binary into structured sections, paragraphs, and tables."""
        pass
