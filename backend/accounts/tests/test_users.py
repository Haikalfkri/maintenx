import pytest

from accounts.models import User

USERS = "/api/v1/users/"
TECHNICIANS = "/api/v1/users/technicians/"

pytestmark = pytest.mark.django_db


def new_user_payload(**overrides):
    payload = {
        "email": "new.user@example.com",
        "password": "Str0ng-Passw0rd!",
        "first_name": "New",
        "last_name": "User",
        "role": "TECHNICIAN",
    }
    payload.update(overrides)
    return payload


# --- permissions ------------------------------------------------------------

def test_users_requires_authentication(anon_client):
    assert anon_client.get(USERS).status_code == 401


@pytest.mark.parametrize("role_fixture", ["manager_a", "tech_a"])
def test_non_admin_cannot_access_users(request, auth_client, role_fixture):
    client = auth_client(request.getfixturevalue(role_fixture))
    assert client.get(USERS).status_code == 403
    assert client.post(USERS, new_user_payload(), format="json").status_code == 403


# --- list / retrieve ----------------------------------------------------------

def test_admin_can_list_users_with_pagination(auth_client, admin_a, manager_a, tech_a):
    response = auth_client(admin_a).get(USERS)
    assert response.status_code == 200
    assert response.data["count"] == 3
    assert {"count", "next", "previous", "results"} <= set(response.data)


def test_list_never_exposes_password(auth_client, admin_a):
    result = auth_client(admin_a).get(USERS).data["results"][0]
    assert "password" not in result


def test_admin_can_filter_by_role(auth_client, admin_a, manager_a, tech_a):
    response = auth_client(admin_a).get(USERS, {"role": "TECHNICIAN"})
    assert [u["email"] for u in response.data["results"]] == [tech_a.email]


def test_admin_can_search(auth_client, admin_a, tech_a):
    response = auth_client(admin_a).get(USERS, {"search": "Tono"})
    assert response.data["count"] == 1


def test_ordering_by_unlisted_field_is_ignored(auth_client, admin_a, tech_a):
    # 'password' bukan field yang diizinkan untuk ordering, jadi tidak boleh error 500
    assert auth_client(admin_a).get(USERS, {"ordering": "password"}).status_code == 200


# --- create -------------------------------------------------------------------

def test_admin_creates_user_in_own_organization(auth_client, admin_a, org_a):
    response = auth_client(admin_a).post(USERS, new_user_payload(), format="json")
    assert response.status_code == 201
    assert "password" not in response.data
    created = User.objects.get(email="new.user@example.com")
    assert created.organization == org_a
    assert created.check_password("Str0ng-Passw0rd!")  # tersimpan sebagai hash
    assert created.password != "Str0ng-Passw0rd!"


def test_create_ignores_organization_from_payload(auth_client, admin_a, org_a, org_b):
    payload = new_user_payload(organization=str(org_b.id))
    response = auth_client(admin_a).post(USERS, payload, format="json")
    assert response.status_code == 201
    assert User.objects.get(email="new.user@example.com").organization == org_a


def test_create_rejects_duplicate_email_case_insensitive(auth_client, admin_a, tech_a):
    payload = new_user_payload(email=tech_a.email.upper())
    assert auth_client(admin_a).post(USERS, payload, format="json").status_code == 400


def test_create_rejects_weak_password(auth_client, admin_a):
    payload = new_user_payload(password="12345678")
    response = auth_client(admin_a).post(USERS, payload, format="json")
    assert response.status_code == 400
    assert "password" in response.data


def test_create_rejects_invalid_role(auth_client, admin_a):
    payload = new_user_payload(role="SUPERBOSS")
    assert auth_client(admin_a).post(USERS, payload, format="json").status_code == 400


# --- update -------------------------------------------------------------------

def test_admin_can_update_user(auth_client, admin_a, tech_a):
    response = auth_client(admin_a).patch(
        f"{USERS}{tech_a.id}/", {"role": "MANAGER", "first_name": "Promoted"}, format="json"
    )
    assert response.status_code == 200
    tech_a.refresh_from_db()
    assert tech_a.role == "MANAGER"
    assert tech_a.first_name == "Promoted"


def test_admin_can_deactivate_user(auth_client, admin_a, tech_a):
    response = auth_client(admin_a).patch(
        f"{USERS}{tech_a.id}/", {"is_active": False}, format="json"
    )
    assert response.status_code == 200
    tech_a.refresh_from_db()
    assert tech_a.is_active is False


def test_email_cannot_be_changed_via_patch(auth_client, admin_a, tech_a):
    original = tech_a.email
    auth_client(admin_a).patch(f"{USERS}{tech_a.id}/", {"email": "x@example.com"}, format="json")
    tech_a.refresh_from_db()
    assert tech_a.email == original


def test_admin_cannot_deactivate_self(auth_client, admin_a):
    response = auth_client(admin_a).patch(
        f"{USERS}{admin_a.id}/", {"is_active": False}, format="json"
    )
    assert response.status_code == 400


def test_admin_cannot_demote_self(auth_client, admin_a):
    response = auth_client(admin_a).patch(
        f"{USERS}{admin_a.id}/", {"role": "TECHNICIAN"}, format="json"
    )
    assert response.status_code == 400


def test_put_and_delete_are_not_allowed(auth_client, admin_a, tech_a):
    client = auth_client(admin_a)
    assert client.put(f"{USERS}{tech_a.id}/", {}, format="json").status_code == 405
    assert client.delete(f"{USERS}{tech_a.id}/").status_code == 405


# --- technicians dropdown ---------------------------------------------------

@pytest.mark.parametrize("role_fixture", ["admin_a", "manager_a"])
def test_admin_and_manager_can_list_technicians(request, auth_client, role_fixture, tech_a):
    response = auth_client(request.getfixturevalue(role_fixture)).get(TECHNICIANS)
    assert response.status_code == 200
    assert response.data == [
        {"id": str(tech_a.id), "first_name": "Tono", "last_name": "Teknisi"}
    ]


def test_technician_cannot_list_technicians(auth_client, tech_a):
    assert auth_client(tech_a).get(TECHNICIANS).status_code == 403


def test_technicians_list_only_active_technicians(auth_client, manager_a, tech_a, make_user, org_a):
    inactive = make_user(org_a, "TECHNICIAN", is_active=False)
    ids = [t["id"] for t in auth_client(manager_a).get(TECHNICIANS).data]
    assert str(tech_a.id) in ids
    assert str(inactive.id) not in ids
    assert str(manager_a.id) not in ids  # hanya role TECHNICIAN