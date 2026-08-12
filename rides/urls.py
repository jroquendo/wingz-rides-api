from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from rides.views import RideEventViewSet, RideViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("rides", RideViewSet)
router.register("ride-events", RideEventViewSet)

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token-auth"),
    *router.urls,
]
