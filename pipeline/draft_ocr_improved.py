"""Improved OCR client for historical travel journals.

Draft — not yet integrated into the pipeline. Intended to replace/supplement
pipeline/core/ocr.py with:

1. Book-aware prompts (language, genre, dynasty context)
2. Cross-page context passing (prev_page_tail for continuity)
3. Multi-language prompt templates (zh-classical, arabic, en)
4. OCR quality validation with automatic retry
5. Structured output with location hints for downstream extraction

Usage:
    client = ImprovedOCRClient(config)
    pages = await client.ocr_pdf(pdf_path, book_context={
        "title": "伊本·白图泰游记",
        "author": "伊本·白图泰",
        "language": "zh-classical",
        "genre": "travelogue",
        "dynasty": None,
        "era": None,
    })
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import fitz  # PyMuPDF
from openai import AsyncOpenAI


# ──────────────────────────────────────────────────────────────
# Book context model
# ──────────────────────────────────────────────────────────────

class BookContext:
    """Metadata about the book being OCR'd. Injected into every prompt."""

    def __init__(
        self,
        title: str = "",
        author: str = "",
        language: str = "zh-classical",
        genre: str = "travelogue",
        dynasty: str | None = None,
        era: str | None = None,
        expected_patterns: list[str] | None = None,
    ):
        self.title = title
        self.author = author
        self.language = language
        self.genre = genre
        self.dynasty = dynasty
        self.era = era
        self.expected_patterns = expected_patterns or self._default_patterns()

    def _default_patterns(self) -> list[str]:
        if self.language.startswith("zh"):
            return [
                "日期: X年X月X日 / X月X日",
                "地名: XX城/州/国/府/县/山/河",
                "人名: 两到四字人名",
                "编号: 001、002... 或 第X章/回",
            ]
        if self.language == "arabic":
            return [
                "Date: Hijri calendar (X年/X月/X日)",
                "Place: XX city/region/river",
                "Names: proper nouns in Arabic script",
            ]
        return [
            "Date: year references (1271, January 1295, etc.)",
            "Place: city/region/river names",
            "Chapter: numbered sections or headings",
        ]

    def to_prompt_context(self) -> str:
        """Format as context block for prompt injection."""
        parts = []
        if self.title:
            parts.append(f"标题：{self.title}")
        if self.author:
            parts.append(f"作者：{self.author}")
        if self.dynasty:
            parts.append(f"朝代：{self.dynasty}")
        if self.era:
            parts.append(f"年号：{self.era}")
        parts.append(f"语言：{self.language_label}")
        parts.append(f"文体：{self.genre_label}")
        parts.append("预期内容格式：")
        for p in self.expected_patterns:
            parts.append(f"  - {p}")
        return "\n".join(parts)

    @property
    def language_label(self) -> str:
        labels = {
            "zh-classical": "古汉语（文言文）",
            "zh-modern": "现代汉语",
            "arabic": "阿拉伯文",
            "en": "英文",
        }
        return labels.get(self.language, self.language)

    @property
    def genre_label(self) -> str:
        labels = {
            "travelogue": "游记/纪行",
            "diary": "日记",
            "novel": "小说",
            "essay": "散文/随笔",
        }
        return labels.get(self.genre, self.genre)


# ──────────────────────────────────────────────────────────────
# Language-specific prompt fragments
# ──────────────────────────────────────────────────────────────

LANGUAGE_RULES: dict[str, dict] = {
    "zh-classical": {
        "instruction": "这是古汉语（文言文）文本，可能包含竖排或横排。",
        "rules": [
            "保留所有异体字、繁体字，不要转换为简体",
            "人名、地名、朝代名保持原样，不要翻译",
            "如有注释/批注（旁注、夹注），用【注】标记，与正文区分",
            "如遇OCR不确定的字，用[?]标记，不要猜测",
        ],
    },
    "zh-modern": {
        "instruction": "这是现代汉语排版的文本。",
        "rules": [
            "保留原始段落结构和换行",
            "如遇OCR不确定的字，用[?]标记",
        ],
    },
    "arabic": {
        "instruction": "This is classical Arabic text (right-to-left).",
        "rules": [
            "Read right-to-left",
            "Preserve diacritical marks (tashkeel) if present in the image",
            "Keep Arabic numerals as-is",
            "Place names: preserve original transliteration, do not translate",
            "If text is unclear, mark with [?] — do not guess",
        ],
    },
    "en": {
        "instruction": "This is a historical English text.",
        "rules": [
            "Preserve original spelling (may differ from modern English)",
            "Keep footnote markers as [FN:N]",
            "Chapter/section headings should be on separate lines",
            "If text is unclear, mark with [?] — do not guess",
        ],
    },
}


