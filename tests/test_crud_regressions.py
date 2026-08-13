from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from rides.models import Ride, RideEvent, User


@pytest.fixture
def regression_users(db):
    admin = User.objects.create_user(
        username="regression-admin",
        email="regression-admin@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )
    rider = User.objects.create_user(
        username="regression-rider",
        email="regression-rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )
    driver = User.objects.create_user(
        username="regression-driver",
        email="regression-driver@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
    )
    return admin, rider, driver


@pytest.fixture
def regression_client(regression_users):
    client = APIClient()
    client.force_authenticate(regression_users[0])
    return client


@pytest.fixture
def regression_ride(regression_users):
    _, rider, driver = regression_users
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
def test_admin_can_complete_user_crud_workflow(regression_client):
    create_response = regression_client.post(
        reverse("user-list"),
        {
            "username": "crud-user",
            "password": "Strong-create-password-123",
            "role": User.Role.RIDER,
            "first_name": "Original",
            "last_name": "Name",
            "email": "crud-user@example.com",
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED

    user_id = create_response.data["id_user"]
    detail_url = reverse("user-detail", args=(user_id,))
    retrieve_response = regression_client.get(detail_url)
    assert retrieve_response.status_code == status.HTTP_200_OK
    assert retrieve_response.data["email"] == "crud-user@example.com"

    update_response = regression_client.patch(
        detail_url,
        {
            "first_name": "Updated",
            "password": "Strong-updated-password-123",
        },
        format="json",
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.data["first_name"] == "Updated"
    assert "password" not in update_response.data
    assert User.objects.get(id_user=user_id).check_password("Strong-updated-password-123")

    list_response = regression_client.get(reverse("user-list"))
    assert list_response.status_code == status.HTTP_200_OK
    assert user_id in {user["id_user"] for user in list_response.data}

    delete_response = regression_client.delete(detail_url)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(id_user=user_id).exists()


@pytest.mark.django_db
def test_admin_can_complete_ride_event_crud_workflow(regression_client, regression_ride):
    create_response = regression_client.post(
        reverse("rideevent-list"),
        {
            "id_ride": regression_ride.id_ride,
            "description": "Driver assigned",
            "created_at": timezone.now().isoformat(),
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED

    event_id = create_response.data["id_ride_event"]
    detail_url = reverse("rideevent-detail", args=(event_id,))
    retrieve_response = regression_client.get(detail_url)
    assert retrieve_response.status_code == status.HTTP_200_OK
    assert retrieve_response.data["id_ride"] == regression_ride.id_ride

    update_response = regression_client.patch(
        detail_url,
        {"description": "Status changed to pickup"},
        format="json",
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.data["description"] == "Status changed to pickup"

    delete_response = regression_client.delete(detail_url)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert not RideEvent.objects.filter(id_ride_event=event_id).exists()


@pytest.mark.django_db
def test_admin_can_replace_a_ride_with_put(regression_client, regression_ride, regression_users):
    _, rider, driver = regression_users

    response = regression_client.put(
        reverse("ride-detail", args=(regression_ride.id_ride,)),
        {
            "status": Ride.Status.DROPOFF,
            "id_rider": rider.id_user,
            "id_driver": driver.id_user,
            "pickup_latitude": 14.6091,
            "pickup_longitude": 121.0223,
            "dropoff_latitude": 14.6760,
            "dropoff_longitude": 121.0437,
            "pickup_time": (timezone.now() + timedelta(hours=2)).isoformat(),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    regression_ride.refresh_from_db()
    assert regression_ride.status == Ride.Status.DROPOFF
    assert regression_ride.pickup_latitude == 14.6091


@pytest.mark.django_db
def test_duplicate_user_email_returns_validation_error(regression_client, regression_users):
    _, rider, _ = regression_users

    response = regression_client.post(
        reverse("user-list"),
        {
            "username": "duplicate-email",
            "role": User.Role.RIDER,
            "email": rider.email,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


@pytest.mark.django_db
@pytest.mark.parametrize("authenticated", [False, True])
def test_unauthorized_users_cannot_modify_resources(
    regression_users,
    regression_ride,
    authenticated,
):
    _, rider, _ = regression_users
    event = RideEvent.objects.create(
        ride=regression_ride,
        description="Driver assigned",
        created_at=timezone.now(),
    )
    client = APIClient()
    if authenticated:
        client.force_authenticate(rider)
    expected_status = status.HTTP_403_FORBIDDEN if authenticated else status.HTTP_401_UNAUTHORIZED

    requests = (
        client.post(reverse("user-list"), {}, format="json"),
        client.patch(
            reverse("ride-detail", args=(regression_ride.id_ride,)),
            {"status": Ride.Status.PICKUP},
            format="json",
        ),
        client.delete(reverse("rideevent-detail", args=(event.id_ride_event,))),
    )

    assert {response.status_code for response in requests} == {expected_status}
    regression_ride.refresh_from_db()
    assert regression_ride.status == Ride.Status.EN_ROUTE
    assert RideEvent.objects.filter(id_ride_event=event.id_ride_event).exists()


@pytest.mark.django_db
def test_missing_resources_return_not_found(regression_client):
    responses = (
        regression_client.get(reverse("user-detail", args=(999999,))),
        regression_client.get(reverse("ride-detail", args=(999999,))),
        regression_client.get(reverse("rideevent-detail", args=(999999,))),
    )

    assert {response.status_code for response in responses} == {status.HTTP_404_NOT_FOUND}
