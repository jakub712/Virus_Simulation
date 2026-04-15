from app.DB.session import Base
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

class Population_Data(Base):
    __tablename__ = 'population_data'
    id = Column(Integer, primary_key= True, index=True)
    country = Column(String)
    temperature = Column(Float)
    humidity = Column(Float)
    population = Column(Integer)
    density = Column(Float)
    air_quality = Column(Integer)
    healthcare_score = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class SimResults(Base):
    __tablename__ = 'sim_results'

    id = Column(Integer, primary_key=True, index= True)
    country = Column(String)
    virus = Column(String)
    healthy = Column(Integer)
    infected = Column(Integer)
    recovered = Column(Integer)
    dead = Column(Integer)
    simulated_at = Column(DateTime, default=datetime.utcnow)