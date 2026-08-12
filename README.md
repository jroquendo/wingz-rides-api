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

## Development checks

```bash
pytest
ruff check .
ruff format --check .
```

## Configuration

Local configuration is read from `.env`. The committed `.env.example` documents every required
setting. Never commit `.env` or real credentials.
