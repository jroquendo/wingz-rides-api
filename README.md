# Wingz Rides API

A Django REST Framework API for the Wingz Software Engineer assessment.

## Current status

The assessment MVP is complete. It includes admin-protected CRUD endpoints, an optimized and
paginated ride list, status and rider-email filters, stable pickup-time and indexed distance
ordering, recent ride events, validation, and regression coverage. The bonus SQL report is included
below.

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

Create the first API administrator. The custom user manager automatically assigns the `admin` role
to superusers so the account can use the protected endpoints:

```bash
python manage.py createsuperuser
```

Start the development server:

```bash
python manage.py runserver
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

For example, request a token after creating the administrator:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"your-password"}'
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

## Design decisions and implementation notes

- PostgreSQL is used in development and tests because the distance-ordering implementation relies
  on its `cube` and `earthdistance` extensions. Keeping the same database engine in both places
  also makes the query-count and query-plan tests meaningful.
- Rider and driver are loaded with `select_related`, while only the previous 24 hours of events are
  loaded with a filtered `Prefetch`. This keeps the paginated list at three queries, including the
  pagination count, without materializing old events.
- Distance is ordered inside PostgreSQL through a GiST K-nearest-neighbor index. The main challenge
  was preserving efficient pagination for a very large Ride table; calculating distance in Python
  would require loading and sorting the complete result set first.
- All supported ordering modes include `id_ride` as a deterministic tie-breaker. This prevents
  records with equal pickup times or distances from moving between pages.
- Ride foreign keys use `PROTECT` so users referenced by historical rides cannot be deleted. The API
  converts that database protection into a clear `409 Conflict` response.

## Bonus SQL report

The report below finds the first pickup event for each ride and then the first dropoff event after
that pickup. It counts trips lasting more than one hour, grouped by pickup month and driver. Using a
dropoff that occurs after the selected pickup prevents an earlier or out-of-order event from
producing an invalid duration.

```sql
WITH trip_times AS (
    SELECT
        r.id_ride,
        r.id_driver,
        pickup.created_at AS picked_up_at,
        dropoff.created_at AS dropped_off_at
    FROM ride AS r
    JOIN LATERAL (
        SELECT re.created_at
        FROM ride_event AS re
        WHERE re.id_ride = r.id_ride
          AND re.description = 'Status changed to pickup'
        ORDER BY re.created_at, re.id_ride_event
        LIMIT 1
    ) AS pickup ON TRUE
    JOIN LATERAL (
        SELECT re.created_at
        FROM ride_event AS re
        WHERE re.id_ride = r.id_ride
          AND re.description = 'Status changed to dropoff'
          AND re.created_at > pickup.created_at
        ORDER BY re.created_at, re.id_ride_event
        LIMIT 1
    ) AS dropoff ON TRUE
)
SELECT
    TO_CHAR(DATE_TRUNC('month', trip.picked_up_at), 'YYYY-MM') AS month,
    CONCAT_WS(' ', NULLIF(driver.first_name, ''), NULLIF(driver.last_name, '')) AS driver,
    COUNT(*) AS "count_of_trips_over_1_hour"
FROM trip_times AS trip
JOIN "user" AS driver ON driver.id_user = trip.id_driver
WHERE trip.dropped_off_at - trip.picked_up_at > INTERVAL '1 hour'
GROUP BY
    DATE_TRUNC('month', trip.picked_up_at),
    driver.id_user,
    driver.first_name,
    driver.last_name
ORDER BY
    DATE_TRUNC('month', trip.picked_up_at),
    driver.first_name,
    driver.last_name,
    driver.id_user;
```

## Configuration

Local configuration is read from `.env`. The committed `.env.example` documents every required
setting. Never commit `.env` or real credentials.
