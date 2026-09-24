---
title: "Take-Home & Live-Coding Exercises"
---

# Take-Home & Live-Coding Exercises

Real, scoped coding exercises recalled from actual interviews —
attempt each one cold under a time box, then check your approach
against the "what a strong solution demonstrates" list. Distinct from
[Mock Projects](chapter-33.md): these are bite-sized, interview-scoped
tasks (30-90 minutes), not portfolio-scale builds.

## Exercise 1: Weather CLI from a City Directory

**Source:** asked in a real interview round (2026-09).

**The task, as given:**

- Read a CSV file listing 50 cities, each with `name`, `lat`, `lng`.
- Let the user select a city from that list.
- Using the selected city's lat/lng, call a weather API.
- Fetch a 7-day forecast.
- Print the forecast to the CLI.

**Suggested time box:** 45–60 minutes.

**Clarifying questions worth asking before writing any code** — asking
these is itself part of what's being evaluated; a senior candidate
scopes the problem before typing:

- Which weather API? ([Open-Meteo](https://open-meteo.com) is free,
  needs no API key, and is a good default to practice against.)
- Does "print" mean raw JSON, a formatted table, or either is fine?
- Exact numbered selection from the list, or should city lookup
  support partial/fuzzy name matching?
- Any expectation around error handling — city not found, API
  timeout, malformed response?
- One-shot run, or a loop that lets the user pick another city without
  restarting the program?

**What a strong solution demonstrates:**

- Clean separation between CSV loading, the API client, and the
  CLI/presentation layer — not one large `main()` doing everything.
- A real HTTP client with error handling (timeout, non-200 response,
  malformed JSON) — not a bare `requests.get()` with no `try/except`.
- A typed `City` and `DayForecast` (dataclass or `NamedTuple`) instead
  of raw dicts passed around and indexed by string keys.
- Input validation on city selection — a bad index or typo shouldn't
  crash the program with an unhandled exception.
- At least one test that doesn't require a live network call — the
  CSV parsing and response-parsing logic should be testable with an
  injected/fake HTTP client.

**A starter structure to practice against:**

```python
# cities.py
from dataclasses import dataclass
import csv

@dataclass(frozen=True)
class City:
    name: str
    lat: float
    lng: float

def load_cities(csv_path: str) -> list[City]:
    with open(csv_path, newline="") as f:
        return [
            City(row["name"], float(row["lat"]), float(row["lng"]))
            for row in csv.DictReader(f)
        ]

# weather_client.py
import requests
from dataclasses import dataclass

@dataclass(frozen=True)
class DayForecast:
    date: str
    temp_max: float
    temp_min: float
    precipitation_mm: float

class WeatherClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def get_forecast(self, lat: float, lng: float, days: int = 7) -> list[DayForecast]:
        response = self.session.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": days,
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()["daily"]
        return [
            DayForecast(date, tmax, tmin, precip)
            for date, tmax, tmin, precip in zip(
                data["time"], data["temperature_2m_max"],
                data["temperature_2m_min"], data["precipitation_sum"],
            )
        ]

# cli.py
def prompt_city_selection(cities: list[City]) -> City:
    for i, city in enumerate(cities, start=1):
        print(f"{i}. {city.name}")
    while True:
        choice = input("Select a city (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(cities):
            return cities[int(choice) - 1]
        print("Invalid selection, try again.")

def print_forecast(city: City, forecast: list[DayForecast]) -> None:
    print(f"\n7-day forecast for {city.name}:")
    for day in forecast:
        print(f"  {day.date}: {day.temp_min}°C - {day.temp_max}°C, "
              f"{day.precipitation_mm}mm precipitation")

def main():
    cities = load_cities("cities.csv")
    selected = prompt_city_selection(cities)
    forecast = WeatherClient().get_forecast(selected.lat, selected.lng)
    print_forecast(selected, forecast)

if __name__ == "__main__":
    main()
```

**Likely follow-up questions an interviewer asks once the code works:**

- "How would you add caching so re-selecting the same city within a
  minute doesn't re-hit the API?" — same TTL-based pattern as
  [LLM Response Caching §4](llm-response-caching.md#4-is-every-llm-response-worth-caching-and-how-do-you-pick-a-ttl),
  just at CLI scale instead of an API-response scale.
- "How would you test this without making real network calls in CI?"
  — the `WeatherClient(session=...)` constructor above exists
  specifically so a test can inject a fake session returning canned
  JSON, instead of hitting the real API.
- "What if the CSV had 50,000 cities instead of 50 — does your
  selection UX still work?" — tests whether the candidate hardcoded an
  assumption (printing every city as a numbered list) that doesn't
  scale, versus building a search/filter step before selection.
- "What happens if two cities in the CSV have the same name?" — tests
  whether selection logic silently picks the wrong one, or handles the
  ambiguity (e.g. disambiguating by showing lat/lng, or requiring a
  unique identifier).

---

*More exercises get added here as they come up in real interviews —
this page is meant to grow, not stay a fixed list.*
