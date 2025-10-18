import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    
    # Add test data
    db = TestingSessionLocal()
    products = [
        Product(sku="SKU001", name="Product 1", brand="BrandA", color="Red", size="M", mrp=100, price=80, quantity=10),
        Product(sku="SKU002", name="Product 2", brand="BrandB", color="Blue", size="L", mrp=200, price=150, quantity=5),
        Product(sku="SKU003", name="Product 3", brand="BrandA", color="Red", size="S", mrp=150, price=120, quantity=8),
    ]
    db.bulk_save_objects(products)
    db.commit()
    db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)


def test_get_products_default(test_db):
    
    response = client.get("/products")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["products"]) == 3


def test_get_products_pagination(test_db):
    
    response = client.get("/products?page=1&limit=2")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["products"]) == 2


def test_get_products_page_2(test_db):
    
    response = client.get("/products?page=2&limit=2")
    
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert len(data["products"]) == 1


def test_get_products_invalid_page(test_db):
    
    response = client.get("/products?page=0")
    
    assert response.status_code == 422