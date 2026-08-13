from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class RidePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        value = request.query_params.get(self.page_size_query_param)
        if value is None:
            return self.page_size

        try:
            page_size = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                {self.page_size_query_param: "A positive integer is required."}
            ) from error

        if page_size <= 0:
            raise ValidationError({self.page_size_query_param: "A positive integer is required."})
        return min(page_size, self.max_page_size)
