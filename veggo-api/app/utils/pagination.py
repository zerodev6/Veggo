import math
from typing import Any, Dict, List, TypeVar
from app.schemas.common import PaginatedData, PaginatedResponse

T = TypeVar("T")


def parse_pagination(page: int = 1, limit: int = 20) -> tuple[int, int, int]:
    """Ensures page is >= 1 and limit is clamped between 1 and 100."""
    page = max(1, page)
    limit = min(100, max(1, limit))
    skip = (page - 1) * limit
    return skip, limit, page


def build_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int
) -> Dict[str, Any]:
    """Formats standard paginated dictionary response."""
    pages = math.ceil(total / limit) if limit > 0 else 0
    return {
        "success": True,
        "message": "Success",
        "data": {
            "items": items,
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages
        }
    }
