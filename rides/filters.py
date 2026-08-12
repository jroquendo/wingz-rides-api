import django_filters

from rides.models import Ride


class RideFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Ride.Status.choices)
    rider_email = django_filters.CharFilter(
        field_name="rider__email",
        lookup_expr="exact",
    )

    class Meta:
        model = Ride
        fields = ("status", "rider_email")
