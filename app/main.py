from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd
from io import StringIO
from typing import Optional
import os

from app.database import get_db, init_db
from app.schemas import ProductResponse, ProductList, UploadResponse
from app.validators import CSVValidator
from app import crud

# Create FastAPI app
app = FastAPI(
    title="Product Catalog API",
    description="Backend service for CSV product upload and management",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Create uploads directory if not exists
    os.makedirs("uploads", exist_ok=True)


@app.get("/")
def root():
    #Root endpoint
    return {
        "message": "Product Catalog API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "products": "/products",
            "search": "/products/search"
        }
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV file
        contents = await file.read()
        csv_data = StringIO(contents.decode('utf-8'))
        df = pd.read_csv(csv_data)
        
        # Validate CSV structure
        is_valid, message = CSVValidator.validate_csv_structure(df)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Validate and process each row
        valid_products = []
        errors = []
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            is_valid, product, error_msg = CSVValidator.validate_row(row_dict, idx + 2)  # +2 for header and 0-index
            
            if is_valid and product:
                # Check for duplicate SKU
                existing = crud.get_product_by_sku(db, product.sku)
                if existing:
                    errors.append({
                        "row": idx + 2,
                        "error": f"Duplicate SKU: {product.sku} already exists"
                    })
                else:
                    valid_products.append(product)
            else:
                errors.append({"row": idx + 2, "error": error_msg})
        
        # Bulk insert valid products
        if valid_products:
            crud.bulk_create_products(db, valid_products)
        
        return UploadResponse(
            message="CSV processed successfully",
            total_rows=len(df),
            valid_rows=len(valid_products),
            invalid_rows=len(errors),
            errors=errors[:10] 
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    except pd.errors.ParserError:
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/products", response_model=ProductList)
def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * limit
    products, total = crud.get_products(db, skip=skip, limit=limit)
    
    return ProductList(
        total=total,
        page=page,
        page_size=limit,
        products=products
    )


@app.get("/products/search", response_model=ProductList)
def search_products(
    brand: Optional[str] = Query(None, description="Filter by brand"),
    color: Optional[str] = Query(None, description="Filter by color"),
    minPrice: Optional[float] = Query(None, ge=0, description="Minimum price"),
    maxPrice: Optional[float] = Query(None, ge=0, description="Maximum price"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """"
    Search and filter products
    
    **Query Parameters:**
    - brand: Filter by brand name (partial match, case-insensitive)
    - color: Filter by color (partial match, case-insensitive)
    - minPrice: Minimum price filter
    - maxPrice: Maximum price filter
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 100)
    
    """
    skip = (page - 1) * limit
    
    products, total = crud.search_products(
        db,
        brand=brand,
        color=color,
        min_price=minPrice,
        max_price=maxPrice,
        skip=skip,
        limit=limit
    )
    
    return ProductList(
        total=total,
        page=page,
        page_size=limit,
        products=products
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)