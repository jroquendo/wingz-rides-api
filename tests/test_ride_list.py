from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from rides.models import Ride, RideEvent, User


@pytest.fixture
def ride_list_client(db):
    admin = User.objects.create_user(
        username="ride-list-admin",
        email="ride-list-admin@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )
    client = APIClient()
    client.force_authenticate(admin)
    return client


@pytest.fixture
def ride_with_events(db):
    rider = User.objects.create_user(
        username="ride-list-rider",
        email="ride-list-rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
        first_name="Ride",
        last_name="Rider",
        phone_number="+639171111111",
    )
    driver = User.objects.create_user(
        username="ride-list-driver",
        email="ride-list-driver@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
        first_name="Ride",
        last_name="Driver",
        phone_number="+639172222222",
    )
    ride = Ride.objects.create(
        status=Ride.Status.PICKUP,
        rider=rider,
        driver=driver,
        pickup_latitude=14.5995,
        pickup_longitude=120.9842,
        dropoff_latitude=14.5547,
        dropoff_longitude=121.0244,
        pickup_time=timezone.now(),
    )
    recent_event = RideEvent.objects.create(
        ride=ride,
        description="Status changed to pickup",
        created_at=timezone.now() - timedelta(hours=2),
    )
    old_event = RideEvent.objects.create(
        ride=ride,
        description="Old event",
        created_at=timezone.now() - timedelta(hours=25),
    )
    return ride, recent_event, old_event


@pytest.mark.django_db
def test_ride_list_includes_related_users_and_only_recent_events(
    ride_list_client,
    ride_with_events,
):
    ride, recent_event, old_event = ride_with_events

    response = ride_list_client.get(reverse("ride-list"))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    ride_data = response.data[0]
    assert ride_data["id_ride"] == ride.id_ride
    assert ride_data["id_rider"] == ride.rider_id
    assert ride_data["id_driver"] == ride.driver_id
    assert ride_data["rider"] == {
        "id_user": ride.rider_id,
        "role": User.Role.RIDER,
        "first_name": "Ride",
        "last_name": "Rider",
        "email": "ride-list-rider@example.com",
        "phone_number": "+639171111111",
    }
    assert ride_data["driver"] == {
        "id_user": ride.driver_id,
        "role": User.Role.DRIVER,
        "first_name": "Ride",
        "last_name": "Driver",
        "email": "ride-list-driver@example.com",
        "phone_number": "+639172222222",
    }
    assert [event["id_ride_event"] for event in ride_data["todays_ride_events"]] == [
        recent_event.id_ride_event
    ]
    assert old_event.id_ride_event not in {
        event["id_ride_event"] for event in ride_data["todays_ride_events"]
    }


@pytest.mark.django_db
def test_ride_list_uses_two_queries(
    ride_list_client,
    ride_with_events,
    django_assert_num_queries,
):
    ride = ride_with_events[0]
    second_ride = Ride.objects.create(
        status=Ride.Status.EN_ROUTE,
        rider=ride.rider,
        driver=ride.driver,
        pickup_latitude=14.6091,
        pickup_longitude=121.0223,
        dropoff_latitude=14.6760,
        dropoff_longitude=121.0437,
        pickup_time=timezone.now() + timedelta(hours=1),
    )
    RideEvent.objects.create(
        ride=second_ride,
        description="Driver assigned",
        created_at=timezone.now() - timedelta(minutes=30),
    )

    with django_assert_num_queries(2):
        response = ride_list_client.get(reverse("ride-list"))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_ride_detail_keeps_the_crud_response_shape(ride_list_client, ride_with_events):
    ride = ride_with_events[0]

    response = ride_list_client.get(reverse("ride-detail", args=(ride.id_ride,)))

    assert response.status_code == status.HTTP_200_OK
    assert "rider" not in response.data
    assert "driver" not in response.data
    assert "todays_ride_events" not in response.data
