from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100, description="Unique product code")
    name: str = Field(..., min_length=1, max_length=255, description="Product title")
    brand: str = Field(..., min_length=1, max_length=100, description="Product brand")
    color: Optional[str] = Field(None, max_length=50, description="Product color")
    size: Optional[str] = Field(None, max_length=50, description="Product size")
    mrp: float = Field(..., gt=0, description="Maximum Retail Price")
    price: float = Field(..., gt=0, description="Selling price")
    quantity: int = Field(..., ge=0, description="Available quantity")

    @field_validator('price')
    @classmethod
    def validate_price_vs_mrp(cls, v, info):
        if 'mrp' in info.data and v > info.data['mrp']:
            raise ValueError('price must be less than or equal to mrp')
        return v


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductList(BaseModel):
    total: int
    page: int
    page_size: int
    products: list[ProductResponse]


class UploadResponse(BaseModel):
    message: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[dict]