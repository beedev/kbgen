"""Adapter factory — selects the active ITSM integration by name."""

from functools import lru_cache

from src.config import get_settings
from src.itsm.base import ITSMAdapter
from src.itsm.glpi import GLPIAdapter
from src.itsm.mock import MockITSMAdapter


@lru_cache
def get_adapter(name: str | None = None) -> ITSMAdapter:
    s = get_settings()
    which = (name or s.itsm_adapter).lower()
    if which == "glpi":
        return GLPIAdapter(
            base_url=s.glpi_url,
            app_token=s.glpi_app_token or None,
            user_token=s.glpi_user_token or None,
        )
    if which == "mock":
        return MockITSMAdapter()
    raise ValueError(f"Unknown ITSM adapter: {which}")
