from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from rides.models import Ride, RideEvent, User


class RelatedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id_user",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone_number",
        )


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        required=False,
        write_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id_user",
            "username",
            "password",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
        )
        read_only_fields = ("id_user",)

    def validate(self, attrs):
        password = attrs.get("password")
        if self.instance is None and not password:
            raise serializers.ValidationError({"password": "This field is required."})

        if password:
            password_user = User(
                **{
                    field: attrs.get(field, getattr(self.instance, field, ""))
                    for field in ("username", "first_name", "last_name", "email")
                }
            )
            try:
                django_validate_password(password, user=password_user)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=("password",))
        return user


class RideSerializer(serializers.ModelSerializer):
    id_rider = serializers.PrimaryKeyRelatedField(
        source="rider",
        queryset=User.objects.all(),
    )
    id_driver = serializers.PrimaryKeyRelatedField(
        source="driver",
        queryset=User.objects.all(),
    )

    class Meta:
        model = Ride
        fields = (
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
        )
        read_only_fields = ("id_ride",)

    def validate_id_rider(self, user):
        if user.role != User.Role.RIDER:
            raise serializers.ValidationError("The selected user must have the rider role.")
        return user

    def validate_id_driver(self, user):
        if user.role != User.Role.DRIVER:
            raise serializers.ValidationError("The selected user must have the driver role.")
        return user

    def validate(self, attrs):
        rider = attrs.get("rider", getattr(self.instance, "rider", None))
        driver = attrs.get("driver", getattr(self.instance, "driver", None))
        if rider == driver:
            raise serializers.ValidationError("The rider and driver must be different users.")
        return attrs


class RideEventSerializer(serializers.ModelSerializer):
    id_ride = serializers.PrimaryKeyRelatedField(
        source="ride",
        queryset=Ride.objects.all(),
    )

    class Meta:
        model = RideEvent
        fields = ("id_ride_event", "id_ride", "description", "created_at")
        read_only_fields = ("id_ride_event",)


class RideListSerializer(RideSerializer):
    rider = RelatedUserSerializer(read_only=True)
    driver = RelatedUserSerializer(read_only=True)
    todays_ride_events = RideEventSerializer(many=True, read_only=True)

    class Meta(RideSerializer.Meta):
        fields = RideSerializer.Meta.fields + (
            "rider",
            "driver",
            "todays_ride_events",
        )
