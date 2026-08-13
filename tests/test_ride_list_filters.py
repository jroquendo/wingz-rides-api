from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from rides.models import Ride, User


@pytest.fixture
def filtered_ride_list(db):
    admin = User.objects.create_user(
        username="filter-admin",
        email="filter-admin@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )
    rider_one = User.objects.create_user(
        username="filter-rider-one",
        email="first.rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )
    rider_two = User.objects.create_user(
        username="filter-rider-two",
        email="second.rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )
    driver = User.objects.create_user(
        username="filter-driver",
        email="filter-driver@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
    )
    pickup_time = timezone.now() + timedelta(days=1)
    rides = [
        Ride.objects.create(
            status=Ride.Status.PICKUP,
            rider=rider_one,
            driver=driver,
            pickup_latitude=14.5995,
            pickup_longitude=120.9842,
            dropoff_latitude=14.5547,
            dropoff_longitude=121.0244,
            pickup_time=pickup_time,
        ),
        Ride.objects.create(
            status=Ride.Status.PICKUP,
            rider=rider_one,
            driver=driver,
            pickup_latitude=14.6091,
            pickup_longitude=121.0223,
            dropoff_latitude=14.6760,
            dropoff_longitude=121.0437,
            pickup_time=pickup_time,
        ),
        Ride.objects.create(
            status=Ride.Status.DROPOFF,
            rider=rider_two,
            driver=driver,
            pickup_latitude=14.6760,
            pickup_longitude=121.0437,
            dropoff_latitude=14.5995,
            dropoff_longitude=120.9842,
            pickup_time=pickup_time + timedelta(hours=2),
        ),
    ]
    client = APIClient()
    client.force_authenticate(admin)
    return client, rides


@pytest.mark.django_db
def test_ride_list_is_paginated(filtered_ride_list):
    client, rides = filtered_ride_list

    response = client.get(reverse("ride-list"), {"page_size": 2})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 2
    assert response.data["next"] is not None
    assert response.data["previous"] is None
    assert [ride["id_ride"] for ride in response.data["results"]] == [
        rides[0].id_ride,
        rides[1].id_ride,
    ]


@pytest.mark.django_db
def test_ride_list_filters_by_status(filtered_ride_list):
    client, rides = filtered_ride_list

    response = client.get(reverse("ride-list"), {"status": Ride.Status.DROPOFF})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id_ride"] == rides[2].id_ride


@pytest.mark.django_db
def test_ride_list_filters_by_rider_email(filtered_ride_list):
    client, rides = filtered_ride_list

    response = client.get(reverse("ride-list"), {"rider_email": "first.rider@example.com"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert [ride["id_ride"] for ride in response.data["results"]] == [
        rides[0].id_ride,
        rides[1].id_ride,
    ]


@pytest.mark.django_db
def test_ride_list_combines_filters_and_pickup_time_ordering(filtered_ride_list):
    client, rides = filtered_ride_list

    response = client.get(
        reverse("ride-list"),
        {
            "status": Ride.Status.PICKUP,
            "rider_email": "first.rider@example.com",
            "ordering": "-pickup_time",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert [ride["id_ride"] for ride in response.data["results"]] == [
        rides[0].id_ride,
        rides[1].id_ride,
    ]


@pytest.mark.django_db
def test_ride_list_orders_by_pickup_time(filtered_ride_list):
    client, rides = filtered_ride_list

    ascending = client.get(reverse("ride-list"), {"ordering": "pickup_time"})
    descending = client.get(reverse("ride-list"), {"ordering": "-pickup_time"})

    assert [ride["id_ride"] for ride in ascending.data["results"]] == [
        rides[0].id_ride,
        rides[1].id_ride,
        rides[2].id_ride,
    ]
    assert [ride["id_ride"] for ride in descending.data["results"]] == [
        rides[2].id_ride,
        rides[0].id_ride,
        rides[1].id_ride,
    ]


@pytest.mark.django_db
def test_ride_list_rejects_unsupported_ordering(filtered_ride_list):
    client, _ = filtered_ride_list

    response = client.get(reverse("ride-list"), {"ordering": "status"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["ordering"] == (
        "Ordering must be 'pickup_time', '-pickup_time', or 'distance'."
    )


@pytest.mark.django_db
def test_ride_list_rejects_unknown_status(filtered_ride_list):
    client, _ = filtered_ride_list

    response = client.get(reverse("ride-list"), {"status": "cancelled"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "status" in response.data
