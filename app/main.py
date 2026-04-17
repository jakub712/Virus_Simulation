from fastapi import FastAPI, Path, Depends, HTTPException
from app.DB import models
from app.DB.models import Population_Data, SimResults
from app.DB.session import engine, SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.data import virus_sim, VIRUSES, get_health_info, calculate_healthcare_score
from app.data import (
    get_population_info,
    get_weather_info,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def frontend():
    return FileResponse("index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependancy = Annotated[Session, Depends(get_db)]

@app.get("/compare_sims/{country1}/{country2}/{virus}/{days}", status_code= status.HTTP_200_OK)
def compare_simulations(db:db_dependancy, country1:str, country2:str, days:int = Path(description="recomended is 365"), virus:str = Path(description="Options: Black_Plague, Ebola, COVID, Spanish_Flu, Smallpox, Cholera")):
    try:
        temp1 = get_weather_info(country1)['temperature']
        temp2 = get_weather_info(country2)['temperature']
        humidity1 = get_weather_info(country1)['humidity']
        humidity2 = get_weather_info(country2)['humidity']
        population1 = get_population_info(country1)['population']
        population2 = get_population_info(country2)['population']
        density1 = get_population_info(country1)['density']
        density2 = get_population_info(country2)['density']
        health1 = get_health_info(country1)
        health2 = get_health_info(country2)
        doctors1 = health1["doctors_per_1000"]
        beds1 = health1["beds_per_1000"]
        sanitation1  = health1["sanitation_percent"]
        score1 = calculate_healthcare_score(doctors1, beds1, sanitation1)
        doctors2 = health2["doctors_per_1000"]
        beds2 = health2["beds_per_1000"]
        sanitation2  = health2["sanitation_percent"]
        score2 = calculate_healthcare_score(doctors2, beds2, sanitation2)
        score1 = max(score1, 0.15)
        score2 = max(score2, 0.15)
        density1 = max(density1, 75)
        density2 = max(density2, 75)

    except Exception:
        raise HTTPException(status_code=404, detail="Country not found")

    try:
        v = VIRUSES.get(virus.lower())
        sim_results1 = virus_sim(v, temp1, humidity1, population1, density1, score1, sanitation1, days)
        sim_results2 = virus_sim(v, temp2, humidity2, population2, density2, score2, sanitation2, days)
    except Exception:
        raise HTTPException(status_code=404, detail="Virus not found")
    
    simulation_model1 = SimResults(
        country = country1,
        virus = virus,
        healthy = sim_results1["healthy"],
        infected = sim_results1["infected"],
        recovered=sim_results1["recovered"],
        dead = sim_results1["dead"]
    )
    simulation_model2 = SimResults(
        country = country2,
        virus = virus,
        healthy = sim_results2["healthy"],
        infected = sim_results2["infected"],
        recovered=sim_results2["recovered"],
        dead = sim_results2["dead"]
    )
    db.add(simulation_model1)
    db.add(simulation_model2)
    db.commit()

    return{
        "country1": country1,
        "country2": country2,
        "virus":virus,
        "simulation1": sim_results1,
        "simulation2": sim_results2    
    }

@app.get("/sim/read_all",status_code= status.HTTP_200_OK)
def read_all_sims(db:db_dependancy):
    return db.query(SimResults).all()

@app.get("/country/read_all", status_code=status.HTTP_200_OK)
def read_all_population_info(db:db_dependancy):
    return db.query(Population_Data).all()


@app.get("/{country}", status_code=status.HTTP_200_OK)
def get_country_data(country: str, db:db_dependancy):
    try:
        temp = get_weather_info(country)['temperature']
        humidity = get_weather_info(country)['humidity']
        population = get_population_info(country)['population']
        density = get_population_info(country)['density']
        air_quality = get_population_info(country)['air_quality']
        health = get_health_info(country)
        doctors = health["doctors_per_1000"]
        beds = health["beds_per_1000"]
        sanitation = health["sanitation_percent"]
        score = calculate_healthcare_score(doctors, beds, sanitation)
    except Exception:
        raise HTTPException(status_code=404, detail="Country not found")

    country_model = Population_Data(
        country = country,
        temperature = temp,
        humidity = humidity,
        population = population,
        density = density,
        air_quality = air_quality,
        healthcare_score = score
    )
    db.add(country_model)
    db.commit()

    return {
        "country": country,
        "temperature": temp,
        "humidity": humidity,
        "population": population,
        "density": density,
        "air_quality": air_quality,
        "healthcare": score
    }
