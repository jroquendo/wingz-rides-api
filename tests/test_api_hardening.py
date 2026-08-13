import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from rides.models import Ride, User


@pytest.fixture
def hardening_context(db):
    admin = User.objects.create_user(
        username="hardening-admin",
        email="hardening-admin@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )
    rider = User.objects.create_user(
        username="hardening-rider",
        email="hardening-rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )
    driver = User.objects.create_user(
        username="hardening-driver",
        email="hardening-driver@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
    )
    client = APIClient()
    client.force_authenticate(admin)
    return client, admin, rider, driver


@pytest.mark.django_db
def test_user_creation_requires_password(hardening_context):
    client, _, _, _ = hardening_context

    response = client.post(
        reverse("user-list"),
        {
            "username": "missing-password",
            "role": User.Role.RIDER,
            "email": "missing-password@example.com",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert str(response.data["password"][0]) == "This field is required."
    assert not User.objects.filter(username="missing-password").exists()


@pytest.mark.django_db
def test_password_validation_uses_submitted_user_fields(hardening_context):
    client, _, _, _ = hardening_context

    response = client.post(
        reverse("user-list"),
        {
            "username": "matching-password",
            "password": "matching-password",
            "role": User.Role.RIDER,
            "email": "matching-password@example.com",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.data


@pytest.mark.django_db
def test_deleting_user_assigned_to_ride_returns_conflict(hardening_context):
    client, _, rider, driver = hardening_context
    Ride.objects.create(
        status=Ride.Status.EN_ROUTE,
        rider=rider,
        driver=driver,
        pickup_latitude=14.5995,
        pickup_longitude=120.9842,
        dropoff_latitude=14.5547,
        dropoff_longitude=121.0244,
        pickup_time=timezone.now(),
    )

    response = client.delete(reverse("user-detail", args=(rider.id_user,)))

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "assigned to one or more rides" in response.data["detail"]
    assert User.objects.filter(id_user=rider.id_user).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("page_size", ["invalid", "0", "-1"])
def test_invalid_page_size_returns_validation_error(hardening_context, page_size):
    client, _, _, _ = hardening_context

    response = client.get(reverse("ride-list"), {"page_size": page_size})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["page_size"] == "A positive integer is required."


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("latitude", "longitude", "error_field"),
    [
        ("nan", "120.9842", "pickup_latitude"),
        ("inf", "120.9842", "pickup_latitude"),
        ("14.5995", "-inf", "pickup_longitude"),
    ],
)
def test_distance_ordering_rejects_non_finite_coordinates(
    hardening_context,
    latitude,
    longitude,
    error_field,
):
    client, _, _, _ = hardening_context

    response = client.get(
        reverse("ride-list"),
        {
            "ordering": "distance",
            "pickup_latitude": latitude,
            "pickup_longitude": longitude,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data[error_field] == "A finite numeric value is required."


@pytest.mark.django_db
def test_composite_indexes_replace_redundant_single_column_indexes():
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('ride', 'ride_event')
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

    assert "ride_status_pickup_idx" in indexes
    assert "event_ride_created_idx" in indexes
    assert "ride_status_96b64fae" not in indexes
    assert "ride_event_id_ride_93d5fca7" not in indexes
