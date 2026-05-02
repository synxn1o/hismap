"""TOC extraction and page-offset mapping for historical book PDFs.

Strategy:
1. Extract electronic TOC (PDF bookmarks/outline) — highest quality
2. Fallback: OCR the TOC pages and parse entries with page numbers
3. Calculate offset: PDF_page - book_page = constant (for most books)
4. Use TOC to drive targeted OCR (skip prefaces, jump to chapters)

Draft — not yet integrated.

Usage:
    mapper = TOCPageMapper(pdf_path)
    await mapper.load()
    # Get PDF page for book page 100
    pdf_page = mapper.book_to_pdf(100)
    # Get all TOC entries
    entries = mapper.entries
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────

@dataclass
class TOCEntry:
    """A single TOC entry."""
    title: str              # cleaned title text
    book_page: int          # page number as printed in the book
    pdf_page: int | None    # mapped PDF page (filled after offset calculation)
    level: int = 1          # nesting level (1=top, 2=sub)
    confidence: float = 1.0 # 1.0 for electronic, <1.0 for OCR
    source: str = "electronic"  # "electronic" or "ocr"
    raw_title: str = ""     # original text before cleaning

    @property
    def is_resolved(self) -> bool:
        return self.pdf_page is not None


@dataclass
class TOCResult:
    """Result of TOC extraction."""
    entries: list[TOCEntry] = field(default_factory=list)
    source: str = "none"          # "electronic", "ocr", "none"
    offset: int | None = None     # pdf_page = book_page + offset
    offset_confidence: float = 0.0
    toc_pdf_pages: list[int] = field(default_factory=list)  # which PDF pages are TOC
    content_start_pdf: int | None = None  # first non-frontmatter PDF page
    raw_electronic: list = field(default_factory=list)  # raw fitz outline
    raw_ocr_text: str = ""        # raw OCR text of TOC pages

    @property
    def has_entries(self) -> bool:
        return len(self.entries) > 0

    @property
    def book_page_range(self) -> tuple[int, int] | None:
        pages = [e.book_page for e in self.entries if e.book_page > 0]
        return (min(pages), max(pages)) if pages else None


# ──────────────────────────────────────────────────────────────
# Electronic TOC extraction
# ──────────────────────────────────────────────────────────────

def extract_electronic_toc(doc: fitz.Document) -> list[dict]:
    """Extract TOC from PDF bookmarks/outline.

    Returns list of {level, title, pdf_page}.
    PyMuPDF page numbers are 0-indexed internally, but get_toc() returns
    1-indexed page numbers.
    """
    toc = doc.get_toc()
    if not toc:
        return []

    entries = []
    for level, title, page in toc:
        if title.strip():
            entries.append({
                "level": level,
                "title": title.strip(),
                "pdf_page": page,  # 1-indexed
            })
    return entries


def is_frontmatter(electronic_toc: list[dict]) -> set[int]:
    """Identify PDF pages that are frontmatter (preface, TOC, etc.).

    Heuristic: pages before the first "content" bookmark.
    Content bookmarks typically start with chapter-like titles.
    """
    frontmatter_pages: set[int] = set()

    # Common frontmatter keywords
    fm_keywords = {
        '前言', '序言', '序', '译者的话', '校订者序言', '作者序',
        '目次', '目录', '内容', '索引', '凡例', '说明',
        'preface', 'foreword', 'introduction', 'contents',
        'table of contents', 'acknowledgments', 'dedication',
        '出版说明', '编者说明', '重印说明', '修订说明',
        '主要参考书目', '参考文献', 'bibliography',
    }

    for entry in electronic_toc:
        title_lower = entry["title"].lower().strip()
        # Check if it's frontmatter
        if any(kw in title_lower for kw in fm_keywords):
            # Add all pages from this entry to the next one (or +5 as estimate)
            frontmatter_pages.add(entry["pdf_page"])

    return frontmatter_pages


# ──────────────────────────────────────────────────────────────
# OCR-based TOC extraction
# ──────────────────────────────────────────────────────────────

# Patterns for TOC entries with page numbers
# Format: "title………………… 3" or "title... 22" or "title 22"
TOC_ENTRY_PATTERNS = [
    # Chinese dotted line style: 标题………………… 页码
    re.compile(r'^(.+?)[.…·]{3,}\s*(\d+)\s*$'),
    # Tab-separated: 标题\t页码
    re.compile(r'^(.+?)\s{3,}(\d+)\s*$'),
    # Simple: 标题 页码 (at least 2 spaces before number)
    re.compile(r'^(.+?)\s{2,}(\d{1,4})\s*$'),
    # Parenthesized: (标题) 页码
    re.compile(r'^[(\（](.+?)[)\）]\s*(\d+)\s*$'),
    # Roman numerals: 标题 ... iii
    re.compile(r'^(.+?)[.…\s]+([ivxlcdm]+)\s*$', re.IGNORECASE),
]


def parse_toc_text(raw_text: str) -> list[dict]:
    """Parse OCR'd TOC text into entries with titles and page numbers.

    Returns list of {title, book_page, raw_line}.
    """
    entries: list[dict] = []
    seen_pages: set[int] = set()

    for line in raw_text.split('\n'):
        line = line.strip()
        if not line or len(line) < 3:
            continue

        # Skip obvious non-TOC lines
        if re.match(r'^第?\d+页|^page\s+\d+|^\d+\s*$', line, re.IGNORECASE):
            continue

        for pattern in TOC_ENTRY_PATTERNS:
            m = pattern.match(line)
            if m:
                title = m.group(1).strip().rstrip('.…·')
                page_str = m.group(2)

                # Convert roman numerals
                if re.match(r'^[ivxlcdm]+$', page_str, re.IGNORECASE):
                    page = _roman_to_int(page_str)
                else:
                    page = int(page_str)

                if page > 0 and title:
                    # Deduplicate: same page number often appears in OCR errors
                    if page not in seen_pages:
                        entries.append({
                            "title": title,
                            "book_page": page,
                            "raw_line": line,
                        })
                        seen_pages.add(page)
                break

    return entries


def _roman_to_int(s: str) -> int:
    """Convert roman numeral string to integer."""
    roman = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
    s = s.lower()
    result = 0
    for i in range(len(s)):
        if i + 1 < len(s) and roman.get(s[i], 0) < roman.get(s[i + 1], 0):
            result -= roman.get(s[i], 0)
        else:
            result += roman.get(s[i], 0)
    return result


def find_toc_pages(doc: fitz.Document) -> list[int]:
    """Find which PDF pages contain the table of contents.

    Strategy:
    1. Check electronic TOC for "目录"/"目次"/"contents" entries
    2. Fallback: scan first 30 pages for TOC-like content
    """
    # Method 1: Electronic TOC
    outline = doc.get_toc()
    for level, title, page in outline:
        if any(kw in title for kw in ['目录', '目次', 'contents', 'CONTENTS']):
            # TOC starts at this page, estimate ~10 pages
            return list(range(page, min(page + 15, len(doc))))

    # Method 2: Heuristic scan of first 30 pages
    toc_start = None
    for i in range(min(30, len(doc))):
        text = doc[i].get_text()
        # TOC pages typically have many lines ending with numbers
        lines = text.strip().split('\n')
        numbered_lines = sum(1 for l in lines if re.search(r'\d+\s*$', l))
        if numbered_lines > 5 and numbered_lines / len(lines) > 0.3:
            if toc_start is None:
                toc_start = i
        elif toc_start is not None:
            # TOC ended
            return list(range(toc_start, i))

    if toc_start is not None:
        return list(range(toc_start, toc_start + 10))

    return []


# ──────────────────────────────────────────────────────────────
# Offset calculation
# ──────────────────────────────────────────────────────────────

def calculate_offset(
    electronic_toc: list[dict],
    ocr_entries: list[dict],
    total_pdf_pages: int,
) -> tuple[int | None, float]:
    """Calculate the offset between book page numbers and PDF page numbers.

    offset = pdf_page - book_page
    So: pdf_page = book_page + offset

    Uses multiple strategies and picks the most confident one.

    Returns (offset, confidence) or (None, 0.0) if unable to determine.
    """
    candidates: list[tuple[int, float]] = []

    # Strategy 1: Electronic TOC gives us direct PDF page numbers.
    # If we know "上册" is at PDF p33 and content starts at book_p1,
    # and the first real content is around PDF p38 (after preface pages),
    # then offset ≈ 37.
    if electronic_toc:
        # Find the last frontmatter entry and first content entry
        fm_pages = is_frontmatter(electronic_toc)
        content_entries = [e for e in electronic_toc if e["pdf_page"] not in fm_pages]
        if content_entries:
            first_content_pdf = content_entries[0]["pdf_page"]
            # Assume first content = book page 1 (or close to it)
            offset = first_content_pdf - 1
            candidates.append((offset, 0.7))

    # Strategy 2: Cross-reference electronic TOC with OCR entries
    # If electronic TOC says "伊本·白图泰小传" at PDF p37,
    # and OCR TOC says "伊本·白图泰小传" at book_p37,
    # then offset = 37 - 37 = 0... but that's suspicious.
    # Better: find entries where we can match titles.
    if electronic_toc and ocr_entries:
        matches = _match_toc_entries(electronic_toc, ocr_entries)
        if matches:
            offsets = [pdf_p - book_p for pdf_p, book_p in matches]
            # Use median offset
            offsets.sort()
            median_offset = offsets[len(offsets) // 2]
            # Confidence based on consistency
            consistent = sum(1 for o in offsets if abs(o - median_offset) <= 2)
            confidence = consistent / len(offsets) * 0.9
            candidates.append((median_offset, confidence))

    # Strategy 3: If we have OCR entries, find the first entry with book_page=1
    # or the smallest book page, and estimate its PDF page
    if ocr_entries and not candidates:
        min_book_page = min(e["book_page"] for e in ocr_entries)
        # First content page is usually after ~20-40 frontmatter pages
        # This is a rough heuristic
        estimated_pdf = 35 + min_book_page  # very rough
        candidates.append((estimated_pdf - min_book_page, 0.3))

    if not candidates:
        return None, 0.0

    # Pick highest confidence candidate
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0]


def _match_toc_entries(
    electronic: list[dict],
    ocr: list[dict],
) -> list[tuple[int, int]]:
    """Match electronic TOC entries with OCR entries by title similarity.

    Returns list of (pdf_page, book_page) pairs.
    """
    matches = []
    for e_entry in electronic:
        e_title = _normalize_title(e_entry["title"])
        for o_entry in ocr:
            o_title = _normalize_title(o_entry["title"])
            # Simple fuzzy match: check if significant substrings overlap
            if _titles_match(e_title, o_title):
                matches.append((e_entry["pdf_page"], o_entry["book_page"]))
                break
    return matches


def _normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove punctuation, whitespace, common OCR artifacts
    title = re.sub(r'[.…·，。、：；！？""''（）\[\]【】\s]+', '', title)
    title = title.strip()
    return title.lower()


def _titles_match(a: str, b: str, threshold: float = 0.6) -> bool:
    """Check if two normalized titles are similar enough."""
    if not a or not b:
        return False
    # Character overlap ratio
    common = set(a) & set(b)
    if not common:
        return False
    ratio = len(common) / max(len(set(a)), len(set(b)))
    return ratio >= threshold


# ──────────────────────────────────────────────────────────────
# Main mapper class
# ──────────────────────────────────────────────────────────────

class TOCPageMapper:
    """Extract TOC and map book page numbers to PDF page numbers."""

    def __init__(self, pdf_path: str, ocr_client=None):
        self.pdf_path = pdf_path
        self.ocr_client = ocr_client
        self.doc: fitz.Document | None = None
        self.result = TOCResult()

    async def load(self) -> TOCResult:
        """Load and process TOC. Main entry point."""
        self.doc = fitz.open(self.pdf_path)

        # Step 1: Try electronic TOC
        electronic = extract_electronic_toc(self.doc)
        if electronic:
            self.result.raw_electronic = electronic
            self.result.source = "electronic"
            # Convert to TOCEntry objects
            for entry in electronic:
                self.result.entries.append(TOCEntry(
                    title=entry["title"],
                    book_page=0,  # unknown until we compute offset
                    pdf_page=entry["pdf_page"],
                    level=entry["level"],
                    confidence=1.0,
                    source="electronic",
                ))

        # Step 2: Find and OCR TOC pages
        toc_pages = find_toc_pages(self.doc)
        self.result.toc_pdf_pages = toc_pages

        if toc_pages and self.ocr_client:
            ocr_entries = await self._ocr_toc_pages(toc_pages)
            if ocr_entries:
                # Merge OCR entries (fill in book_page for electronic entries,
                # or add new entries not in electronic TOC)
                self._merge_ocr_entries(ocr_entries)
                if self.result.source == "electronic":
                    self.result.source = "merged"
                else:
                    self.result.source = "ocr"

        # Step 3: Calculate offset
        ocr_raw = [
            {"title": e.title, "book_page": e.book_page}
            for e in self.result.entries if e.book_page > 0
        ]
        offset, confidence = calculate_offset(
            self.result.raw_electronic, ocr_raw, len(self.doc)
        )
        self.result.offset = offset
        self.result.offset_confidence = confidence

        # Step 4: Resolve all entries
        if offset is not None:
            for entry in self.result.entries:
                if entry.book_page > 0:
                    entry.pdf_page = entry.book_page + offset
                # For electronic entries with pdf_page but no book_page:
                elif entry.pdf_page is not None:
                    entry.book_page = entry.pdf_page - offset

        # Step 5: Determine content start
        fm = is_frontmatter(self.result.raw_electronic) if self.result.raw_electronic else set()
        if fm:
            self.result.content_start_pdf = max(fm) + 1
        elif offset is not None:
            self.result.content_start_pdf = offset + 1

        return self.result

    async def _ocr_toc_pages(self, toc_pages: list[int]) -> list[dict]:
        """OCR the TOC pages and parse entries."""
        if not self.ocr_client:
            return []

        all_text = []
        for page_num in toc_pages:
            page = self.doc[page_num]
            pix = page.get_pixmap(dpi=200)
            import base64
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()

            # Use a TOC-specific prompt
            text = await self.ocr_client.ocr_page(img_b64, prompt=(
                "这是一页书籍目录。请提取所有目录条目，保留标题和页码。\n"
                "格式：标题 + 页码（数字）\n"
                "每行一个条目，标题和页码之间保留原始的点线或空格。\n"
                "只输出目录内容，不要添加说明。"
            ))
            all_text.append(text)

        self.result.raw_ocr_text = "\n".join(all_text)
        return parse_toc_text(self.result.raw_ocr_text)

    def _merge_ocr_entries(self, ocr_entries: list[dict]):
        """Merge OCR-extracted entries into the result."""
        existing_titles = {_normalize_title(e.title) for e in self.result.entries}

        for ocr in ocr_entries:
            norm_title = _normalize_title(ocr["title"])
            # Check if this entry already exists (from electronic TOC)
            matched = False
            for entry in self.result.entries:
                if _titles_match(_normalize_title(entry.title), norm_title):
                    # Update book_page if not set
                    if entry.book_page == 0:
                        entry.book_page = ocr["book_page"]
                        entry.confidence = 0.8
                    matched = True
                    break

            if not matched:
                self.result.entries.append(TOCEntry(
                    title=ocr["title"],
                    book_page=ocr["book_page"],
                    pdf_page=None,  # will be resolved after offset calc
                    level=1,
                    confidence=0.7,
                    source="ocr",
                    raw_title=ocr.get("raw_line", ""),
                ))

    def book_to_pdf(self, book_page: int) -> int | None:
        """Convert book page number to PDF page number."""
        if self.result.offset is None:
            return None
        return book_page + self.result.offset

    def pdf_to_book(self, pdf_page: int) -> int | None:
        """Convert PDF page number to book page number."""
        if self.result.offset is None:
            return None
        return pdf_page - self.result.offset

    def get_content_pages(self) -> list[int]:
        """Get PDF page numbers for all content (excluding frontmatter)."""
        if not self.doc:
            return []
        start = self.result.content_start_pdf or 0
        return list(range(start, len(self.doc)))

    def get_chapter_pages(self) -> list[dict]:
        """Get chapter boundaries as {title, start_pdf, end_pdf}."""
        resolved = [e for e in self.result.entries if e.is_resolved]
        chapters = []
        for i, entry in enumerate(resolved):
            end_pdf = resolved[i + 1].pdf_page if i + 1 < len(resolved) else len(self.doc)
            chapters.append({
                "title": entry.title,
                "book_page": entry.book_page,
                "start_pdf": entry.pdf_page,
                "end_pdf": end_pdf,
                "source": entry.source,
            })
        return chapters

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
