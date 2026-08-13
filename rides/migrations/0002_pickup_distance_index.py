from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0001_initial"),
    ]

    operations = [
        CreateExtension("cube"),
        CreateExtension("earthdistance"),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX ride_pickup_earth_gist "
                "ON ride USING gist "
                "(ll_to_earth(pickup_latitude, pickup_longitude))"
            ),
            reverse_sql="DROP INDEX IF EXISTS ride_pickup_earth_gist",
        ),
    ]
