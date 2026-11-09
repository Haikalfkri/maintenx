import pytest

LOGIN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"

pytestmark = pytest.mark.django_db


def login(client, email, password):
    return client.post(LOGIN, {"email": email, "password": password}, format="json")


def test_login_success_returns_tokens(anon_client, manager_a, password):
    response = login(anon_client, manager_a.email, password)
    assert response.status_code == 200
    assert set(response.data) == {"access", "refresh"}


def test_login_email_is_case_insensitive(anon_client, manager_a, password):
    response = login(anon_client, manager_a.email.upper(), password)
    assert response.status_code == 200


def test_login_wrong_password(anon_client, manager_a):
    assert login(anon_client, manager_a.email, "wrong-password").status_code == 401


def test_login_unknown_email(anon_client):
    assert login(anon_client, "nobody@example.com", "whatever").status_code == 401


def test_inactive_user_cannot_login(anon_client, manager_a, password):
    manager_a.is_active = False
    manager_a.save()
    assert login(anon_client, manager_a.email, password).status_code == 401


def test_inactive_organization_cannot_login(anon_client, manager_a, org_a, password):
    org_a.is_active = False
    org_a.save()
    assert login(anon_client, manager_a.email, password).status_code == 401


def test_superuser_without_organization_cannot_use_api(anon_client, django_user_model, password):
    django_user_model.objects.create_superuser("root@example.com", password)
    assert login(anon_client, "root@example.com", password).status_code == 401


def test_me_requires_authentication(anon_client):
    assert anon_client.get(ME).status_code == 401


def test_me_returns_profile_with_organization(anon_client, manager_a, org_a, password):
    tokens = login(anon_client, manager_a.email, password).data
    anon_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = anon_client.get(ME)
    assert response.status_code == 200
    assert response.data["email"] == manager_a.email
    assert response.data["role"] == "MANAGER"
    assert response.data["organization"]["name"] == org_a.name
    assert "password" not in response.data


def test_refresh_rotates_and_blacklists_old_token(anon_client, manager_a, password):
    old_refresh = login(anon_client, manager_a.email, password).data["refresh"]

    first = anon_client.post(REFRESH, {"refresh": old_refresh}, format="json")
    assert first.status_code == 200
    assert first.data["refresh"] != old_refresh

    # token lama sudah di-blacklist setelah rotasi
    reuse = anon_client.post(REFRESH, {"refresh": old_refresh}, format="json")
    assert reuse.status_code == 401


def test_logout_blacklists_refresh_token(anon_client, manager_a, password):
    refresh = login(anon_client, manager_a.email, password).data["refresh"]

    assert anon_client.post(LOGOUT, {"refresh": refresh}, format="json").status_code == 204
    assert anon_client.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401


def test_logout_with_invalid_token(anon_client):
    response = anon_client.post(LOGOUT, {"refresh": "not-a-token"}, format="json")
    assert response.status_code == 400


def test_logout_requires_refresh_field(anon_client):
    assert anon_client.post(LOGOUT, {}, format="json").status_code == 400


def test_deactivated_user_cannot_refresh(anon_client, manager_a, password):
    refresh = login(anon_client, manager_a.email, password).data["refresh"]
    manager_a.is_active = False
    manager_a.save()
    assert anon_client.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401


def test_deactivated_user_access_token_is_rejected(anon_client, manager_a, password):
    access = login(anon_client, manager_a.email, password).data["access"]
    manager_a.is_active = False
    manager_a.save()
    anon_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert anon_client.get(ME).status_code == 401