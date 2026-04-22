"""ITSM adapters — pluggable integrations for ticketing systems."""

from src.itsm.base import ITSMAdapter, ItsmKbArticle, KbSearchResult
from src.itsm.registry import get_adapter

__all__ = ["ITSMAdapter", "ItsmKbArticle", "KbSearchResult", "get_adapter"]
