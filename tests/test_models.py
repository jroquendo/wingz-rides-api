from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from rides.models import Ride, RideEvent, User


@pytest.fixture
def rider(db):
    return User.objects.create_user(
        username="rider",
        email="rider@example.com",
        password="test-password",
        role=User.Role.RIDER,
    )


@pytest.fixture
def driver(db):
    return User.objects.create_user(
        username="driver",
        email="driver@example.com",
        password="test-password",
        role=User.Role.DRIVER,
    )


@pytest.fixture
def ride(rider, driver):
    return Ride.objects.create(
        status=Ride.Status.EN_ROUTE,
        rider=rider,
        driver=driver,
        pickup_latitude=14.5995,
        pickup_longitude=120.9842,
        dropoff_latitude=14.5547,
        dropoff_longitude=121.0244,
        pickup_time=timezone.now() + timedelta(hours=1),
    )


@pytest.mark.django_db
def test_user_uses_assessment_primary_key_and_role():
    user = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="test-password",
        role=User.Role.ADMIN,
    )

    assert user.id_user is not None
    assert user.role == "admin"
    assert str(user) == "admin@example.com"


@pytest.mark.django_db
def test_ride_links_rider_and_driver(ride, rider, driver):
    assert ride.rider == rider
    assert ride.driver == driver
    assert ride.status == "en-route"
    assert str(ride) == f"Ride {ride.id_ride} (en-route)"


@pytest.mark.django_db
def test_ride_rejects_coordinates_outside_valid_ranges(rider, driver):
    ride = Ride(
        status=Ride.Status.PICKUP,
        rider=rider,
        driver=driver,
        pickup_latitude=91,
        pickup_longitude=120,
        dropoff_latitude=14,
        dropoff_longitude=-181,
        pickup_time=timezone.now(),
    )

    with pytest.raises(ValidationError) as error:
        ride.full_clean()

    assert {"pickup_latitude", "dropoff_longitude"} <= set(error.value.message_dict)


@pytest.mark.django_db
def test_ride_event_is_available_from_ride(ride):
    event = RideEvent.objects.create(
        ride=ride,
        description="Status changed to pickup",
        created_at=timezone.now(),
    )

    assert list(ride.ride_events.all()) == [event]
    assert str(event) == f"Ride {ride.id_ride}: Status changed to pickup"


@pytest.mark.django_db
def test_users_with_rides_cannot_be_deleted(ride, rider):
    with pytest.raises(ProtectedError):
        rider.delete()


@pytest.mark.django_db
def test_deleting_a_ride_deletes_its_events(ride):
    RideEvent.objects.create(
        ride=ride,
        description="Status changed to dropoff",
        created_at=timezone.now(),
    )

    ride.delete()

    assert not RideEvent.objects.exists()
