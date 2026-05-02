"""Chapter/segment detection framework for historical texts.

Supports multiple detection strategies ranked by priority.
Each detector targets a specific structural pattern found in
historical travelogues, novels, and other literary genres.

Usage:
    chain = build_default_chain()
    chapters = chain.detect(text, strategy="auto")
    # or
    chapters = chain.detect(text, strategy="numbered_short_lines")
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────

@dataclass
class Chapter:
    """A detected chapter/segment."""
    title: str
    start_pos: int          # character offset in full text
    end_pos: int
    text: str
    level: int = 1          # 1=卷/部/Book, 2=章/Chapter, 3=节/Section
    metadata: dict = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)


# ──────────────────────────────────────────────────────────────
# Base detector
# ──────────────────────────────────────────────────────────────

class ChapterDetector(ABC):
    """Base class for chapter detection strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this detector."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Lower number = higher priority. Used for auto-ordering."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for interactive selection."""

    @property
    def genres(self) -> list[str]:
        """Genres this detector is designed for (e.g. 'travelogue', 'novel')."""
        return ["*"]

    @abstractmethod
    def detect(self, text: str) -> Optional[list[Chapter]]:
        """Return chapters if this detector can handle the text, else None."""


# ──────────────────────────────────────────────────────────────
# Detector chain
# ──────────────────────────────────────────────────────────────

class ManualSelectionNeeded(Exception):
    """Raised when strategy='manual' — caller should pick a detector."""
    def __init__(self, detectors: list[dict]):
        self.detectors = detectors


class ChapterDetectorChain:
    """Ordered chain of chapter detectors."""

    def __init__(self):
        self.detectors: list[ChapterDetector] = []

    def register(self, detector: ChapterDetector) -> "ChapterDetectorChain":
        self.detectors.append(detector)
        self.detectors.sort(key=lambda d: d.priority)
        return self

    def list_detectors(self) -> list[dict]:
        return [
            {
                "name": d.name,
                "priority": d.priority,
                "description": d.description,
                "genres": d.genres,
            }
            for d in self.detectors
        ]

    def detect(
        self,
        text: str,
        strategy: str = "auto",
        min_chapters: int = 2,
    ) -> list[Chapter]:
        """Run detection.

        Args:
            text: Full document text.
            strategy:
                "auto"     — try detectors by priority, return first match.
                "best"     — try all, return the one with most chapters.
                "<name>"   — use the named detector only.
                "manual"   — raise ManualSelectionNeeded with detector list.
            min_chapters: Minimum chapters to consider a valid split.
        """
        if strategy == "manual":
            raise ManualSelectionNeeded(self.list_detectors())

        if strategy == "best":
            best: list[Chapter] | None = None
            best_score = -999
            for d in self.detectors:
                result = d.detect(text)
                if result:
                    # Trim back-matter before scoring
                    trimmed = self._trim_backmatter(result)
                    score = self._score_split(trimmed)
                    if score > best_score:
                        best, best_score = trimmed, score
            return best or self._fallback(text)

        # auto or named
        for d in self.detectors:
            if strategy != "auto" and d.name != strategy:
                continue
            result = d.detect(text)
            if result and len(result) >= min_chapters:
                return result

        return self._fallback(text)

    def _fallback(self, text: str) -> list[Chapter]:
        """Return the whole text as a single chapter."""
        return [Chapter(title="(full text)", start_pos=0, end_pos=len(text), text=text)]

    @staticmethod
    def _trim_backmatter(chapters: list[Chapter]) -> list[Chapter]:
        """Remove trailing back-matter chapters (notes, bibliography, index).

        Detects chapters whose titles match common back-matter patterns
        and removes them plus all subsequent chapters.
        """
        backmatter_patterns = [
            r'(?i)^(NOTES?|INDEX|APPENDIX|BIBLIOGRAPHY|GLOSSARY|REFERENCES)',
            r'(?i)^(ABBREVIATIONS|FURTHER\s+READING|ACKNOWLEDGEMENTS?|WORKS\s+CITED)',
            r'(?i)^(EDITIONS|CRITICIAL|BOOKS\s+INSPIRED)',
        ]
        for i, ch in enumerate(chapters):
            for pat in backmatter_patterns:
                if re.match(pat, ch.title):
                    return chapters[:i] if i > 0 else chapters
        return chapters

    @staticmethod
    def _score_split(chapters: list[Chapter]) -> float:
        """Score a chapter split. Higher is better.

        Heuristic: prefer balanced chapter sizes. Penalizes very few (< 3) or
        extremely many (> 300) chapters, but is fairly tolerant of counts in
        the 5-200 range as long as chapters are balanced.
        """
        n = len(chapters)
        if n < 2:
            return -10

        # Count penalty: only penalize extremes
        if n < 3:
            count_penalty = -2
        elif n > 300:
            count_penalty = -(n - 300) * 0.01
        else:
            count_penalty = 0  # 3-300 is fine

        # Balance score: penalize if chapters vary wildly in size
        sizes = [c.char_count for c in chapters if c.char_count > 0]
        if not sizes:
            return -10
        avg = sum(sizes) / len(sizes)
        if avg == 0:
            return -10
        cv = (sum((s - avg) ** 2 for s in sizes) / len(sizes)) ** 0.5 / avg
        balance_score = -cv * 2  # lower coefficient of variation = better

        # Bonus: chapters that cover the full text (no large gaps)
        total_text = sum(sizes)
        span = chapters[-1].end_pos - chapters[0].start_pos + 1
        coverage = total_text / span if span > 0 else 0
        coverage_score = coverage * 2

        return count_penalty + balance_score + coverage_score


# ──────────────────────────────────────────────────────────────
# Detector 1: RTF structural headings (highest fidelity)
# ──────────────────────────────────────────────────────────────

class RTFHeadingDetector(ChapterDetector):
    """Extract chapter structure directly from RTF markup.

    Reads \\outlinelevel, \\sN heading styles, and bold paragraph markers
    BEFORE stripping RTF. This preserves heading hierarchy that striprtf loses.

    Use this via `detect_from_rtf(raw_rtf_text)` for RTF files,
    or it falls back to plain-text detection.
    """
    name = "rtf_headings"
    priority = 5
    description = "RTF结构化标题（直接解析RTF的outlinelevel/heading样式，最高保真度）"
    genres = ["*"]

    # RTF style definitions: \sN ... heading M;  → style_num → outline_level
    STYLE_RE = re.compile(
        r'\\s(\d+).*?outlinelevel(\d+).*?heading\s+\d+',
        re.IGNORECASE | re.DOTALL,
    )
    # Paragraph with outlinelevel in body
    OUTLINE_RE = re.compile(r'\\outlinelevel(\d+)')
    # Bold marker
    BOLD_RE = re.compile(r'\\b\b')
    # Paragraph end
    PAR_RE = re.compile(r'\\par\b')

    def detect(self, text: str) -> Optional[list[Chapter]]:
        # This detector needs raw RTF, not plain text.
        # Use detect_from_rtf() directly for RTF files.
        # For plain text, fall through to other detectors.
        return None

    def detect_from_rtf(self, raw_rtf: str) -> Optional[list[Chapter]]:
        """Parse RTF directly to extract chapter structure."""
        # Step 1: build style map from stylesheet
        style_map: dict[int, int] = {}  # style_num → outline_level
        stylesheet_match = re.search(
            r'\{\\stylesheet(.*?)\}', raw_rtf, re.DOTALL
        )
        if stylesheet_match:
            for m in self.STYLE_RE.finditer(stylesheet_match.group(1)):
                style_num, outline_level = int(m.group(1)), int(m.group(2))
                style_map[style_num] = outline_level

        # Step 2: find heading paragraphs in document body
        # Split by \par to get paragraphs
        body_start = raw_rtf.find('\\pard')
        if body_start == -1:
            body_start = 0

        headings: list[dict] = []
        # Walk through looking for outline markers
        pos = body_start
        current_text_parts: list[str] = []
        current_outline: int | None = None

        for m in re.finditer(r'\\(par|outlinelevel|s\d+|b\b)', raw_rtf[body_start:]):
            cmd = m.group(1)
            abs_pos = body_start + m.start()

            if cmd.startswith('outlinelevel'):
                level_m = re.match(r'outlinelevel(\d+)', cmd)
                if level_m:
                    current_outline = int(level_m.group(1))

            elif cmd.startswith('s') and not cmd.startswith('snext'):
                # Style reference — check if it maps to a heading
                style_m = re.match(r's(\d+)', cmd)
                if style_m:
                    sn = int(style_m.group(1))
                    if sn in style_map:
                        current_outline = style_map[sn]

            elif cmd == 'par':
                # End of paragraph — extract text between last \par and here
                para_text = self._extract_para_text(raw_rtf[pos:abs_pos])
                if para_text and current_outline is not None:
                    headings.append({
                        "level": current_outline,
                        "title": para_text.strip(),
                        "pos": abs_pos,
                    })
                pos = abs_pos
                current_outline = None

        if len(headings) < 2:
            return None

        # Step 3: convert positions to plain-text character offsets
        # We need to map RTF positions → stripped text positions
        return self._build_chapters_from_rtf_headings(raw_rtf, headings)

    def _extract_para_text(self, rtf_fragment: str) -> str:
        """Extract visible text from an RTF paragraph fragment."""
        # Remove RTF commands, keep text
        text = re.sub(r'\\[a-z]+\d*\s?', '', rtf_fragment)
        text = re.sub(r'[{}]', '', text)
        # Decode unicode escapes: \u12345?
        text = re.sub(
            r'\\u(\d+)\?',
            lambda m: chr(int(m.group(1))),
            text,
        )
        text = re.sub(r'\\[~_{}]', '', text)
        return text.strip()

    def _build_chapters_from_rtf_headings(
        self, raw_rtf: str, headings: list[dict]
    ) -> list[Chapter]:
        """Build Chapter list from RTF heading positions."""
        # Simple approach: extract text between heading positions
        chapters = []
        for i, h in enumerate(headings):
            start = h["pos"]
            end = headings[i + 1]["pos"] if i + 1 < len(headings) else len(raw_rtf)
            segment_rtf = raw_rtf[start:end]
            segment_text = self._extract_para_text(segment_rtf)
            chapters.append(Chapter(
                title=h["title"],
                start_pos=start,
                end_pos=end,
                text=segment_text,
                level=h["level"] + 1,  # RTF levels are 0-based
                metadata={"source": "rtf_structure", "outline_level": h["level"]},
            ))
        return chapters


# ──────────────────────────────────────────────────────────────
# Detector 2: Numbered short lines (游记/小说通用)
# ──────────────────────────────────────────────────────────────

class NumberedShortLineDetector(ChapterDetector):
    """Detect chapters marked as short standalone lines with number prefixes.

    Matches patterns like:
        001 波罗弟兄二人自君士坦丁堡往游世界
        1 The Middle East
        Chapter 1: The Beginning
        第一章 出发
        一、总论

    Handles TOC vs body by detecting clustered (TOC) vs spread (body) headings.
    """
    name = "numbered_short_lines"
    priority = 15
    description = "数字编号短行（001 标题 / 1 标题 / 第一章 / 一、等编号格式）"
    genres = ["travelogue", "novel", "essay", "*"]

    # Combined pattern for various numbering styles
    PATTERNS = [
        # Three-digit padded: 001 标题
        (r'^(\d{3})\s+(.+)$', "padded_number"),
        # Simple number + title: 1 The Middle East
        (r'^(\d{1,3})\s+([A-Z\u4e00-\u9fff].{2,})$', "simple_number"),
        # Chapter N / 第N章
        (r'^(Chapter\s+\d+|第[一二三四五六七八九十百千\d]+[卷章节回篇部])\s*[：:.\s]*(.*)$', "chapter_label"),
        # 一、 / 二、 (Chinese ordinal)
        (r'^([一二三四五六七八九十]+)[、.]\s*(.+)$', "chinese_ordinal"),
        # (1) / （一）
        (r'^[（(]([一二三四五六七八九十\d]+)[）)]\s*(.+)$', "paren_number"),
    ]

    def __init__(self, max_heading_length: int = 80, min_heading_gap: int = 500):
        self.max_heading_length = max_heading_length
        self.min_heading_gap = min_heading_gap  # min chars between headings

    def detect(self, text: str) -> Optional[list[Chapter]]:
        lines = text.split('\n')
        matches: list[tuple[int, int, str, str]] = []  # (line_idx, char_pos, title, style)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or len(stripped) > self.max_heading_length:
                continue
            for pattern, style in self.PATTERNS:
                m = re.match(pattern, stripped)
                if m:
                    title = stripped
                    char_pos = sum(len(lines[j]) + 1 for j in range(i))
                    matches.append((i, char_pos, title, style))
                    break

        if len(matches) < 2:
            return None

        # TOC detection: if the first numbered entry (e.g. 001) appears again
        # later, the first occurrence is TOC and the second is body start.
        # For non-numbered patterns, fall back to clustering heuristic.
        first_num = self._extract_number(matches[0][2], matches[0][3])
        if first_num is not None:
            # Find where the numbering resets (first number reappears)
            body_start_idx = None
            for j in range(1, len(matches)):
                num = self._extract_number(matches[j][2], matches[j][3])
                if num is not None and num <= first_num:
                    body_start_idx = j
                    break
            if body_start_idx is not None and body_start_idx > 1:
                matches = matches[body_start_idx:]

        elif len(matches) >= 4:
            # Non-numbered: use clustering (all in first 15% = TOC)
            toc_threshold = len(text) * 0.15
            if matches[-1][1] < toc_threshold:
                body_matches = self._find_body_headings(text, lines)
                if len(body_matches) >= 2:
                    matches = body_matches

        if len(matches) < 2:
            return None

        # For consecutive numbered entries, don't filter by gap — keep all.
        # For non-numbered patterns, apply gap filter.
        is_numbered = first_num is not None
        if is_numbered:
            filtered = matches  # keep all numbered entries
        else:
            filtered = [matches[0]]
            for m in matches[1:]:
                if m[1] - filtered[-1][1] >= self.min_heading_gap:
                    filtered.append(m)

        if len(filtered) < 2:
            return None

        # Build chapters
        chapters = []
        for i, (line_idx, char_pos, title, style) in enumerate(filtered):
            if i + 1 < len(filtered):
                end_pos = filtered[i + 1][1]
            else:
                end_pos = len(text)

            chapter_text = text[char_pos:end_pos].strip()
            # Remove the heading line from the body text
            first_newline = chapter_text.find('\n')
            if first_newline > 0:
                chapter_text = chapter_text[first_newline:].strip()

            level = self._infer_level(style, title)
            chapters.append(Chapter(
                title=title,
                start_pos=char_pos,
                end_pos=end_pos,
                text=chapter_text,
                level=level,
                metadata={"style": style, "line_number": line_idx},
            ))

        return chapters

    @staticmethod
    def _extract_number(title: str, style: str) -> Optional[int]:
        """Extract the numeric identifier from a matched heading, if any."""
        if style == "padded_number":
            m = re.match(r'^(\d{3})', title)
            return int(m.group(1)) if m else None
        if style == "simple_number":
            m = re.match(r'^(\d{1,3})', title)
            return int(m.group(1)) if m else None
        return None

    def _find_body_headings(
        self, text: str, lines: list[str]
    ) -> list[tuple[int, int, str, str]]:
        """Re-scan text after TOC threshold for body chapter headings."""
        # Skip the first 15% of text
        skip_pos = int(len(text) * 0.15)
        remaining = text[skip_pos:]

        matches = []
        for i, line in enumerate(remaining.split('\n')):
            stripped = line.strip()
            if not stripped or len(stripped) > self.max_heading_length:
                continue
            for pattern, style in self.PATTERNS:
                m = re.match(pattern, stripped)
                if m:
                    char_pos = skip_pos + sum(
                        len(l) + 1 for l in remaining.split('\n')[:i]
                    )
                    matches.append((i, char_pos, stripped, style))
                    break
        return matches

    def _infer_level(self, style: str, title: str) -> int:
        if style == "chapter_label":
            if re.search(r'第[一二三四五六七八九十百千]+[卷部]|Book\s+\d+', title, re.IGNORECASE):
                return 1
            if re.search(r'第[一二三四五六七八九十百千]+[章回]|Chapter\s+\d+', title, re.IGNORECASE):
                return 2
        if style == "padded_number":
            return 3  # fine-grained sections
        return 2


# ──────────────────────────────────────────────────────────────
# Detector 3: ALL-CAPS standalone headings (e.g. ONE, TWO, PROLOGUE)
# ──────────────────────────────────────────────────────────────

class AllCapsHeadingDetector(ChapterDetector):
    """Detect chapters marked by ALL-CAPS standalone words.

    Common in English editions: ONE, TWO, THREE, PROLOGUE, EPILOGUE.
    Often followed by a subtitle on the next line:
        ONE
        The Middle East
    """
    name = "allcaps_headings"
    priority = 12
    description = "ALL-CAPS独立标题行（ONE / TWO / PROLOGUE 等大写单词，常见于英文版）"
    genres = ["travelogue", "novel"]

    # Match ALL-CAPS words (2+ chars, no lowercase)
    HEADING_RE = re.compile(
        r'^\s*([A-Z]{2,}(?:\s+[A-Z]{2,})*)\s*$'
    )

    def __init__(self, min_gap: int = 1000):
        self.min_gap = min_gap

    def detect(self, text: str) -> Optional[list[Chapter]]:
        lines = text.split('\n')
        matches: list[tuple[int, int, str, str]] = []  # (line_idx, char_pos, label, subtitle)

        for i, line in enumerate(lines):
            m = self.HEADING_RE.match(line)
            if not m:
                continue

            label = m.group(1).strip()
            # Skip common non-heading caps words
            skip_words = {
                'THE', 'AND', 'FOR', 'NOT', 'BUT', 'NOR', 'YET', 'SO',
                'FROM', 'WITH', 'THAT', 'THIS', 'HAVE', 'WILL', 'BEEN',
                'EACH', 'WHEN', 'WHERE', 'WHAT', 'WHO', 'HOW',
                'CONTENTS', 'NOTES', 'INDEX', 'APPENDIX', 'BIBLIOGRAPHY',
                'ACKNOWLEDGEMENTS', 'ACKNOWLEDGMENTS', 'FURTHER', 'READING',
                'ABBREVIATIONS', 'MAPS', 'CHRONOLOGY', 'INTRODUCTION',
                'FOLLOW', 'PENGUIN', 'CLASSICS',
            }
            # Also skip multi-word common phrases (exact word prefix, not partial)
            if any(label == w or label.startswith(w + ' ') for w in skip_words):
                continue
            if len(label) > 40:
                continue

            # Look for subtitle on next non-blank line
            subtitle = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                s = lines[j].strip()
                if s and not self.HEADING_RE.match(lines[j]):
                    subtitle = s
                    break

            title = f"{label} {subtitle}".strip() if subtitle else label
            char_pos = sum(len(lines[k]) + 1 for k in range(i))
            matches.append((i, char_pos, title, label))

        if len(matches) < 2:
            return None

        # Filter by gap
        filtered = [matches[0]]
        for m in matches[1:]:
            if m[1] - filtered[-1][1] >= self.min_gap:
                filtered.append(m)

        if len(filtered) < 2:
            return None

        chapters = []
        for i, (line_idx, char_pos, title, label) in enumerate(filtered):
            end_pos = filtered[i + 1][1] if i + 1 < len(filtered) else len(text)
            chapter_text = text[char_pos:end_pos].strip()
            # Remove heading lines from body
            body_lines = chapter_text.split('\n')
            skip = 0
            for bl in body_lines[:3]:
                if bl.strip() == label or not bl.strip():
                    skip += len(bl) + 1
                else:
                    break
            chapter_text = chapter_text[skip:].strip()

            chapters.append(Chapter(
                title=title,
                start_pos=char_pos,
                end_pos=end_pos,
                text=chapter_text,
                level=1,  # These are typically top-level divisions
                metadata={"style": "allcaps", "label": label},
            ))

        return chapters


# ──────────────────────────────────────────────────────────────
# Detector 4: Multi-line blank separation
# ──────────────────────────────────────────────────────────────

class BlankLineDetector(ChapterDetector):
    """Split by multiple consecutive blank lines."""
    name = "blank_lines"
    priority = 80
    description = "多空行分割（适用于无明确章节标记的文本）"
    genres = ["*"]

    def __init__(self, min_blanks: int = 3, min_chapter_chars: int = 200):
        self.min_blanks = min_blanks
        self.min_chapter_chars = min_chapter_chars

    def detect(self, text: str) -> Optional[list[Chapter]]:
        # Match 3+ consecutive blank lines
        pattern = r'(?:\n\s*){' + str(self.min_blanks) + r',}\n?'
        parts = re.split(pattern, text)

        # Filter out tiny fragments
        parts = [p for p in parts if len(p.strip()) >= self.min_chapter_chars]
        if len(parts) < 2:
            return None

        chapters = []
        offset = 0
        for part in parts:
            start = text.find(part, offset)
            if start == -1:
                start = offset
            # Generate a title from the first meaningful line
            first_line = part.strip().split('\n')[0].strip()
            title = first_line[:60] + ("..." if len(first_line) > 60 else "")
            chapters.append(Chapter(
                title=title,
                start_pos=start,
                end_pos=start + len(part),
                text=part.strip(),
                level=2,
            ))
            offset = start + len(part)

        return chapters


# ──────────────────────────────────────────────────────────────
# Detector 4: Travelogue / diary date markers
# ──────────────────────────────────────────────────────────────

class TravelogueDetector(ChapterDetector):
    """Detect segments by date markers in travel diaries.

    Works for Chinese dynasty dates (光绪十年三月初一)
    and Western dates (1271, January 1295, etc.).
    """
    name = "travelogue_dates"
    priority = 35
    description = "游记/日记专用：按年号日期或公历日期分段（光绪X年 / 1271年等）"
    genres = ["travelogue", "diary"]

    PATTERNS = [
        # Chinese dynasty year: 光绪十年
        re.compile(
            r'(光绪|宣统|咸丰|同治|道光|嘉庆|乾隆|雍正|康熙|'
            r'嘉靖|万历|崇祯|弘治|正德|永乐|洪武|景泰|天顺|成化)\s*'
            r'([一二三四五六七八九十]+)\s*年'
        ),
        # Chinese date: 三月初一
        re.compile(r'([一二三四五六七八九十]+)\s*月\s*([一二三四五六七八九十]+)\s*[日号]'),
        # Western year in text: "in 1271" / "1295年"
        re.compile(r'(?:^|\s)((?:1[2-4])\d{2})\s*[年\s]'),
    ]

    def __init__(self, max_gap: int = 5000, min_segments: int = 3):
        self.max_gap = max_gap  # max chars between date markers to merge
        self.min_segments = min_segments

    def detect(self, text: str) -> Optional[list[Chapter]]:
        date_positions: list[tuple[int, str]] = []

        for pattern in self.PATTERNS:
            for m in pattern.finditer(text):
                date_positions.append((m.start(), m.group(0).strip()))

        if len(date_positions) < self.min_segments:
            return None

        # Deduplicate overlapping matches
        date_positions.sort(key=lambda x: x[0])
        deduped = [date_positions[0]]
        for pos, label in date_positions[1:]:
            if pos - deduped[-1][0] > 50:  # not overlapping
                deduped.append((pos, label))

        if len(deduped) < self.min_segments:
            return None

        # Group by proximity
        segments: list[tuple[int, int, str]] = []
        seg_start = 0
        seg_label = deduped[0][1]

        for i in range(1, len(deduped)):
            if deduped[i][0] - deduped[i - 1][0] > self.max_gap:
                segments.append((deduped[seg_start][0], deduped[i][0], seg_label))
                seg_start = i
                seg_label = deduped[i][1]

        segments.append((deduped[seg_start][0], len(text), seg_label))

        if len(segments) < 2:
            return None

        return [
            Chapter(
                title=label,
                start_pos=start,
                end_pos=end,
                text=text[start:end].strip(),
                level=2,
                metadata={"type": "travelogue_segment"},
            )
            for start, end, label in segments
        ]


# ──────────────────────────────────────────────────────────────
# Detector 5: Short standalone lines (any language)
# ──────────────────────────────────────────────────────────────

class ShortStandaloneLineDetector(ChapterDetector):
    """Detect headings as short lines surrounded by blank lines.

    More relaxed than NumberedShortLine — doesn't require number prefix.
    Works for both CJK and Latin text.
    """
    name = "short_standalone_lines"
    priority = 45
    description = "独立短行标题（空白行包围的短行，不要求数字编号）"
    genres = ["*"]

    def __init__(self, max_length: int = 60, min_chapter_chars: int = 100):
        self.max_length = max_length
        self.min_chapter_chars = min_chapter_chars

    def detect(self, text: str) -> Optional[list[Chapter]]:
        lines = text.split('\n')
        candidates: list[tuple[int, int, str]] = []  # (line_idx, char_pos, title)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or len(stripped) > self.max_length:
                continue

            # Must be a standalone line (blank line before and after)
            prev_blank = (i == 0 or not lines[i - 1].strip())
            next_blank = (i == len(lines) - 1 or not lines[i + 1].strip())

            if prev_blank and next_blank:
                char_pos = sum(len(lines[j]) + 1 for j in range(i))
                candidates.append((i, char_pos, stripped))

        if len(candidates) < 2:
            return None

        # Filter: must have substantial text between candidates
        filtered = [candidates[0]]
        for c in candidates[1:]:
            if c[1] - filtered[-1][1] >= self.min_chapter_chars:
                filtered.append(c)

        if len(filtered) < 2:
            return None

        chapters = []
        for i, (line_idx, char_pos, title) in enumerate(filtered):
            end_pos = filtered[i + 1][1] if i + 1 < len(filtered) else len(text)
            chapter_text = text[char_pos:end_pos].strip()
            # Remove heading line from body
            first_nl = chapter_text.find('\n')
            if first_nl > 0:
                chapter_text = chapter_text[first_nl:].strip()

            chapters.append(Chapter(
                title=title,
                start_pos=char_pos,
                end_pos=end_pos,
                text=chapter_text,
                level=2,
            ))

        return chapters


# ──────────────────────────────────────────────────────────────
# Detector 6: LLM-assisted (fallback)
# ──────────────────────────────────────────────────────────────

class LLMDetector(ChapterDetector):
    """Use an LLM to identify chapter boundaries. Slowest, most flexible."""
    name = "llm_smart"
    priority = 999
    description = "LLM智能识别（最慢但最灵活，适用于格式不规则的文本）"
    genres = ["*"]

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def detect(self, text: str) -> Optional[list[Chapter]]:
        if self.llm is None:
            return None
        # This is an async-capable detector; for sync use, return None
        # Call detect_async() instead
        return None

    async def detect_async(self, text: str) -> Optional[list[Chapter]]:
        """Async version for use with LLM client."""
        if self.llm is None:
            return None

        # Sample first 10k chars for structure analysis
        sample = text[:10000]
        prompt = f"""Analyze the structure of this text and identify chapter/section boundaries.

