"""
Rich content extraction from AI responses.

Extracts structured content elements like:
- Code blocks (with language detection)
- Hyperlinks (URLs)
- Tables (markdown tables)
- Lists (ordered/unordered)
- Citations/references
- Embedded entities (locations, businesses, etc.)
- Images (URLs/references)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class CodeBlock:
    """Extracted code block from response."""
    language: str | None
    code: str
    line_count: int

    def to_dict(self) -> dict:
        return {
            "type": "code",
            "language": self.language,
            "code": self.code,
            "line_count": self.line_count,
        }


@dataclass
class Hyperlink:
    """Extracted hyperlink from response."""
    url: str
    text: str | None = None
    context: str | None = None  # Surrounding text for context

    def to_dict(self) -> dict:
        result = {"type": "link", "url": self.url}
        if self.text:
            result["text"] = self.text
        if self.context:
            result["context"] = self.context
        return result


@dataclass
class Table:
    """Extracted markdown table from response."""
    headers: list[str]
    rows: list[list[str]]
    row_count: int

    def to_dict(self) -> dict:
        return {
            "type": "table",
            "headers": self.headers,
            "rows": self.rows,
            "row_count": self.row_count,
        }


@dataclass
class Citation:
    """Extracted citation/reference from response."""
    id: str
    source: str | None = None
    url: str | None = None

    def to_dict(self) -> dict:
        result = {"type": "citation", "id": self.id}
        if self.source:
            result["source"] = self.source
        if self.url:
            result["url"] = self.url
        return result


@dataclass
class Entity:
    """Extracted entity (business, location, person, etc.)."""
    entity_type: Literal["business", "location", "person", "organization", "other"]
    name: str
    id: str | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        result = {
            "type": "entity",
            "entity_type": self.entity_type,
            "name": self.name,
        }
        if self.id:
            result["id"] = self.id
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class ListItem:
    """Extracted list from response."""
    list_type: Literal["ordered", "unordered", "checklist"]
    items: list[str]
    item_count: int

    def to_dict(self) -> dict:
        return {
            "type": "list",
            "list_type": self.list_type,
            "items": self.items,
            "item_count": self.item_count,
        }


@dataclass
class ContentAnalysis:
    """Analysis result for AI response content."""

    # Raw content stats
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0

    # Extracted elements
    code_blocks: list[CodeBlock] = field(default_factory=list)
    hyperlinks: list[Hyperlink] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    lists: list[ListItem] = field(default_factory=list)

    # Content flags
    has_markdown: bool = False
    has_emoji: bool = False
    has_math: bool = False

    # Language detection (for non-English responses)
    detected_language: str | None = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "stats": {
                "chars": self.char_count,
                "words": self.word_count,
                "lines": self.line_count,
            },
            "flags": {
                "has_markdown": self.has_markdown,
                "has_emoji": self.has_emoji,
                "has_math": self.has_math,
            },
        }

        if self.code_blocks:
            result["code_blocks"] = [cb.to_dict() for cb in self.code_blocks]
        if self.hyperlinks:
            result["hyperlinks"] = [hl.to_dict() for hl in self.hyperlinks]
        if self.tables:
            result["tables"] = [t.to_dict() for t in self.tables]
        if self.citations:
            result["citations"] = [c.to_dict() for c in self.citations]
        if self.entities:
            result["entities"] = [e.to_dict() for e in self.entities]
        if self.lists:
            result["lists"] = [li.to_dict() for li in self.lists]
        if self.detected_language:
            result["detected_language"] = self.detected_language

        return result


class ContentExtractor:
    """Extracts rich content elements from AI response text."""

    # Regex patterns
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w*)\n(.*?)```',
        re.DOTALL
    )

    INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')

    # Markdown link: [text](url)
    MARKDOWN_LINK_PATTERN = re.compile(
        r'\[([^\]]+)\]\(([^)]+)\)'
    )

    # Raw URLs
    URL_PATTERN = re.compile(
        r'https?://[^\s<>\[\]()"\',]+[^\s<>\[\]()"\',.]'
    )

    # Markdown table: | header | header |
    TABLE_PATTERN = re.compile(
        r'^\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)+)',
        re.MULTILINE
    )

    # Markdown headers
    HEADER_PATTERN = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)

    # Bold/italic
    BOLD_PATTERN = re.compile(r'\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_')

    # Ordered list: 1. item, 2. item
    ORDERED_LIST_PATTERN = re.compile(
        r'(?:^|\n)(\d+\.\s+.+(?:\n(?!\d+\.)\s+.+)*)',
        re.MULTILINE
    )

    # Unordered list: - item, * item, • item
    UNORDERED_LIST_PATTERN = re.compile(
        r'(?:^|\n)([-*•]\s+.+(?:\n(?![-*•])\s+.+)*)',
        re.MULTILINE
    )

    # Checklist: - [ ] item, - [x] item
    CHECKLIST_PATTERN = re.compile(
        r'(?:^|\n)(-\s+\[[ xX]\]\s+.+)',
        re.MULTILINE
    )

    # Emoji pattern (basic Unicode emoji ranges)
    EMOJI_PATTERN = re.compile(
        r'[\U0001F300-\U0001F9FF]|[\U00002600-\U000027BF]|[\U0001F600-\U0001F64F]'
    )

    # Math: $...$ or $$...$$
    MATH_PATTERN = re.compile(r'\$\$?.+?\$\$?', re.DOTALL)

    # ChatGPT entity markers: \ue200entity\ue202[...]\ue201
    CHATGPT_ENTITY_PATTERN = re.compile(
        r'\ue200entity\ue202\[([^\]]+)\]\ue201'
    )

    # ChatGPT citation markers: \ue200cite\ue202...\ue201
    CHATGPT_CITE_PATTERN = re.compile(
        r'\ue200cite\ue202([^\ue201]+)\ue201'
    )

    def extract(self, content: str) -> ContentAnalysis:
        """
        Extract all rich content elements from response text.

        Args:
            content: The raw response content string

        Returns:
            ContentAnalysis with all extracted elements
        """
        if not content:
            return ContentAnalysis()

        analysis = ContentAnalysis(
            char_count=len(content),
            word_count=len(content.split()),
            line_count=content.count('\n') + 1,
        )

        # Extract code blocks
        analysis.code_blocks = self._extract_code_blocks(content)

        # Extract hyperlinks
        analysis.hyperlinks = self._extract_hyperlinks(content)

        # Extract tables
        analysis.tables = self._extract_tables(content)

        # Extract lists
        analysis.lists = self._extract_lists(content)

        # Extract ChatGPT-specific elements
        analysis.entities = self._extract_chatgpt_entities(content)
        analysis.citations = self._extract_chatgpt_citations(content)

        # Detect content flags
        analysis.has_markdown = self._has_markdown(content)
        analysis.has_emoji = bool(self.EMOJI_PATTERN.search(content))
        analysis.has_math = bool(self.MATH_PATTERN.search(content))

        return analysis

    def _extract_code_blocks(self, content: str) -> list[CodeBlock]:
        """Extract fenced code blocks."""
        blocks = []

        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or None
            code = match.group(2).strip()
            line_count = code.count('\n') + 1

            blocks.append(CodeBlock(
                language=language,
                code=code,
                line_count=line_count,
            ))

        return blocks

    def _extract_hyperlinks(self, content: str) -> list[Hyperlink]:
        """Extract markdown links and raw URLs."""
        links = []
        seen_urls = set()

        # First extract markdown links [text](url)
        for match in self.MARKDOWN_LINK_PATTERN.finditer(content):
            text = match.group(1)
            url = match.group(2)
            if url not in seen_urls:
                seen_urls.add(url)
                links.append(Hyperlink(url=url, text=text))

        # Then extract raw URLs not in markdown format
        for match in self.URL_PATTERN.finditer(content):
            url = match.group(0)
            if url not in seen_urls:
                seen_urls.add(url)
                # Get surrounding context (20 chars before/after)
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end].strip()
                links.append(Hyperlink(url=url, context=context))

        return links

    def _extract_tables(self, content: str) -> list[Table]:
        """Extract markdown tables."""
        tables = []

        for match in self.TABLE_PATTERN.finditer(content):
            header_row = match.group(1)
            body_rows = match.group(2)

            # Parse headers
            headers = [h.strip() for h in header_row.split('|') if h.strip()]

            # Parse body rows
            rows = []
            for row_line in body_rows.strip().split('\n'):
                cells = [c.strip() for c in row_line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)

            if headers and rows:
                tables.append(Table(
                    headers=headers,
                    rows=rows,
                    row_count=len(rows),
                ))

        return tables

    def _extract_lists(self, content: str) -> list[ListItem]:
        """Extract ordered, unordered, and checklists."""
        lists = []

        # Check for checklists first (more specific)
        checklist_matches = self.CHECKLIST_PATTERN.findall(content)
        if checklist_matches:
            items = [m.strip() for m in checklist_matches]
            if items:
                lists.append(ListItem(
                    list_type="checklist",
                    items=items,
                    item_count=len(items),
                ))

        # Ordered lists
        ordered_matches = self.ORDERED_LIST_PATTERN.findall(content)
        if ordered_matches:
            # Extract individual items
            items = []
            for block in ordered_matches:
                for line in block.split('\n'):
                    line = line.strip()
                    if re.match(r'^\d+\.\s+', line):
                        items.append(re.sub(r'^\d+\.\s+', '', line))
            if items:
                lists.append(ListItem(
                    list_type="ordered",
                    items=items,
                    item_count=len(items),
                ))

        # Unordered lists
        unordered_matches = self.UNORDERED_LIST_PATTERN.findall(content)
        if unordered_matches:
            items = []
            for block in unordered_matches:
                for line in block.split('\n'):
                    line = line.strip()
                    if re.match(r'^[-*•]\s+', line):
                        items.append(re.sub(r'^[-*•]\s+', '', line))
            if items:
                lists.append(ListItem(
                    list_type="unordered",
                    items=items,
                    item_count=len(items),
                ))

        return lists

    def _extract_chatgpt_entities(self, content: str) -> list[Entity]:
        """Extract ChatGPT entity markers."""
        entities = []

        for match in self.CHATGPT_ENTITY_PATTERN.finditer(content):
            entity_data = match.group(1)
            try:
                # Parse the entity array: ["turn0business1","THE PLANT cafe organic",1]
                import json
                parts = json.loads(f'[{entity_data}]')
                if len(parts) >= 2:
                    entity_id = parts[0] if isinstance(parts[0], str) else None
                    name = parts[1] if isinstance(parts[1], str) else str(parts[1])

                    # Detect entity type from ID
                    entity_type: Literal["business", "location", "person", "organization", "other"] = "other"
                    if entity_id:
                        if "business" in entity_id:
                            entity_type = "business"
                        elif "location" in entity_id or "place" in entity_id:
                            entity_type = "location"
                        elif "person" in entity_id:
                            entity_type = "person"
                        elif "org" in entity_id:
                            entity_type = "organization"

                    entities.append(Entity(
                        entity_type=entity_type,
                        name=name,
                        id=entity_id,
                        metadata={"index": parts[2]} if len(parts) > 2 else None,
                    ))
            except (json.JSONDecodeError, IndexError, TypeError):
                # If parsing fails, create a basic entity
                entities.append(Entity(
                    entity_type="other",
                    name=entity_data,
                ))

        return entities

    def _extract_chatgpt_citations(self, content: str) -> list[Citation]:
        """Extract ChatGPT citation markers."""
        citations = []
        seen_ids = set()

        for match in self.CHATGPT_CITE_PATTERN.finditer(content):
            cite_data = match.group(1)
            # Citations can be multiple IDs separated by \ue202
            for cite_id in cite_data.split('\ue202'):
                cite_id = cite_id.strip()
                if cite_id and cite_id not in seen_ids:
                    seen_ids.add(cite_id)
                    citations.append(Citation(
                        id=cite_id,
                        source="chatgpt_search" if "search" in cite_id else None,
                    ))

        return citations

    def _has_markdown(self, content: str) -> bool:
        """Check if content contains markdown formatting."""
        return bool(
            self.HEADER_PATTERN.search(content) or
            self.BOLD_PATTERN.search(content) or
            self.CODE_BLOCK_PATTERN.search(content) or
            self.TABLE_PATTERN.search(content) or
            self.MARKDOWN_LINK_PATTERN.search(content)
        )


# Module-level instance for convenience
_extractor = ContentExtractor()


def extract_content(content: str) -> ContentAnalysis:
    """
    Extract rich content elements from AI response text.

    This is the main entry point for content extraction.

    Args:
        content: The raw response content string

    Returns:
        ContentAnalysis with all extracted elements
    """
    return _extractor.extract(content)
