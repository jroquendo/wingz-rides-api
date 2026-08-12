from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter


class StableRideOrderingFilter(OrderingFilter):
    ordering_param = "ordering"
    allowed_fields = {"pickup_time"}

    def get_ordering(self, request, queryset, view):
        requested = request.query_params.get(self.ordering_param)
        if not requested:
            return ["id_ride"]

        fields = [field.strip() for field in requested.split(",") if field.strip()]
        invalid_fields = [
            field for field in fields if field.removeprefix("-") not in self.allowed_fields
        ]
        if invalid_fields or len(fields) != 1:
            raise ValidationError(
                {self.ordering_param: ("Ordering must be either 'pickup_time' or '-pickup_time'.")}
            )

        requested_field = fields[0]
        return [requested_field, "id_ride"]
