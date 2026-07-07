"""Gemini extraction service for aviation ticket intelligence."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class FlightTracking(BaseModel):
    carrier: str = ""
    flight_number: str = ""
    from_code: str = ""
    to_code: str = ""
    departure_date: str = ""
    tracking_details: str = ""


class TicketExtraction(BaseModel):
    passenger_names: list[str] = Field(default_factory=list)
    flights: list[FlightTracking] = Field(default_factory=list)
    ai_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ticket_reference: str = ""
    pnr: str = ""
    remarks: str = ""


class GeminiExtractor:
    """Extracts structured travel data using Google Gemini."""

    _AIRLINE_CODE_MAP = {
        "turkish airlines": "TK",
        "saudia": "SV",
        "ethiopian airlines": "ET",
        "qatar airways": "QR",
    }

    _AIRPORT_CODE_MAP = {
        "lagos": "LOS",
        "doha": "DOH",
        "abuja": "ABV",
        "madinah": "MED",
        "jeddah": "JED",
        "istanbul": "IST",
    }

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name

    @staticmethod
    def _build_prompt() -> str:
        return (
            "Extract ticket data and return ONLY valid JSON using this schema keys exactly: "
            "{passenger_names:[str], flights:[{carrier:str, flight_number:str, from_code:str, "
            "to_code:str, departure_date:str, tracking_details:str}], ai_confidence:float, "
            "ticket_reference:str, pnr:str, remarks:str}. "
            "Rule 1) Use exact field names from the Pydantic schema. "
            "Rule 2) Do not add unknown keys. "
            "Rule 3) If a value is missing, return an empty string for strings, or 0 for counts. "
            "Rule 4) Keep all flights in chronological order. "
            "Rule 5) Date format must be 'DD MMM' (e.g., '23 JUL') when available. "
            "Rule 6) Ensure ai_confidence is a float between 0.0 and 1.0. "
            "Rule 7) CRITICAL: Convert all airline carrier names into standard 2-letter IATA airline "
            "codes (e.g., TK for Turkish Airlines, SV for Saudia, ET for Ethiopian Airlines, "
            "QR for Qatar Airways). "
            "Rule 8) CRITICAL: Convert all departure and arrival cities/countries into their official "
            "3-letter IATA airport codes (e.g., LOS for Lagos, DOH for Doha, ABV for Abuja, MED for "
            "Madinah, JED for Jeddah, IST for Istanbul). "
            "Rule 9) CRITICAL: Always combine the 2-letter airline carrier code and the flight number "
            "together inside the flight_number field with no spaces (e.g., QR1182, TK1824)."
        )

    @staticmethod
    def _safe_json_loads(raw_text: str) -> dict[str, Any]:
        if not raw_text:
            return {}

        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _to_airline_code(self, carrier: str) -> str:
        raw = (carrier or "").strip()
        if len(raw) == 2 and raw.isalpha():
            return raw.upper()
        return self._AIRLINE_CODE_MAP.get(raw.lower(), raw[:2].upper())

    def _to_airport_code(self, place: str) -> str:
        raw = (place or "").strip()
        if len(raw) == 3 and raw.isalpha():
            return raw.upper()
        return self._AIRPORT_CODE_MAP.get(raw.lower(), raw[:3].upper())

    def _normalize_date(self, value: str) -> str:
        text = (value or "").strip().upper()
        if re.fullmatch(r"\d{2}\s+[A-Z]{3}", text):
            return text
        date_patterns = ("%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%Y-%m-%d")
        for pattern in date_patterns:
            try:
                return datetime.strptime(value, pattern).strftime("%d %b").upper()
            except (TypeError, ValueError):
                continue
        return text

    def _normalize_flight_number(self, carrier_code: str, flight_number: str) -> str:
        number_part = "".join(re.findall(r"\d+", flight_number or ""))
        return f"{carrier_code}{number_part}" if number_part else (flight_number or "").replace(" ", "").upper()

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {
            "passenger_names": payload.get("passenger_names") or [],
            "flights": payload.get("flights") or [],
            "ai_confidence": payload.get("ai_confidence") or 0.0,
            "ticket_reference": payload.get("ticket_reference") or "",
            "pnr": payload.get("pnr") or "",
            "remarks": payload.get("remarks") or "",
        }

        flights: list[dict[str, Any]] = []
        for item in normalized["flights"]:
            item = item or {}
            carrier_code = self._to_airline_code(str(item.get("carrier", "")))
            from_code = self._to_airport_code(str(item.get("from_code", "")))
            to_code = self._to_airport_code(str(item.get("to_code", "")))
            departure_date = self._normalize_date(str(item.get("departure_date", "")))
            formatted = {
                "carrier": carrier_code,
                "flight_number": self._normalize_flight_number(
                    carrier_code, str(item.get("flight_number", ""))
                ),
                "from_code": from_code,
                "to_code": to_code,
                "departure_date": departure_date,
                "tracking_details": str(item.get("tracking_details", "")),
            }
            flights.append(formatted)

        flights.sort(key=lambda value: value["departure_date"] or "ZZZ")
        normalized["flights"] = flights
        try:
            confidence = float(normalized["ai_confidence"])
        except (TypeError, ValueError):
            confidence = 0.0
        normalized["ai_confidence"] = min(1.0, max(0.0, confidence))
        return normalized

    def _load_file_part(self, file_path: str | Path) -> tuple[str, bytes]:
        path = Path(file_path)
        suffix = path.suffix.lower()
        mime_type = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "application/octet-stream")
        return mime_type, path.read_bytes()

    def extract_from_file(self, file_path: str | Path) -> TicketExtraction:
        if not self.api_key:
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY.")

        try:
            import google.generativeai as genai
        except ImportError as error:
            raise RuntimeError("google-generativeai package is required.") from error

        mime_type, binary = self._load_file_part(file_path)
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(
            [
                self._build_prompt(),
                {"mime_type": mime_type, "data": binary},
            ]
        )
        raw_text = getattr(response, "text", "") or ""
        payload = self._safe_json_loads(raw_text)
        normalized = self._normalize_payload(payload)
        return TicketExtraction.model_validate(normalized)
