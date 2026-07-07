"""Application entry point for INNA ATAINA TRAVELS OPS PRO."""

from __future__ import annotations

import os

from core.controller import ExtractionController
from services.gemini_extractor import GeminiExtractor
from ui.main_window import MainWindow


def main() -> None:
    extractor = GeminiExtractor(api_key=os.getenv("GEMINI_API_KEY"))
    controller = ExtractionController(extractor=extractor)
    app = MainWindow(controller=controller)
    app.mainloop()


if __name__ == "__main__":
    main()
