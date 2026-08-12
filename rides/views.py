from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import viewsets

from rides.models import Ride, RideEvent, User
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


class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.select_related("rider", "driver")
    serializer_class = RideSerializer
    permission_classes = (HasAdminRole,)

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
