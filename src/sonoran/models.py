from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CADStandardResponse(Generic[T]):
    success: bool
    data: Optional[T] = None
    reason: Any = None
