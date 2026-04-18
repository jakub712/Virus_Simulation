# Virus Spread Simulation API

A FastAPI backend that simulates the spread of historical and modern viruses across real-world countries. Uses live weather, population, and air quality data to feed an epidemiological model giving each simulation a unique, data-driven result based on actual conditions.

Built with FastAPI, PostgreSQL, SQLAlchemy, and Docker.

## What it does

Send a country and a virus, get back a day-by-day simulation of how that outbreak would unfold. The engine pulls real temperature, humidity, population density, and air quality data at runtime, then factors in the country's healthcare infrastructure to determine infection spread, recovery rates, and mortality.

You can compare two countries running the same virus side-by-side, retrieve all historical runs from the database, or just query a country's environmental profile on its own.

## Viruses

| Virus | Infection Rate | Mortality Rate | Recovery Time |
|---|---|---|---|
| Black Plague | 0.80 | 0.70 | 10 days |
| Spanish Flu | 0.75 | 0.10 | 7 days |
| Smallpox | 0.70 | 0.30 | 21 days |
| COVID-19 | 0.60 | 0.02 | 14 days |
| Cholera | 0.50 | 0.25 | 5 days |
| Ebola | 0.40 | 0.50 | 14 days |

## How the model works

The simulation runs a day-by-day loop based on a modified SIR model — Susceptible, Infected, Recovered, Dead — where each day's outcome feeds into the next. Rather than using static country profiles, every simulation pulls live data at request time so results reflect actual current conditions.

### Environmental factors

Before the loop starts, four multipliers are calculated from real-world data:

**Temperature factor** scales spread based on how far the country's current temperature is from the virus's optimal climate. The formula `max(0.5, 1.0 - (temp_diff / 40))` means a virus in its ideal climate spreads at full rate, but is never reduced below 50% — cold weather slows it, it doesn't stop it.

**Density factor** is clamped between 0.15 and 1.0 using `density / 500`. A minimum of 75 people/km² is enforced before this calculation — island nations and sparsely populated countries with unusually low recorded densities were producing unrealistically slow spreads in testing, so the floor prevents the model from treating them as nearly empty.

**Humidity factor** is a straight linear ratio (`humidity / 100`). Higher humidity increases airborne transmission — this is well-documented for respiratory viruses and generalised here across all virus types as a base assumption.

**Sanitation factor** (`sanitation / 100`) is applied on the infection side, not just mortality. Poor sanitation increases the rate at which the virus reaches new hosts, not just how badly it affects them once infected.

### Healthcare score

The healthcare score is a composite of three normalised metrics:

```
doctors_score    = min(doctors_per_1000 / 5.0, 1.0)
beds_score       = min(beds_per_1000 / 13.0, 1.0)
sanitation_score = min(sanitation_percent / 100.0, 1.0)

score = (doctors_score + beds_score + sanitation_score) / 3
```

The denominators (5.0, 13.0) represent realistic upper bounds — countries near those figures score close to 1.0. The score is clamped to a minimum of 0.15 in the simulation so that even the worst healthcare systems retain some capacity to treat patients. Without this floor, mortality in low-scoring countries compounded unrealistically fast in early testing.

### The daily loop

Each day calculates three values:

```
new_infections = healthy × effective_infection_rate × (infected / population)
                 × temp_factor × humidity_factor × sanitation_factor

new_deaths     = (infected × mortality_rate / recovery_time) × (1 - score) × 0.5

new_recoveries = infected × (1 - mortality_rate) / recovery_time × max(score, 0.1)
```

New infections use a frequency-dependent term `(infected / population)` so spread naturally slows as the susceptible pool shrinks. If deaths and recoveries together would exceed the current infected count in a single day, both are scaled down proportionally to prevent the pool going negative.

The loop breaks early if the infected count drops below 0.5. At that point the outbreak has effectively ended.

## Endpoints

### `GET /{country}`

Fetches live environmental and healthcare data for a country and stores it in the database.

**Example:** `GET /Germany`

```json
{
  "country": "Germany",
  "temperature": 12.4,
  "humidity": 71,
  "population": 83200000,
  "density": 233.5,
  "air_quality": 2,
  "healthcare": 0.84
}
```

---

### `POST /sim/{country}/{virus}/{days}`

Runs a full simulation. Returns final population counts and a day-by-day history.

**Example:** `POST /sim/Germany/Ebola/365`

```json
{
  "country": "Germany",
  "virus": "Ebola",
  "simulation": {
    "healthy": 81200000,
    "infected": 0,
    "recovered": 1950000,
    "dead": 50000,
    "history": [
      { "day": 1, "healthy": 83199900, "infected": 150, "recovered": 0, "dead": 0 }
    ]
  }
}
```

Virus options: `Black_Plague`, `Ebola`, `COVID`, `Spanish_Flu`, `Smallpox`, `Cholera`

Recommended: 365 days

---

### `GET /compare_sims/{country1}/{country2}/{virus}/{days}`

Runs two full simulations in one request and returns them side-by-side for direct comparison.

