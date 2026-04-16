import requests
import os
import json
from dotenv import load_dotenv
load_dotenv()



def get_population_info(country):
    url = f"https://restcountries.com/v3.1/name/{country}?fields=population,area,latlng"
    response = requests.get(url)
    data = response.json()[0]
    population = data['population']
    area = data['area']
    density = population / area
    lat = data["latlng"][0]
    lon = data["latlng"][1]
    air = get_air_quality(lat, lon)
    return {
        "population": population,
        "density": density,
        "lat": lat,
        "lon": lon,
        "air_quality": air
    }

def get_weather_info(country):
    API_KEY = os.getenv("GET_WEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={country}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    temperature = data['main']['temp']
    humidity = data['main']['humidity']
    return {
        "temperature": temperature,
        "humidity": humidity
    }

def get_air_quality(lat, lon):
    API_KEY = os.getenv("GET_WEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    response = requests.get(url)
    data = response.json()
    air_quality = data["list"][0]["main"]["aqi"]
    return air_quality

class Virus:
    def __init__(self, infection_rate, mortality_rate, recovery_time, incubation_time, temp_optimal):
        self.infection_rate = infection_rate
        self.mortality_rate = mortality_rate
        self.recovery_time = recovery_time
        self.incubation_time = incubation_time
        self.temp_optimal = temp_optimal

Black_Plague = Virus(0.8, 0.7, 10, 5, 20)
Ebola = Virus(0.4, 0.5, 14, 8, 28)
COVID = Virus(0.6, 0.02, 14, 5, 5)
Spanish_Flu = Virus(0.75, 0.1, 7, 3, 10)
Smallpox = Virus(0.7, 0.3, 21, 12, 15)
Cholera = Virus(0.5, 0.25, 5, 2, 30)

VIRUSES = {
    "black_plague": Black_Plague,
    "ebola": Ebola,
    "covid": COVID,
    "spanish_flu": Spanish_Flu,
    "smallpox": Smallpox,
    "cholera": Cholera
}

def virus_sim(v, temp, humidity, population, density, score, sanitation, days):
    days = int(days)
    healthy = float(population - 1000)
    infected = 1000
    recovered = 0.0
    dead = 0.0
    history = []

    temp_diff = abs(temp - v.temp_optimal)
    temp_factor = max(0.5, 1.0 - (temp_diff / 40))
    density_factor = max(min(density / 500, 1.0), 0.15)
    humidity_factor = humidity / 100
    sanitation_factor = max(0.3, 1 - (sanitation / 200))

    effective_infection_rate = v.infection_rate * (0.5 + density_factor * 0.5)

    for day in range(days):
        if infected < 0.5:
            break

        new_infections = (
            healthy
            * effective_infection_rate
            * (infected / population)
            * temp_factor
            * humidity_factor
            * sanitation_factor
        )
        new_infections = min(new_infections, healthy)

        base_deaths = infected * v.mortality_rate / v.recovery_time
        new_deaths = base_deaths * (1.0 - score) * 0.5
        new_recoveries = infected * (1.0 - v.mortality_rate) / v.recovery_time * max(score, 0.1)

        total_outflow = new_deaths + new_recoveries
        if total_outflow > infected:
            scale = infected / total_outflow
            new_deaths *= scale
            new_recoveries *= scale

        healthy -= new_infections
        infected += new_infections - new_deaths - new_recoveries
        recovered += new_recoveries
        dead += new_deaths

        history.append({
            "day": day + 1,
            "healthy": round(healthy),
            "infected": round(infected),
            "recovered": round(recovered),
            "dead": round(dead),
        })

    return {
        "healthy": round(healthy),
        "infected": round(infected),
        "recovered": round(recovered),
        "dead": round(dead),
        "history": history,
    }

def get_health_info(country):
    with open("app/DATA/healthcare_data.json", "r") as file:
        health_data = json.load(file)

    for entry in health_data:
        if entry["name"].lower() == country.lower():
            return entry


def calculate_healthcare_score(doctors, beds, sanitation):
    if not doctors or not beds or not sanitation:
        return 0.5
    doctors_score = min(doctors / 5.0, 1.0)
    beds_score = min(beds / 13.0, 1.0)
    sanitation_score = min(sanitation / 100.0, 1.0)
    score = (doctors_score + beds_score + sanitation_score) / 3
    return round(score, 2)