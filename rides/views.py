from rest_framework import viewsets

from rides.models import Ride, RideEvent, User
from rides.permissions import HasAdminRole
from rides.serializers import RideEventSerializer, RideSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (HasAdminRole,)


class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.select_related("rider", "driver")
    serializer_class = RideSerializer
    permission_classes = (HasAdminRole,)


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.select_related("ride")
    serializer_class = RideEventSerializer
    permission_classes = (HasAdminRole,)
