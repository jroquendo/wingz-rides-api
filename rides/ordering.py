import math

from django.db.models import FloatField
from django.db.models.expressions import RawSQL
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter


class StableRideOrderingFilter(OrderingFilter):
    ordering_param = "ordering"
    pickup_latitude_param = "pickup_latitude"
    pickup_longitude_param = "pickup_longitude"

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering[0] != "distance":
            return queryset.order_by(*ordering)

        latitude, longitude = self.get_pickup_coordinates(request)
        distance_expression = RawSQL(
            (
                'll_to_earth("ride"."pickup_latitude", "ride"."pickup_longitude") '
                "<-> ll_to_earth(%s, %s)"
            ),
            (latitude, longitude),
            output_field=FloatField(),
        )
        return queryset.annotate(pickup_distance=distance_expression).order_by(
            "pickup_distance",
            "id_ride",
        )

    def get_ordering(self, request, queryset, view):
        requested = request.query_params.get(self.ordering_param)
        if not requested:
            self.reject_unused_coordinates(request)
            return ["id_ride"]

        fields = [field.strip() for field in requested.split(",") if field.strip()]
        invalid_fields = [
            field for field in fields if field not in {"pickup_time", "-pickup_time", "distance"}
        ]
        if invalid_fields or len(fields) != 1:
            raise ValidationError(
                {
                    self.ordering_param: (
                        "Ordering must be 'pickup_time', '-pickup_time', or 'distance'."
                    )
                }
            )

        requested_field = fields[0]
        if requested_field != "distance":
            self.reject_unused_coordinates(request)
        return [requested_field, "id_ride"]

    def get_pickup_coordinates(self, request):
        latitude_value = request.query_params.get(self.pickup_latitude_param)
        longitude_value = request.query_params.get(self.pickup_longitude_param)

        if latitude_value is None or longitude_value is None:
            raise ValidationError(
                {
                    self.ordering_param: (
                        "Distance ordering requires both pickup_latitude and pickup_longitude."
                    )
                }
            )

        latitude = self.parse_coordinate(latitude_value, self.pickup_latitude_param, -90, 90)
        longitude = self.parse_coordinate(
            longitude_value,
            self.pickup_longitude_param,
            -180,
            180,
        )
        return latitude, longitude

    @staticmethod
    def parse_coordinate(value, parameter, minimum, maximum):
        try:
            coordinate = float(value)
        except (TypeError, ValueError) as error:
            raise ValidationError({parameter: "A numeric value is required."}) from error

        if not math.isfinite(coordinate):
            raise ValidationError({parameter: "A finite numeric value is required."})
        if not minimum <= coordinate <= maximum:
            raise ValidationError({parameter: f"Value must be between {minimum} and {maximum}."})
        return coordinate

    def reject_unused_coordinates(self, request):
        supplied_coordinates = {
            parameter
            for parameter in (self.pickup_latitude_param, self.pickup_longitude_param)
            if parameter in request.query_params
        }
        if supplied_coordinates:
            raise ValidationError(
                {
                    self.ordering_param: (
                        "Pickup coordinates can only be used with ordering=distance."
                    )
                }
            )
