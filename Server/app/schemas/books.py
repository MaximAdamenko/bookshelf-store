from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.auth import InputModel


class BookSearchParams(InputModel):
    q: str | None = Field(None, max_length=200)
    category_id: int | None = Field(None, ge=1)
    author_id: int | None = Field(None, ge=1)
    publisher_id: int | None = Field(None, ge=1)
    min_price_cents: int | None = Field(None, ge=0)
    max_price_cents: int | None = Field(None, ge=0)
    in_stock: bool = False
    sort: Literal["newest", "price_asc", "price_desc", "relevance"] = "newest"
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @model_validator(mode="after")
    def _price_range_sane(self) -> "BookSearchParams":
        if (self.min_price_cents is not None and self.max_price_cents is not None
                and self.min_price_cents > self.max_price_cents):
            raise ValueError("min_price_cents must not exceed max_price_cents")
        return self


class BookCreate(InputModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field("", max_length=5000)
    price_cents: int = Field(ge=0)
    quantity: int = Field(0, ge=0)
    author_ids: list[int] = Field(min_length=1, max_length=10)
    category_ids: list[int] = Field(min_length=1, max_length=10)
    publisher_id: int | None = Field(None, ge=1)


class BookPatch(InputModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    price_cents: int | None = Field(None, ge=0)
    quantity: int | None = Field(None, ge=0)
    is_active: bool | None = None
    author_ids: list[int] | None = Field(None, min_length=1, max_length=10)
    category_ids: list[int] | None = Field(None, min_length=1, max_length=10)
    publisher_id: int | None = Field(None, ge=1)


class AuthorRef(BaseModel):
    author_id: int
    name: str


class CategoryRef(BaseModel):
    category_id: int
    name: str


class PublisherRef(BaseModel):
    publisher_id: int
    name: str


class BookPublic(BaseModel):
    book_id: int
    title: str
    description: str
    price_cents: int
    quantity: int
    cover_path: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    publisher_id: int | None
    publisher: str | None
    authors: list[AuthorRef]
    categories: list[CategoryRef]


class BookListResponse(BaseModel):
    items: list[BookPublic]
    total: int
