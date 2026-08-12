from django.conf import settings
from django.core.management import call_command


def test_project_configuration_passes_django_checks():
    call_command("check")


def test_required_apps_are_installed():
    assert {"rides", "rest_framework", "django_filters"} <= set(settings.INSTALLED_APPS)
