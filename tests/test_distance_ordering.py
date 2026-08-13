from datetime import timedelta

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from rides.models import Ride, User
from rides.views import RideViewSet


@pytest.fixture
def distance_rides(db):
    admin = User.objects.create_user(
        username="distance-admin",
        email="distance-admin@example.com",
        password="Strong-test-password-123",
        role=User.Role.ADMIN,
    )
    rider = User.objects.create_user(
        username="distance-rider",
        email="distance-rider@example.com",
        password="Strong-test-password-123",
        role=User.Role.RIDER,
    )
    driver = User.objects.create_user(
        username="distance-driver",
        email="distance-driver@example.com",
        password="Strong-test-password-123",
        role=User.Role.DRIVER,
    )

    locations = [
        ("near", 14.6000, 120.9850),
        ("middle", 14.6091, 121.0223),
        ("far", 14.6760, 121.0437),
    ]
    rides = {}
    for index, (name, latitude, longitude) in enumerate(locations):
        rides[name] = Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=rider,
            driver=driver,
            pickup_latitude=latitude,
            pickup_longitude=longitude,
            dropoff_latitude=14.5547,
            dropoff_longitude=121.0244,
            pickup_time=timezone.now() + timedelta(hours=index),
        )

    client = APIClient()
    client.force_authenticate(admin)
    return client, rides


@pytest.mark.django_db
def test_ride_list_orders_by_distance_from_pickup_location(distance_rides):
    client, rides = distance_rides

    response = client.get(
        reverse("ride-list"),
        {
            "ordering": "distance",
            "pickup_latitude": "14.5995",
            "pickup_longitude": "120.9842",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert [ride["id_ride"] for ride in response.data["results"]] == [
        rides["near"].id_ride,
        rides["middle"].id_ride,
        rides["far"].id_ride,
    ]


@pytest.mark.django_db
def test_distance_ordering_works_with_filters_and_pagination(distance_rides):
    client, rides = distance_rides

    response = client.get(
        reverse("ride-list"),
        {
            "status": Ride.Status.EN_ROUTE,
            "ordering": "distance",
            "pickup_latitude": "14.5995",
            "pickup_longitude": "120.9842",
            "page_size": 2,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 3
    assert [ride["id_ride"] for ride in response.data["results"]] == [
        rides["near"].id_ride,
        rides["middle"].id_ride,
    ]
    assert response.data["next"] is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "error_field"),
    [
        ({"ordering": "distance"}, "ordering"),
        (
            {
                "ordering": "distance",
                "pickup_latitude": "not-a-number",
                "pickup_longitude": "120.9842",
            },
            "pickup_latitude",
        ),
        (
            {
                "ordering": "distance",
                "pickup_latitude": "91",
                "pickup_longitude": "120.9842",
            },
            "pickup_latitude",
        ),
        (
            {
                "ordering": "distance",
                "pickup_latitude": "14.5995",
                "pickup_longitude": "181",
            },
            "pickup_longitude",
        ),
        (
            {"ordering": "pickup_time", "pickup_latitude": "14.5995"},
            "ordering",
        ),
    ],
)
def test_distance_ordering_rejects_invalid_coordinates(distance_rides, query, error_field):
    client, _ = distance_rides

    response = client.get(reverse("ride-list"), query)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert error_field in response.data


@pytest.mark.django_db
def test_distance_ordering_uses_three_queries(
    distance_rides,
    django_assert_num_queries,
):
    client, _ = distance_rides

    with django_assert_num_queries(3):
        response = client.get(
            reverse("ride-list"),
            {
                "ordering": "distance",
                "pickup_latitude": "14.5995",
                "pickup_longitude": "120.9842",
            },
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_distance_ordering_has_knn_gist_index():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE tablename = 'ride' AND indexname = 'ride_pickup_earth_gist'
            """
        )
        index_definition = cursor.fetchone()

    assert index_definition is not None
    assert "USING gist" in index_definition[0]
    assert "ll_to_earth" in index_definition[0]


@pytest.mark.django_db
def test_postgresql_query_plan_uses_pickup_distance_index(distance_rides):
    _, rides = distance_rides
    assert rides

    request = Request(
        APIRequestFactory().get(
            reverse("ride-list"),
            {
                "ordering": "distance",
                "pickup_latitude": "14.5995",
                "pickup_longitude": "120.9842",
            },
        )
    )
    view = RideViewSet()
    view.action = "list"
    view.request = request
    queryset = view.filter_queryset(view.get_queryset())[:20]

    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        query_plan = queryset.explain(costs=False)

    assert "Index Scan using ride_pickup_earth_gist" in query_plan
