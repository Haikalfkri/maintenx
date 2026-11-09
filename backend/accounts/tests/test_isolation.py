"""Isolasi data antar organisasi: user Org A tidak boleh menyentuh data Org B."""
import pytest

USERS = "/api/v1/users/"
TECHNICIANS = "/api/v1/users/technicians/"

pytestmark = pytest.mark.django_db


def test_list_excludes_other_organization(auth_client, admin_a, tech_a, admin_b, tech_b):
    emails = {u["email"] for u in auth_client(admin_a).get(USERS).data["results"]}
    assert emails == {admin_a.email, tech_a.email}
    assert admin_b.email not in emails
    assert tech_b.email not in emails


def test_cannot_retrieve_user_of_other_organization(auth_client, admin_a, tech_b):
    assert auth_client(admin_a).get(f"{USERS}{tech_b.id}/").status_code == 404


def test_cannot_update_user_of_other_organization(auth_client, admin_a, tech_b):
    response = auth_client(admin_a).patch(
        f"{USERS}{tech_b.id}/", {"role": "ADMIN", "is_active": False}, format="json"
    )
    assert response.status_code == 404
    tech_b.refresh_from_db()
    assert tech_b.role == "TECHNICIAN"
    assert tech_b.is_active is True


def test_technicians_dropdown_excludes_other_organization(auth_client, manager_a, tech_a, tech_b):
    ids = [t["id"] for t in auth_client(manager_a).get(TECHNICIANS).data]
    assert str(tech_a.id) in ids
    assert str(tech_b.id) not in ids


def test_each_organization_sees_only_its_own_users(auth_client, admin_a, admin_b):
    a_emails = {u["email"] for u in auth_client(admin_a).get(USERS).data["results"]}
    b_emails = {u["email"] for u in auth_client(admin_b).get(USERS).data["results"]}
    assert a_emails.isdisjoint(b_emails)


def test_inactive_organization_blocks_existing_session(auth_client, admin_a, org_a):
    client = auth_client(admin_a)
    assert client.get(USERS).status_code == 200
    org_a.is_active = False
    org_a.save()
    assert client.get(USERS).status_code == 403