For each section, provide:
1. The heading or first 30 characters of the section
2. Approximate character position in the text

Return JSON:
{{"sections": [{{"title": "...", "position": 0}}, ...]}}

TEXT:
{sample}"""

        try:
            result = await self.llm.extract_json(prompt)
            import json
            data = json.loads(result)
            sections = data.get("sections", [])
            if len(sections) < 2:
                return None

            chapters = []
            for i, sec in enumerate(sections):
                start = sec["position"]
                end = sections[i + 1]["position"] if i + 1 < len(sections) else len(text)
                chapters.append(Chapter(
                    title=sec["title"],
                    start_pos=start,
                    end_pos=end,
                    text=text[start:end].strip(),
                    level=2,
                    metadata={"source": "llm"},
                ))
            return chapters
        except Exception:
            return None


# ──────────────────────────────────────────────────────────────
# Convenience: build default chain
# ──────────────────────────────────────────────────────────────

def build_default_chain(llm_client=None) -> ChapterDetectorChain:
    """Build a detector chain with all built-in detectors."""
    chain = ChapterDetectorChain()
    chain.register(RTFHeadingDetector())
    chain.register(AllCapsHeadingDetector())
    chain.register(NumberedShortLineDetector())
    chain.register(ShortStandaloneLineDetector())
    chain.register(TravelogueDetector())
    chain.register(BlankLineDetector())
    if llm_client:
        chain.register(LLMDetector(llm_client))
    return chain
