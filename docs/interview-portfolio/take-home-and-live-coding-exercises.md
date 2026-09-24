---
title: "Take-Home & Live-Coding Exercises"
---

# Take-Home & Live-Coding Exercises

Real, scoped coding exercises recalled from actual interviews —
attempt each one cold under a time box, then check your approach
against the "what a strong solution demonstrates" list. Distinct from
[Mock Projects](chapter-33.md): these are interview-scoped tasks
(30 minutes to a few hours), not portfolio-scale builds. Not all of
them are greenfield either — Exercise 2 is a debug-and-extend task,
a genuinely different skill from building from scratch.

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
  [LLM Response Caching §4](../ai-llm/llm-response-caching.md#4-is-every-llm-response-worth-caching-and-how-do-you-pick-a-ttl),
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

## Exercise 2: Movie Database API — Debug & Extend (Django REST Framework)

**Source:** a real SELISE Python Developer take-home assessment. Full
solution: [movie-database-assessment](https://github.com/Fahad-Md-Kamal/movie-database-assessment)
(private-repo submission, now public).

**What makes this one different from Exercise 1:** the assessment
hands you a partially-built, partially-*broken* Django REST Framework
codebase and a feature spec — not a blank file. The skill being tested
is reading unfamiliar code, finding bugs that don't announce
themselves, and correctly extending existing patterns, not typing
from scratch.

**The task, as given:**

- **Auth**: log in with either username+password or email+password, no
  forgot-password needed. Unauthenticated users get zero access to
  anything.
- **Movies**: authenticated-only viewing (list + detail). Authenticated
  users can create movies; a movie is always linked to its creator;
  only the creator can update it. All movies are visible to any
  authenticated user, not just the creator's own.
- **Ratings**: a 1–5 score, authenticated only. A user can change their
  *own* rating repeatedly. The movie's `avg_rating` recomputes
  automatically on every rating create/update — but the movie's
  `updated_at` must **not** change when only `avg_rating` changes (it
  should only change on an actual movie edit).
- **Reports**: authenticated users can report a movie as inappropriate.
  Only SuperAdmins can list reports. Reports start `Unresolved`, and a
  SuperAdmin resolves each one to either "mark movie as inappropriate"
  or "reject report" — implemented as a **state machine**. An
  inappropriate movie is hidden from everyone *except* its creator (who
  still sees it, marked inappropriate). A SuperAdmin can reverse a
  prior decision at any time.
- Swagger/OpenAPI docs for every endpoint.
- **Acceptance criteria**: 2 regular users + 1 SuperAdmin, 2 movies per
  user, ratings from every user on every movie, one report rejected,
  one report accepted.

**Suggested time box:** 3–5 hours — this is a full formal take-home,
not a short live-coding prompt.

**Real bugs found in this specific assessment** — worth internalizing
as a general checklist for *any* Django/DRF take-home, not just this
one:

- A model missing from `INSTALLED_APPS` — Django raises `Model class
  doesn't declare an explicit app_label`. The fix is in settings, not
  the model file; don't go looking in the wrong place.
- **A validation condition inverted**: the original code raised
  "passwords didn't match" when `password == password2` — exactly
  backwards. This is the single most valuable bug to internalize:
  **read a conditional for what it actually checks, not for what the
  variable or error-message names imply it checks.**
- Write-only serializer fields (`password`, `password2`) mistakenly
  marked `read_only=True` — silently breaks registration, since DRF
  then ignores incoming values for those fields entirely. No error,
  just quietly-wrong behavior.
- A model field (`avg_rating`) added to the model with no migration
  generated for it — a classic "forgot `makemigrations`" gap that only
  surfaces as a runtime DB error, not at code review.
- The wrong permission class wired to an endpoint — `IsAuthenticated`
  where `IsOwnerOrReadOnly` was actually required, silently letting
  any authenticated user edit someone else's movie.
- A URL-ordering bug — a dynamic path parameter route declared
  *before* a static route in `urls.py`, so Django matches the dynamic
  pattern first and the static route becomes unreachable. URL routers
  generally match in declaration order — specific/static routes need
  to come before catch-all/dynamic ones.
- A serializer's `source=` pointed at the wrong related field
  (`source='username'` instead of `source='creator.username'`) —
  returns the wrong data silently, no error raised anywhere.
- `avg_rating` not recalculated when a rating was created/updated — a
  business-rule bug, not a crash; only caught by actually testing the
  acceptance criteria end-to-end, not by reading the code.

**What a strong solution demonstrates:**

- Reading unfamiliar code methodically before changing it — the
  inverted-password-check bug above is invisible from a diff alone;
  it only surfaces by tracing what the code *actually does* against
  what the spec says it should do.
- Correctly updating `avg_rating` without touching `updated_at` —
  Django's `auto_now=True` fires on *any* `.save()` call, so this
  specifically requires `.save(update_fields=[...])` or a targeted
  `.update()` call, not a full `.save()`.
- A real state machine for the report lifecycle — even implemented
  simply (an enum plus a guarded transition method, not a full
  state-machine library), the discipline matters: an invalid
  transition should raise, not silently no-op.
- Consistent visibility filtering — an "inappropriate" movie has to
  disappear from *every* list/detail endpoint except its creator's own
  view. That's a rule that has to be applied uniformly across every
  queryset returning movies, not patched into one view and forgotten
  in another.
- Usable Swagger/OpenAPI docs (e.g. `drf-spectacular`) that accurately
  reflect auth requirements and response shapes, not just "present."

**A design smell worth noticing in this exact assessment, as a
discussion point:** the `Report` model in this codebase has both a
`report_state` enum (`UNRESOLVED`/`REJECTED`/`ACCEPTED`) *and* a
separate `is_closed` boolean. Two fields tracking overlapping state
can drift out of sync — nothing stops code from setting
`report_state='ACCEPTED'` while forgetting to also set
`is_closed=True`. The more robust design derives closed-ness from the
state (`is_closed` as a property: `report_state != UNRESOLVED`) rather
than storing it redundantly. Worth deciding *before* writing your own
version which one you'd pick, and being ready to defend it.

**Likely follow-up questions an interviewer asks about this kind of task:**

- "Walk me through how you found bug X." — tests whether you debugged
  systematically (reading error messages, tracing code, writing a
  failing test first) versus guessing and getting lucky.
- "Why does `auto_now=True` fire on every save, and how did that
  affect your `avg_rating` update?" — a direct test of understanding
  Django's field internals, not just having copy-pasted a fix.
- "How would you enforce that a report can't move from `Rejected` back
  to `Unresolved` directly?" — tests whether the state machine
  actually *rejects* invalid transitions, or just happens to never be
  asked to make one during the acceptance tests.
- "The `is_closed` boolean and the state enum can disagree — how do
  you stop that?" — the redundant-state design smell above, as a live
  question.

---

*More exercises get added here as they come up in real interviews —
this page is meant to grow, not stay a fixed list.*
