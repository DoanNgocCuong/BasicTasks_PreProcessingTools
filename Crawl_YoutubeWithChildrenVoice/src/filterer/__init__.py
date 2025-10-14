# filterer package

"""
Filterer Package - Content filtering and validation

This package handles API-based filtering of processed content
to ensure quality and appropriateness of children's voice data.
"""

from .api_client import FiltererAPIClient, FilterResult

__all__ = [
    "FiltererAPIClient",
    "FilterResult"
]