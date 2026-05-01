from __future__ import annotations

import base64
from pathlib import Path

import fitz  # PyMuPDF
from openai import AsyncOpenAI


class OCRClient:
    """OCR via OpenAI-compatible vision API. Config lives under `ocr:` in config.yaml."""

    def __init__(self, config: dict):
        ocr_cfg = config["ocr"]
        self.client = AsyncOpenAI(
            base_url=ocr_cfg["base_url"],
            api_key=ocr_cfg["api_key"],
        )
        self.model = ocr_cfg["model"]
        self.dpi = ocr_cfg.get("dpi", 200)
        self.max_tokens = ocr_cfg.get("max_tokens", 4096)

    async def ocr_page(self, img_b64: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image. Preserve paragraph breaks. Return only the extracted text, no commentary."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    async def ocr_pdf(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        texts = []
        for page in doc:
            pix = page.get_pixmap(dpi=self.dpi)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            text = await self.ocr_page(img_b64)
            texts.append(text)
        doc.close()
        return "\n\n".join(texts)
