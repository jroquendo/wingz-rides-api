from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from rides.models import Ride, RideEvent, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin-api",
        email="admin-api@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def non_admin_user(db):
    return User.objects.create_user(
        username="rider-api",
        email="rider-api@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )


@pytest.fixture
def driver_user(db):
    return User.objects.create_user(
        username="driver-api",
        email="driver-api@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(admin_user)
    return api_client


@pytest.mark.django_db
@pytest.mark.parametrize("route_name", ["user-list", "ride-list", "rideevent-list"])
def test_anonymous_users_cannot_access_crud_endpoints(api_client, route_name):
    response = api_client.get(reverse(route_name))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize("route_name", ["user-list", "ride-list", "rideevent-list"])
def test_non_admin_users_cannot_access_crud_endpoints(api_client, non_admin_user, route_name):
    api_client.force_authenticate(non_admin_user)

    response = api_client.get(reverse(route_name))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["detail"] == "Only users with the admin role can access this endpoint."


@pytest.mark.django_db
def test_admin_can_create_user_and_password_is_hashed(admin_client):
    response = admin_client.post(
        reverse("user-list"),
        {
            "username": "new-driver",
            "password": "Strong-driver-password-123",
            "role": User.Role.DRIVER,
            "first_name": "New",
            "last_name": "Driver",
            "email": "new-driver@example.com",
            "phone_number": "+639171234567",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert "password" not in response.data
    assert User.objects.get(id_user=response.data["id_user"]).check_password(
        "Strong-driver-password-123"
    )


@pytest.mark.django_db
def test_admin_can_manage_a_ride(admin_client, non_admin_user, driver_user):
    create_response = admin_client.post(
        reverse("ride-list"),
        {
            "status": Ride.Status.EN_ROUTE,
            "id_rider": non_admin_user.id_user,
            "id_driver": driver_user.id_user,
            "pickup_latitude": 14.5995,
            "pickup_longitude": 120.9842,
            "dropoff_latitude": 14.5547,
            "dropoff_longitude": 121.0244,
            "pickup_time": (timezone.now() + timedelta(hours=1)).isoformat(),
        },
        format="json",
    )

    assert create_response.status_code == status.HTTP_201_CREATED
    ride_url = reverse("ride-detail", args=(create_response.data["id_ride"],))

    update_response = admin_client.patch(
        ride_url,
        {"status": Ride.Status.PICKUP},
        format="json",
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.data["status"] == Ride.Status.PICKUP

    delete_response = admin_client.delete(ride_url)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert not Ride.objects.exists()


@pytest.mark.django_db
def test_ride_requires_users_with_matching_roles(admin_client, admin_user, non_admin_user):
    response = admin_client.post(
        reverse("ride-list"),
        {
            "status": Ride.Status.EN_ROUTE,
            "id_rider": admin_user.id_user,
            "id_driver": non_admin_user.id_user,
            "pickup_latitude": 14.5995,
            "pickup_longitude": 120.9842,
            "dropoff_latitude": 14.5547,
            "dropoff_longitude": 121.0244,
            "pickup_time": timezone.now().isoformat(),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "id_rider" in response.data
    assert "id_driver" in response.data


@pytest.mark.django_db
def test_admin_can_create_and_list_ride_event(
    admin_client,
    non_admin_user,
    driver_user,
):
    ride = Ride.objects.create(
        status=Ride.Status.PICKUP,
        rider=non_admin_user,
        driver=driver_user,
        pickup_latitude=14.5995,
        pickup_longitude=120.9842,
        dropoff_latitude=14.5547,
        dropoff_longitude=121.0244,
        pickup_time=timezone.now(),
    )

    create_response = admin_client.post(
        reverse("rideevent-list"),
        {
            "id_ride": ride.id_ride,
            "description": "Status changed to pickup",
            "created_at": timezone.now().isoformat(),
        },
        format="json",
    )

    assert create_response.status_code == status.HTTP_201_CREATED
    assert RideEvent.objects.filter(ride=ride).count() == 1

    list_response = admin_client.get(reverse("rideevent-list"))
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data[0]["id_ride"] == ride.id_ride


@pytest.mark.django_db
def test_user_can_exchange_credentials_for_token(api_client, admin_user):
    response = api_client.post(
        reverse("api-token-auth"),
        {"username": admin_user.username, "password": "Strong-test-password-123"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["token"]
