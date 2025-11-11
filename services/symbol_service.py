"""
services/symbol_service.py

Symbol parsing and formatting service.

Handles DTC symbol formats and extracts display-friendly names.
Example: 'F.US.MESZ25' -> 'MES'
"""

from __future__ import annotations

from typing import Optional
from utils.logger import get_logger


log = get_logger(__name__)


class SymbolService:
    """
    Symbol parsing and formatting service.

    Handles conversion between DTC full symbols and display symbols.
    """

    @staticmethod
    def extract_display_symbol(full_symbol: str) -> str:
        """
        Extract 3-letter display symbol from full DTC symbol.

        Example: 'F.US.MESZ25' -> 'MES'

        Format breakdown:
        - F = Exchange (Futures)
        - US = Country
        - MESZ25 = Product code + expiry (MES = Micro E-mini S&P 500, Z25 = Dec 2025)

        Args:
            full_symbol: Full DTC symbol string

        Returns:
            Display symbol (3 letters) or full symbol if format not recognized
        """
        try:
            # Look for pattern: *.US.XXX* where XXX are the 3 letters we want
            parts = full_symbol.split(".")
            for i, part in enumerate(parts):
                if part == "US" and i + 1 < len(parts):
                    # Get the next part after 'US'
                    next_part = parts[i + 1]
                    if len(next_part) >= 3:
                        # Extract first 3 letters
                        return next_part[:3].upper()
            # Fallback: return as-is
            return full_symbol.strip().upper()
        except Exception:
            return full_symbol.strip().upper()

    @staticmethod
    def parse_symbol_parts(full_symbol: str) -> dict[str, Optional[str]]:
        """
        Parse full DTC symbol into component parts.

        Args:
            full_symbol: Full DTC symbol string

        Returns:
            Dict with keys: exchange, country, product, expiry, display
        """
        try:
            parts = full_symbol.split(".")
            if len(parts) >= 3:
                exchange = parts[0]
                country = parts[1]
                product_with_expiry = parts[2]

                # Extract product code (first 2-3 letters) and expiry
                product = product_with_expiry[:3] if len(product_with_expiry) >= 3 else product_with_expiry
                expiry = product_with_expiry[3:] if len(product_with_expiry) > 3 else None

                return {
                    "exchange": exchange,
                    "country": country,
                    "product": product,
                    "expiry": expiry,
                    "display": product,
                }

            return {
                "exchange": None,
                "country": None,
                "product": full_symbol.strip().upper(),
                "expiry": None,
                "display": full_symbol.strip().upper(),
            }
        except Exception:
            return {
                "exchange": None,
                "country": None,
                "product": full_symbol.strip().upper(),
                "expiry": None,
                "display": full_symbol.strip().upper(),
            }

    @staticmethod
    def format_symbol_for_display(full_symbol: str, include_expiry: bool = False) -> str:
        """
        Format symbol for UI display.

        Args:
            full_symbol: Full DTC symbol string
            include_expiry: If True, include expiry month/year

        Returns:
            Formatted symbol string
        """
        parts = SymbolService.parse_symbol_parts(full_symbol)

        if include_expiry and parts["expiry"]:
            return f"{parts['product']}{parts['expiry']}"

        return parts["display"] or full_symbol.strip().upper()
