import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from app.main import app
from app.database import Base, get_db
from app.models import Product

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)


def test_upload_valid_csv(test_db):
    
    csv_content = b"""sku,name,brand,color,size,mrp,price,quantity
SKU001,Product 1,BrandA,Red,M,100.0,80.0,10
SKU002,Product 2,BrandB,Blue,L,200.0,150.0,5"""
    
    files = {"file": ("products.csv", BytesIO(csv_content), "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows"] == 2
    assert data["invalid_rows"] == 0
    assert data["total_rows"] == 2


def test_upload_invalid_price(test_db):
    
    csv_content = b"""sku,name,brand,color,size,mrp,price,quantity
SKU001,Product 1,BrandA,Red,M,100.0,150.0,10"""
    
    files = {"file": ("products.csv", BytesIO(csv_content), "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows"] == 0
    assert data["invalid_rows"] == 1


def test_upload_missing_required_field(test_db):
    
    csv_content = b"""sku,name,brand,color,size,mrp,quantity
SKU001,Product 1,BrandA,Red,M,100.0,10"""
    
    files = {"file": ("products.csv", BytesIO(csv_content), "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 400


def test_upload_negative_quantity(test_db):
    
    csv_content = b"""sku,name,brand,color,size,mrp,price,quantity
SKU001,Product 1,BrandA,Red,M,100.0,80.0,-5"""
    
    files = {"file": ("products.csv", BytesIO(csv_content), "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["invalid_rows"] == 1


def test_upload_duplicate_sku(test_db):
    
    csv_content = b"""sku,name,brand,color,size,mrp,price,quantity
SKU001,Product 1,BrandA,Red,M,100.0,80.0,10
SKU001,Product 2,BrandB,Blue,L,200.0,150.0,5"""
    
    files = {"file": ("products.csv", BytesIO(csv_content), "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows"] == 1
    assert data["invalid_rows"] == 1


def test_upload_non_csv_file(test_db):
   
    files = {"file": ("test.txt", BytesIO(b"not a csv"), "text/plain")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]