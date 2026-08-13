from datetime import timedelta

from django.db.models import Prefetch
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from rides.filters import RideFilter
from rides.models import Ride, RideEvent, User
from rides.ordering import StableRideOrderingFilter
from rides.pagination import RidePagination
from rides.permissions import HasAdminRole
from rides.serializers import (
    RideEventSerializer,
    RideListSerializer,
    RideSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (HasAdminRole,)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            user.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "This user cannot be deleted because they are assigned "
                        "to one or more rides."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.select_related("rider", "driver")
    serializer_class = RideSerializer
    permission_classes = (HasAdminRole,)
    pagination_class = RidePagination
    filter_backends = (DjangoFilterBackend, StableRideOrderingFilter)
    filterset_class = RideFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset

        cutoff = timezone.now() - timedelta(hours=24)
        recent_events = RideEvent.objects.filter(created_at__gte=cutoff).order_by(
            "created_at",
            "id_ride_event",
        )
        return queryset.prefetch_related(
            Prefetch(
                "ride_events",
                queryset=recent_events,
                to_attr="todays_ride_events",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return RideListSerializer
        return super().get_serializer_class()


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.select_related("ride")
    serializer_class = RideEventSerializer
    permission_classes = (HasAdminRole,)
