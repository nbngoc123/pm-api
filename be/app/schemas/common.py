from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class Page(ORM, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class Msg(ORM):
    message: str = "ok"


def D(x) -> Decimal:
    return Decimal(str(x))
