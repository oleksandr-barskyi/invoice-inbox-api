import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _isolated(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.CELERY_TASK_ALWAYS_EAGER = True
    from config.celery import app

    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("anna", password="pass-12345")


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user("bob", password="pass-12345")


def client_for(u) -> APIClient:
    token, _ = Token.objects.get_or_create(user=u)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return c


@pytest.fixture
def api(user):
    return client_for(user)


@pytest.fixture
def other_api(other_user):
    return client_for(other_user)
