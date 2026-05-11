"""i18n package — exposes t() for all CLI translation lookups."""
from .translate import t
from .catalog import DEFAULT_STRINGS

__all__ = ["t", "DEFAULT_STRINGS"]
