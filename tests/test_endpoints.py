import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app, get_db

from app.DB.session import Base
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from fastapi import status
from app.DB import models
import pytest 
from app.DB.models import Population_Data, SimResults

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

TestingSessionLocal = sessionmaker(autocommit = False, autoflush= False, bind=engine)
Base.metadata.create_all(bind=engine)

def overide_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = overide_get_db
client = TestClient(app)

@pytest.fixture
def test_country():
    db = TestingSessionLocal()
    sim1 = SimResults(
        country="Poland",
        virus="Ebola",
        healthy=37000000,
        infected=1000,
        recovered=500,
        dead=200
    )
    sim2 = SimResults(
        country="Somalia",
        virus="Ebola",
        healthy=19000000,
        infected=500,
        recovered=100,
        dead=50
    )

    db = TestingSessionLocal()

    db.add(sim1)
    db.add(sim2)
    db.commit()
    db.refresh(sim1)
    db.refresh(sim2)
    yield sim1, sim2
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM sim_results;"))
        connection.commit()

def test_get_country_data():
    responce = client.get("/Spain")
    assert responce.status_code == status.HTTP_200_OK
    data = responce.json()
    assert data["country"] == "Spain"
    assert "temperature" in data
    assert "population" in data
    assert "healthcare" in data

def test_simulate():
    responce = client.post("/sim/Spain/Ebola/365")
    assert responce.status_code == status.HTTP_200_OK
    data = responce.json()
    assert data["country"] == "Spain"
    assert data["virus"] == "Ebola"
    assert "simulation" in data

def test_compare_sims(test_country):
    sim1, sim2 = test_country
    response = client.get(f"/compare_sims/{sim1.country}/{sim2.country}/Ebola/365")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["country1"] == "Poland"
    assert data["country2"] == "Somalia"
    assert "simulation1" in data
    assert "simulation2" in data
