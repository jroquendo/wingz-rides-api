# Wingz Rides API

A Django REST Framework API for the Wingz Software Engineer assessment.

## Phase 1 status

The repository currently contains the project foundation: Django and Django REST Framework,
environment-based settings, PostgreSQL through Docker Compose, and the initial quality tooling.
The assessment models and API endpoints will be added in subsequent phases.

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

Database migrations will be introduced with the custom user and ride-domain models in Phase 2.

## Development checks

```bash
pytest
ruff check .
ruff format --check .
```

## Configuration

Local configuration is read from `.env`. The committed `.env.example` documents every required
setting. Never commit `.env` or real credentials.