# ──────────────────────────────────────────────────────────────
# OCR quality checks
# ──────────────────────────────────────────────────────────────

class OCRQualityIssue:
    def __init__(self, issue: str, severity: str = "warn"):
        self.issue = issue
        self.severity = severity  # "warn" or "error"

    def __repr__(self):
        return f"[{self.severity}] {self.issue}"


def validate_ocr_result(text: str, language: str) -> list[OCRQualityIssue]:
    """Check OCR output for common quality issues."""
    issues: list[OCRQualityIssue] = []

    # 1. Too short
    if len(text.strip()) < 30:
        issues.append(OCRQualityIssue("OCR结果过短，可能漏读", "error"))

    # 2. Language character ratio
    if language.startswith("zh"):
        total = len(text.replace(" ", "").replace("\n", ""))
        if total > 0:
            cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            ratio = cjk / total
            if ratio < 0.2:
                issues.append(OCRQualityIssue(
                    f"中文字符比例过低({ratio:.0%})，可能是扫描质量差或语言判断错误",
                    "warn"
                ))

    # 3. Repeated characters (OCR noise)
    if re.search(r'(.)\1{8,}', text):
        issues.append(OCRQualityIssue("检测到连续重复字符(>8次)，可能是OCR噪声", "warn"))

    # 4. Excessive [?] marks
    question_marks = text.count('[?]')
    if question_marks > 10:
        issues.append(OCRQualityIssue(
            f"不确定标记[?]出现{question_marks}次，OCR质量可能较差",
            "warn"
        ))

    # 5. Garbled text detection (mix of random encodings)
    if language.startswith("zh"):
        # Check for mojibake patterns
        mojibake = re.findall(r'[ÃÂ¶¼½¾]{3,}', text)
        if mojibake:
            issues.append(OCRQualityIssue("检测到可能的编码乱码", "error"))

    return issues


# ──────────────────────────────────────────────────────────────
# Main OCR client
# ──────────────────────────────────────────────────────────────

