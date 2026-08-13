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

The endpoint uses page-number pagination with 20 rides per page. A client can request up to 100
rides using `page_size`. For example:

```text
/api/rides/?page=2&page_size=50
```

The list supports the following query parameters:

- `status`: exact Ride status, such as `pickup`
- `rider_email`: exact rider email
- `ordering`: `pickup_time`, `-pickup_time`, or `distance`

Filters and ordering can be combined in a single request:

```text
/api/rides/?status=pickup&rider_email=rider@example.com&ordering=-pickup_time
```

Pickup-time ordering always adds `id_ride` as a stable tie-breaker so records with matching pickup
times do not move between pages. Unsupported ordering values return a clear `400 Bad Request`.

Distance ordering requires a pickup GPS location:

```text
/api/rides/?ordering=distance&pickup_latitude=14.5995&pickup_longitude=120.9842
```

Both coordinates are required and must be within valid latitude and longitude ranges. Distance is
calculated entirely by PostgreSQL. A GiST expression index on
`ll_to_earth(pickup_latitude, pickup_longitude)` supports K-nearest-neighbor ordering through the
`cube` `<->` operator, so PostgreSQL can retrieve the closest rides without calculating and sorting
the full Ride table in application code. `id_ride` remains the stable tie-breaker.
The database account applying migrations must be allowed to install the `cube` and
`earthdistance` extensions.

The list queryset joins rider and driver data with `select_related` and loads the filtered event
collection with a single `Prefetch`. Old events are filtered by PostgreSQL and never loaded into
application memory. A paginated response uses three database queries: one count query, one query
for the current page of rides and related users, and one query for recent RideEvents.

## Development checks

```bash
pytest
ruff check .
ruff format --check .
```

The test suite covers model constraints, complete CRUD workflows, admin-role authorization,
authentication, filtering, both ordering modes, pagination boundaries, the exact 24-hour event
cutoff, stable ordering between pages, and fixed SQL-query budgets. PostgreSQL-specific tests also
verify that nearest-pickup ordering uses the GiST index in the generated query plan.

API validation rejects missing user passwords, invalid page sizes, and non-finite GPS coordinates.
Deleting a rider or driver assigned to a Ride returns `409 Conflict` instead of a server error.

## Configuration

Local configuration is read from `.env`. The committed `.env.example` documents every required
setting. Never commit `.env` or real credentials.
