import re
from typing import List
from app.infrastructure.parsers.base import DocumentParser, ParsedDocument, ParsedSection


class StandardDocumentParser(DocumentParser):
    SUPPORTED_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }

    def supports(self, mime_type: str) -> bool:
        return mime_type.lower() in self.SUPPORTED_MIME_TYPES

    async def parse(self, file_bytes: bytes, file_name: str, mime_type: str) -> ParsedDocument:
        raw_text = ""
        try:
            raw_text = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            raw_text = str(file_bytes)

        sections: List[ParsedSection] = []
        lines = raw_text.splitlines()
        current_heading = "General Overview"
        current_buffer: List[str] = []
        page_num = 1

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Heading Detection (Markdown style # or capital header)
            if line_str.startswith("#") or (len(line_str) < 80 and line_str.isupper()):
                if current_buffer:
                    sections.append(
                        ParsedSection(
                            title=current_heading,
                            content="\n".join(current_buffer),
                            page_number=page_num,
                            is_table=False
                        )
                    )
                    current_buffer = []
                current_heading = line_str.lstrip("#").strip()
            else:
                current_buffer.append(line_str)

        if current_buffer:
            sections.append(
                ParsedSection(
                    title=current_heading,
                    content="\n".join(current_buffer),
                    page_number=page_num,
                    is_table=False
                )
            )

        full_text = "\n\n".join([f"## {s.title}\n{s.content}" for s in sections])

        return ParsedDocument(
            title=file_name,
            sections=sections,
            full_text=full_text,
            metadata={"parser": "StandardDocumentParser", "section_count": len(sections)}
        )
