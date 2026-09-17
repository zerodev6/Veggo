from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None

class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    page: int
    limit: int
    total: int
    pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: PaginatedData[T]
