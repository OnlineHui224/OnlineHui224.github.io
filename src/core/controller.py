"""Application controller connecting UI and extraction services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.gemini_extractor import GeminiExtractor, TicketExtraction


class ExtractionController:
    """Coordinates document extraction and response shaping for the UI."""

    def __init__(self, extractor: GeminiExtractor) -> None:
        self.extractor = extractor

    def extract_ticket_data(self, file_path: str) -> dict[str, Any]:
        extraction: TicketExtraction = self.extractor.extract_from_file(Path(file_path))
        return extraction.model_dump()
