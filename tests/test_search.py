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
        Product(sku="SKU001", name="T-Shirt", brand="StreamThreads", color="Red", size="M", mrp=1000, price=800, quantity=10),
        Product(sku="SKU002", name="Jeans", brand="StreamThreads", color="Blue", size="L", mrp=2000, price=1500, quantity=5),
        Product(sku="SKU003", name="Shirt", brand="DenimWorks", color="Red", size="S", mrp=1500, price=1200, quantity=8),
        Product(sku="SKU004", name="Pants", brand="FashionHub", color="Black", size="M", mrp=2500, price=2200, quantity=3),
    ]
    db.bulk_save_objects(products)
    db.commit()
    db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)


def test_search_by_brand(test_db):
    
    response = client.get("/products/search?brand=StreamThreads")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("StreamThreads" in p["brand"] for p in data["products"])


def test_search_by_color(test_db):
    
    response = client.get("/products/search?color=Red")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("Red" in p["color"] for p in data["products"])


def test_search_by_price_range(test_db):
    
    response = client.get("/products/search?minPrice=500&maxPrice=2000")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert all(500 <= p["price"] <= 2000 for p in data["products"])


def test_search_combined_filters(test_db):
    
    response = client.get("/products/search?brand=StreamThreads&minPrice=1000&maxPrice=2000")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    product = data["products"][0]
    assert "StreamThreads" in product["brand"]
    assert 1000 <= product["price"] <= 2000


def test_search_no_results(test_db):
    
    response = client.get("/products/search?brand=NonExistent")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["products"]) == 0


def test_search_with_pagination(test_db):
    
    response = client.get("/products/search?page=1&limit=2")
    
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["products"]) == 2