**Example:** `GET /compare_sims/Poland/Somalia/Ebola/365`

```json
{
  "country1": "Poland",
  "country2": "Somalia",
  "virus": "Ebola",
  "simulation1": {
    "healthy": 36100000,
    "infected": 0,
    "recovered": 1100000,
    "dead": 192000,
    "history": [...]
  },
  "simulation2": {
    "healthy": 17800000,
    "infected": 0,
    "recovered": 980000,
    "dead": 1220000,
    "history": [...]
  }
}
```

Virus options: `Black_Plague`, `Ebola`, `COVID`, `Spanish_Flu`, `Smallpox`, `Cholera`

---

## Frontend

The repo includes `index.html` — a standalone browser UI for the simulator. Open it directly in any browser, point it at your running API, and run simulations without touching the docs.

### Features

- **Step-based input** — country, pathogen, and duration are laid out as a clear three-step flow
- **Live country fetch** — hit Fetch Data to pull real environmental stats from the API before running
- **SIR chart** — day-by-day susceptible / infected / recovered curves rendered with Chart.js
- **Results as percentages** — peak infected, total deaths, and recovered are shown as a share of population so results are immediately comparable across countries of different sizes
- **Country compare** — run two countries against the same virus side-by-side on independent charts, with its own virus and duration selectors
- **Risk badge** — each result is tagged Extreme / High / Moderate / Low Risk based on mortality rate and R₀
- **Mobile responsive** — works on narrow screens; inputs stack and charts scale down cleanly

### Wiring it to the API

The frontend ships with a mock country database so it runs standalone without a live backend. To connect it to your real API, replace two sections in `index.html`:

**1. Country fetch** — in `fetchCountry()`, replace the mock lookup with a call to `GET /{country}`:

```javascript
async function fetchCountry() {
  const raw = document.getElementById('countryInput').value.trim();
  if (!raw) return;

  const btn = document.getElementById('fetchBtn');
  btn.classList.add('loading');
  btn.innerHTML = '<span class="fetch-icon">◌</span> <span class="fetch-label">Fetching…</span>';

  const res = await fetch(`${document.getElementById('apiUrl').value}/${raw}`);
  const data = await res.json();

  countryData = {
    name: data.country,
    population: data.population,
    r0mod: 1.0   // optionally derive from healthcare score
  };

  document.getElementById('countryCardName').textContent = data.country;
  document.getElementById('cstatPop').textContent = fmt(data.population);
  document.getElementById('cstatDensity').textContent = data.density + '/km²';
  document.getElementById('cstatHealth').textContent = (data.healthcare * 100).toFixed(0) + '/100';
  document.getElementById('cstatR0').textContent = 'x1.00';
  document.getElementById('countryCard').classList.add('visible');

  btn.classList.remove('loading');
  btn.innerHTML = '<span class="fetch-icon">◎</span> <span class="fetch-label">Fetch Data</span>';
}
```

**2. Simulation run** — in `runSimulation()`, replace the local `runSIR()` call with a call to `POST /sim/{country}/{virus}/{days}`:

```javascript
const virusName = selectedVirus.name.replace(' ', '_').replace('-', '');
const res = await fetch(
  `${apiUrl}/sim/${cd.name}/${virusName}/${duration}`,
  { method: 'POST' }
);
const data = await res.json();
// data.simulation.history is the day-by-day array
// data.simulation.dead / recovered / healthy are the final counts
```

The compare tab follows the same pattern using `GET /compare_sims/{country1}/{country2}/{virus}/{days}`.

---

## Setup

### Requirements

- Docker + Docker Compose
- OpenWeatherMap API key (free tier works)

### 1. Clone the repo

```bash
git clone https://github.com/jakub712/Virus_Simulation.git
cd Virus_Simulation
```

### 2. Create a `.env` file

```
GET_WEATHER_API_KEY=your_openweathermap_key
DATABASE_URL=postgresql://postgres:password@db:5432/simulator
```

### 3. Run with Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`. The database starts up first — Docker Compose waits for Postgres to pass its health check before launching the API.

### 4. Open the frontend

```
open index.html
```

Enter `http://localhost:8000` in the API field at the top, then run simulations directly from the browser.

### 5. Interactive docs

```
http://localhost:8000/docs
```

## Running tests

Tests use SQLite in-memory so no database setup is needed.

```bash
pytest tests/
```

The test suite covers:

- Country data retrieval
- Full simulation run
- Simulation comparison with fixture-seeded data and teardown

## External APIs

| API | Usage |
|---|---|
| OpenWeatherMap | Temperature, humidity, air quality index |
| REST Countries | Population, land area, coordinates |

Healthcare data (doctors per 1000, hospital beds per 1000, sanitation percentage) is stored locally in `app/DATA/healthcare_data.json`.

## Stack

- **FastAPI** — API framework
- **PostgreSQL** — production database
- **SQLAlchemy** — ORM
- **Docker + Docker Compose** — containerised deployment
- **pytest** — test suite
- **OpenWeatherMap API** — live environmental data
- **REST Countries API** — population and geographic data