class ImprovedOCRClient:
    """OCR via OpenAI-compatible vision API with context-aware prompts."""

    def __init__(self, config: dict):
        ocr_cfg = config["ocr"]
        self.client = AsyncOpenAI(
            base_url=ocr_cfg["base_url"],
            api_key=ocr_cfg["api_key"],
        )
        self.model = ocr_cfg["model"]
        self.dpi = ocr_cfg.get("dpi", 200)
        self.max_tokens = ocr_cfg.get("max_tokens", 4096)
        self.retry_on_low_quality = ocr_cfg.get("retry_on_low_quality", True)

    # ── Prompt construction ──────────────────────────────────

    def _build_ocr_prompt(
        self,
        book_ctx: BookContext,
        prev_page_tail: str = "",
        page_num: int = 0,
        warnings: list[str] | None = None,
    ) -> str:
        """Build a context-aware OCR prompt."""
        lang_rules = LANGUAGE_RULES.get(book_ctx.language, LANGUAGE_RULES["en"])

        lines = [
            f"你正在OCR一部历史文献的第{page_num}页。" if page_num else "你正在OCR一部历史文献。",
            "",
            "## 书籍信息",
            book_ctx.to_prompt_context(),
            "",
            f"## 语言特征",
            lang_rules["instruction"],
            "",
            "## OCR规则",
        ]
        for rule in lang_rules["rules"]:
            lines.append(f"- {rule}")

        lines.extend([
            "",
            "## 通用规则",
            "- 严格保留原文的段落结构和换行",
            "- 章节标题/编号条目单独成行",
            "- 不要翻译或解释，只输出原文",
            "- 不要添加任何前缀说明（如'以下是OCR结果'）",
        ])

        if prev_page_tail:
            lines.extend([
                "",
                "## 上一页末尾（用于判断段落是否跨页续接）",
                f"```",
                prev_page_tail[-300:],
                f"```",
            ])

        if warnings:
            lines.extend([
                "",
                "## 质量警告（请特别注意）",
            ])
            for w in warnings:
                lines.append(f"- ⚠️ {w}")

        return "\n".join(lines)

    def _build_structured_prompt(
        self,
        book_ctx: BookContext,
        prev_page_tail: str = "",
        page_num: int = 0,
    ) -> str:
        """Build prompt for structured OCR (text + story boundaries)."""
        lang_rules = LANGUAGE_RULES.get(book_ctx.language, LANGUAGE_RULES["en"])

        return f"""你正在处理一部历史游记的页面图片。

## 书籍信息
{book_ctx.to_prompt_context()}

## 语言特征
{lang_rules["instruction"]}

## 任务
1. OCR提取页面全部文字
2. 识别本页包含的独立叙事段落（story）

## 识别规则
- 每个独立的地理位置描述 = 一个story
- 每个独立的事件/故事 = 一个story
- 编号条目（如"001 波斯大州"）= 独立story
- 章节标题（如"第一章"）= 独立story的开始
- 跨页段落：设置 continues_from_prev / continues_to_next
- 标题行不计入正文text，单独放入title字段

## 上一页末尾
```
{prev_page_tail[-300:] if prev_page_tail else "(第一页)"}
```

## 输出格式
```json
{{
  "text": "页面完整OCR文字",
  "page_number": {page_num},
  "stories": [
    {{
      "title": "条目标题或章节名，无标题则为空字符串",
      "text": "该段落的文字",
      "entry_number": "如有编号则填入，如001",
      "continues_from_prev": false,
      "continues_to_next": false,
      "location_hints": ["本段提到的地名"]
    }}
  ]
}}
```

{chr(10).join("- " + r for r in lang_rules["rules"])}

返回纯JSON，不要包含markdown代码块标记。"""

    # ── API calls ────────────────────────────────────────────

    async def ocr_page(
        self,
        img_b64: str,
        book_ctx: BookContext,
        prev_page_tail: str = "",
        page_num: int = 0,
    ) -> str:
        """OCR a single page with context-aware prompt. Returns plain text."""
        prompt = self._build_ocr_prompt(book_ctx, prev_page_tail, page_num)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    async def ocr_page_structured(
        self,
        img_b64: str,
        book_ctx: BookContext,
        prev_page_tail: str = "",
        page_num: int = 0,
    ) -> dict:
        """OCR a single page with structured story boundary detection."""
        prompt = self._build_structured_prompt(book_ctx, prev_page_tail, page_num)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"text": raw, "stories": []}

    # ── PDF processing with context ──────────────────────────

    async def ocr_pdf(
        self,
        pdf_path: str,
        book_ctx: BookContext,
    ) -> list[dict]:
        """OCR entire PDF with cross-page context and quality validation.

        Returns list of page results, each with:
            - "text": str
            - "page_number": int
            - "quality_issues": list[str]
            - "retry": bool (True if page was re-OCR'd)
        """
        doc = fitz.open(pdf_path)
        pages: list[dict] = []
        prev_tail = ""

        for i, page in enumerate(doc):
            page_num = i + 1
            pix = page.get_pixmap(dpi=self.dpi)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()

            # First attempt
            result = await self.ocr_page_structured(
                img_b64, book_ctx, prev_tail, page_num
            )
            result["page_number"] = page_num

            # Quality validation
            text = result.get("text", "")
            issues = validate_ocr_result(text, book_ctx.language)
            result["quality_issues"] = [str(iss) for iss in issues]
            result["retry"] = False

            # Retry on error-level issues
            if self.retry_on_low_quality and any(iss.severity == "error" for iss in issues):
                warnings = [iss.issue for iss in issues]
                retry_prompt = self._build_ocr_prompt(
                    book_ctx, prev_tail, page_num, warnings
                )
                # Retry with plain text OCR (more focused)
                retry_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": retry_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        ],
                    }],
                    max_tokens=self.max_tokens,
                )
                retry_text = retry_response.choices[0].message.content or ""
                if len(retry_text) > len(text):
                    result["text"] = retry_text
                    result["retry"] = True
                    result["quality_issues"].append("已重试，结果已更新")

            pages.append(result)

            # Update cross-page context
            full_text = result.get("text", "")
            prev_tail = full_text[-300:] if len(full_text) > 300 else full_text

        doc.close()
        return pages

    # ── Convenience: simple text-only OCR ─────────────────────

    async def ocr_pdf_simple(
        self,
        pdf_path: str,
        book_ctx: BookContext,
    ) -> str:
        """OCR entire PDF, return concatenated plain text (no structured output)."""
        doc = fitz.open(pdf_path)
        texts: list[str] = []
        prev_tail = ""

        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=self.dpi)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            text = await self.ocr_page(img_b64, book_ctx, prev_tail, i + 1)
            texts.append(text)
            prev_tail = text[-300:] if len(text) > 300 else text

        doc.close()
        return "\n\n".join(texts)
