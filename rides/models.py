from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        if extra_fields.get("role") != "admin":
            raise ValueError("Superusers must have the admin role.")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        DRIVER = "driver", "Driver"
        RIDER = "rider", "Rider"

    id_user = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RIDER)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, blank=True)

    objects = UserManager()

    class Meta:
        db_table = "user"
        ordering = ("id_user",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["admin", "driver", "rider"]),
                name="user_valid_role",
            ),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.email or self.username


class Ride(models.Model):
    class Status(models.TextChoices):
        EN_ROUTE = "en-route", "En route"
        PICKUP = "pickup", "Pickup"
        DROPOFF = "dropoff", "Dropoff"

    id_ride = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    rider = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="rides_as_rider",
        db_column="id_rider",
    )
    driver = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="rides_as_driver",
        db_column="id_driver",
    )
    pickup_latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    pickup_longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    dropoff_latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    dropoff_longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride"
        ordering = ("id_ride",)
        indexes = [
            models.Index(fields=("status", "pickup_time"), name="ride_status_pickup_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["en-route", "pickup", "dropoff"]),
                name="ride_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(pickup_latitude__range=(-90, 90)),
                name="ride_valid_pickup_lat",
            ),
            models.CheckConstraint(
                condition=models.Q(pickup_longitude__range=(-180, 180)),
                name="ride_valid_pickup_lon",
            ),
            models.CheckConstraint(
                condition=models.Q(dropoff_latitude__range=(-90, 90)),
                name="ride_valid_dropoff_lat",
            ),
            models.CheckConstraint(
                condition=models.Q(dropoff_longitude__range=(-180, 180)),
                name="ride_valid_dropoff_lon",
            ),
        ]

    def __str__(self) -> str:
        return f"Ride {self.id_ride} ({self.status})"


class RideEvent(models.Model):
    id_ride_event = models.AutoField(primary_key=True)
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name="ride_events",
        db_column="id_ride",
        db_index=False,
    )
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "ride_event"
        ordering = ("created_at", "id_ride_event")
        indexes = [
            models.Index(fields=("ride", "created_at"), name="event_ride_created_idx"),
            models.Index(fields=("description",), name="event_description_idx"),
        ]

    def __str__(self) -> str:
        return f"Ride {self.ride_id}: {self.description}"
