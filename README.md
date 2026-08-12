# Wingz Rides API

A Django REST Framework API for the Wingz Software Engineer assessment.

## Current status

The repository currently contains the project foundation: Django and Django REST Framework,
environment-based settings, PostgreSQL through Docker Compose, and the initial quality tooling.
The custom user, ride, and ride-event models are also in place. API endpoints will be added in
subsequent phases.

## Prerequisites

- Python 3.12 or newer
- Docker with Docker Compose
- Git

## Local setup

```bash
git clone git@github.com:jroquendo/wingz-rides-api.git
cd wingz-rides-api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
cp .env.example .env
docker compose up -d db
python manage.py check
```

Apply the database migrations after starting PostgreSQL:

```bash
python manage.py migrate
```

## Data model

- `User` extends Django authentication with the required role and phone number fields.
- `Ride` links a rider and driver and stores status, pickup/dropoff coordinates, and pickup time.
- `RideEvent` records timestamped events for a ride.

Foreign keys use Django-friendly attributes while retaining the assessment's database column
names: `id_rider`, `id_driver`, and `id_ride`.

## API access

The CRUD API is available under `/api/`:

- `/api/users/`
- `/api/rides/`
- `/api/ride-events/`

All three resources support list, retrieve, create, update, and delete operations. Only an
authenticated user whose `role` is `admin` may access them. Obtain a token with a username and
password at `/api/auth/token/`, then send it with requests:

```text
Authorization: Token <token>
```

### Ride list response

Each item returned by `/api/rides/` includes:

- `id_rider` and `id_driver` for stable relationship identifiers
- nested `rider` and `driver` details
- `todays_ride_events`, containing only events created during the previous 24 hours

The list queryset joins rider and driver data with `select_related` and loads the filtered event
collection with a single `Prefetch`. Old events are filtered by PostgreSQL and never loaded into
application memory. The unpaginated endpoint therefore uses two database queries regardless of
the number of rides returned.

## Development checks

```bash
pytest
ruff check .
ruff format --check .
```

## Configuration

Local configuration is read from `.env`. The committed `.env.example` documents every required
setting. Never commit `.env` or real credentials.
