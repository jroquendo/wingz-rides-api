from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from rides.models import Ride, RideEvent, User


@pytest.fixture
def list_regression_context(db):
    admin = User.objects.create_user(
        username="list-regression-admin",
        email="list-regression-admin@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )
    rider = User.objects.create_user(
        username="list-regression-rider",
        email="list-regression-rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )
    driver = User.objects.create_user(
        username="list-regression-driver",
        email="list-regression-driver@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
    )
    client = APIClient()
    client.force_authenticate(admin)
    return client, rider, driver


def build_rides(rider, driver, count, pickup_time, **overrides):
    defaults = {
        "status": Ride.Status.EN_ROUTE,
        "pickup_latitude": 14.5995,
        "pickup_longitude": 120.9842,
        "dropoff_latitude": 14.5547,
        "dropoff_longitude": 121.0244,
    }
    defaults.update(overrides)
    return Ride.objects.bulk_create(
        [
            Ride(
                rider=rider,
                driver=driver,
                pickup_time=pickup_time,
                **defaults,
            )
            for _ in range(count)
        ]
    )


@pytest.mark.django_db
def test_empty_ride_list_returns_empty_page(list_regression_context):
    client, _, _ = list_regression_context

    response = client.get(reverse("ride-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


@pytest.mark.django_db
def test_recent_event_cutoff_is_inclusive(list_regression_context):
    client, rider, driver = list_regression_context
    fixed_now = timezone.now()
    ride = build_rides(rider, driver, 1, fixed_now)[0]
    cutoff_event = RideEvent.objects.create(
        ride=ride,
        description="Exactly at cutoff",
        created_at=fixed_now - timedelta(hours=24),
    )
    RideEvent.objects.create(
        ride=ride,
        description="Before cutoff",
        created_at=fixed_now - timedelta(hours=24, microseconds=1),
    )

    with patch("rides.views.timezone.now", return_value=fixed_now):
        response = client.get(reverse("ride-list"))

    events = response.data["results"][0]["todays_ride_events"]
    assert [event["id_ride_event"] for event in events] == [cutoff_event.id_ride_event]


@pytest.mark.django_db
def test_pickup_time_ordering_is_stable_between_pages(list_regression_context):
    client, rider, driver = list_regression_context
    rides = build_rides(rider, driver, 5, timezone.now() + timedelta(days=1))

    first_page = client.get(
        reverse("ride-list"),
        {"ordering": "pickup_time", "page_size": 2, "page": 1},
    )
    second_page = client.get(
        reverse("ride-list"),
        {"ordering": "pickup_time", "page_size": 2, "page": 2},
    )

    assert [ride["id_ride"] for ride in first_page.data["results"]] == [
        rides[0].id_ride,
        rides[1].id_ride,
    ]
    assert [ride["id_ride"] for ride in second_page.data["results"]] == [
        rides[2].id_ride,
        rides[3].id_ride,
    ]
    assert not (
        {ride["id_ride"] for ride in first_page.data["results"]}
        & {ride["id_ride"] for ride in second_page.data["results"]}
    )


@pytest.mark.django_db
def test_distance_ordering_is_stable_between_pages(list_regression_context):
    client, rider, driver = list_regression_context
    rides = build_rides(rider, driver, 5, timezone.now() + timedelta(days=1))
    query = {
        "ordering": "distance",
        "pickup_latitude": "14.5995",
        "pickup_longitude": "120.9842",
        "page_size": 2,
    }

    first_page = client.get(reverse("ride-list"), {**query, "page": 1})
    second_page = client.get(reverse("ride-list"), {**query, "page": 2})

    assert [ride["id_ride"] for ride in first_page.data["results"]] == [
        rides[0].id_ride,
        rides[1].id_ride,
    ]
    assert [ride["id_ride"] for ride in second_page.data["results"]] == [
        rides[2].id_ride,
        rides[3].id_ride,
    ]


@pytest.mark.django_db
def test_page_size_is_capped_at_one_hundred(list_regression_context):
    client, rider, driver = list_regression_context
    build_rides(rider, driver, 101, timezone.now() + timedelta(days=1))

    response = client.get(reverse("ride-list"), {"page_size": 1000})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 101
    assert len(response.data["results"]) == 100
    assert response.data["next"] is not None


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["invalid", "999"])
def test_invalid_or_out_of_range_page_returns_not_found(list_regression_context, page):
    client, rider, driver = list_regression_context
    build_rides(rider, driver, 1, timezone.now())

    response = client.get(reverse("ride-list"), {"page": page})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_query_count_does_not_grow_with_page_size(
    list_regression_context,
    django_assert_num_queries,
):
    client, rider, driver = list_regression_context
    rides = build_rides(rider, driver, 25, timezone.now())
    RideEvent.objects.bulk_create(
        [
            RideEvent(
                ride=ride,
                description="Driver assigned",
                created_at=timezone.now(),
            )
            for ride in rides
        ]
    )

    with django_assert_num_queries(3):
        response = client.get(reverse("ride-list"), {"page_size": 25})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 25
