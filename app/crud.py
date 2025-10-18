from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from app.models import Product
from app.schemas import ProductCreate


def create_product(db: Session, product: ProductCreate) -> Product:
    #Create a new product in database
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100
) -> tuple[List[Product], int]:
    #Get all products with pagination
    total = db.query(Product).count()
    products = db.query(Product).offset(skip).limit(limit).all()
    return products, total


def search_products(
    db: Session,
    brand: Optional[str] = None,
    color: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[Product], int]:
    #Search products with filters
    query = db.query(Product)
    
    # Apply filters
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    
    if color:
        query = query.filter(Product.color.ilike(f"%{color}%"))
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    total = query.count()
    products = query.offset(skip).limit(limit).all()
    return products, total


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    #Get product by SKU
    return db.query(Product).filter(Product.sku == sku).first()


def bulk_create_products(db: Session, products: List[ProductCreate]) -> int:
    #Bulk insert products
    db_products = [Product(**product.model_dump()) for product in products]
    db.bulk_save_objects(db_products)
    db.commit()
    return len(db_products)