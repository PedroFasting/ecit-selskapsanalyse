"""
Tester for dashboard-systemet: brukere, autentisering, profiler og pins.

Bruker FastAPI TestClient med midlertidig testdatabase.
Seeded data inkluderer 1 admin-bruker og 4 standard-profiler.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hr.database import init_database, get_connection, DEFAULT_DB_PATH
from hr.analytics import HRAnalytics
from tests.conftest import seed_employees


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(tmp_path):
    """Opprett midlertidig testdatabase med kjente data."""
    db_path = tmp_path / "test_dashboard.db"
    init_database(db_path)
    seed_employees(db_path)
    return db_path


@pytest.fixture
def client(test_db):
    """FastAPI TestClient med testdatabase."""
    import web.app as web_app_module
    import web.routes.import_routes as import_routes_module

    with patch("hr.database.DEFAULT_DB_PATH", test_db), \
         patch.object(import_routes_module, "DEFAULT_DB_PATH", test_db):

        with TestClient(web_app_module.app, raise_server_exceptions=False) as c:
            web_app_module.analytics = HRAnalytics(db_path=test_db)
            yield c


@pytest.fixture
def admin_client(client, test_db):
    """TestClient innlogget som admin (bruker-id 1 fra seed)."""
    # Seed oppretter admin med id=1
    resp = client.post("/api/auth/login", json={"user_id": 1})
    assert resp.status_code == 200
    # Cookies settes automatisk i TestClient
    return client


@pytest.fixture
def bruker_client(client, test_db):
    """TestClient innlogget som vanlig bruker."""
    # Opprett en vanlig bruker først (krever admin)
    client.post("/api/auth/login", json={"user_id": 1})
    resp = client.post("/api/users", json={
        "navn": "Testbruker",
        "epost": "test@ecit.no",
        "rolle": "bruker",
    })
    assert resp.status_code == 201
    bruker_id = resp.json()["id"]

    # Logg ut admin, logg inn som bruker
    client.post("/api/auth/logout")
    resp = client.post("/api/auth/login", json={"user_id": bruker_id})
    assert resp.status_code == 200
    return client


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------

def assert_json_ok(response, expected_status=200):
    """Verifiser gyldig JSON med riktig statuskode."""
    assert response.status_code == expected_status, (
        f"Forventet {expected_status}, fikk {response.status_code}: {response.text[:300]}"
    )
    return response.json()


# ===========================================================================
# BRUKERE
# ===========================================================================

class TestUsers:
    """Tester for /api/users endepunkter."""

    def test_list_users(self, client):
        """Hent brukerliste (uautentisert OK — brukes til login-dropdown)."""
        data = assert_json_ok(client.get("/api/users"))
        assert isinstance(data, list)
        assert len(data) >= 1
        # Admin fra seed
        admin = data[0]
        assert admin["navn"] == "Admin"
        assert admin["rolle"] == "admin"

    def test_create_user_requires_admin(self, client):
        """Opprettelse uten innlogging gir 401."""
        resp = client.post("/api/users", json={
            "navn": "Ny bruker",
            "epost": "ny@ecit.no",
        })
        assert resp.status_code == 401

    def test_create_user_as_admin(self, admin_client):
        """Admin kan opprette brukere."""
        data = assert_json_ok(
            admin_client.post("/api/users", json={
                "navn": "Kari Test",
                "epost": "kari@ecit.no",
                "rolle": "bruker",
            }),
            expected_status=201,
        )
        assert data["navn"] == "Kari Test"
        assert data["rolle"] == "bruker"
        assert "id" in data

    def test_create_user_duplicate_epost(self, admin_client):
        """Duplikat e-post gir 409."""
        admin_client.post("/api/users", json={
            "navn": "Bruker A",
            "epost": "dup@ecit.no",
            "rolle": "bruker",
        })
        resp = admin_client.post("/api/users", json={
            "navn": "Bruker B",
            "epost": "dup@ecit.no",
            "rolle": "bruker",
        })
        assert resp.status_code == 409

    def test_create_user_as_bruker_forbidden(self, bruker_client):
        """Vanlig bruker kan ikke opprette brukere."""
        resp = bruker_client.post("/api/users", json={
            "navn": "Uautorisert",
            "epost": "hack@ecit.no",
        })
        assert resp.status_code == 403


# ===========================================================================
# BRUKER-OPPDATERING
# ===========================================================================

class TestUpdateUser:
    """Tester for PUT /api/users/{id}."""

    def _create_user(self, admin_client, navn="Testbruker", epost="test@ecit.no", rolle="bruker"):
        resp = admin_client.post("/api/users", json={"navn": navn, "epost": epost, "rolle": rolle})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_update_requires_auth(self, client):
        """Oppdatering uten innlogging gir 401."""
        resp = client.put("/api/users/1", json={"navn": "Hacker"})
        assert resp.status_code == 401

    def test_update_requires_admin(self, bruker_client):
        """Vanlig bruker kan ikke oppdatere brukere."""
        resp = bruker_client.put("/api/users/1", json={"navn": "Nope"})
        assert resp.status_code == 403

    def test_update_navn(self, admin_client):
        """Admin kan endre navn."""
        uid = self._create_user(admin_client, epost="oppdater-navn@ecit.no")
        data = assert_json_ok(admin_client.put(f"/api/users/{uid}", json={"navn": "Nytt Navn"}))
        assert data["navn"] == "Nytt Navn"
        assert data["epost"] == "oppdater-navn@ecit.no"

    def test_update_epost(self, admin_client):
        """Admin kan endre e-post."""
        uid = self._create_user(admin_client, epost="gammel@ecit.no")
        data = assert_json_ok(admin_client.put(f"/api/users/{uid}", json={"epost": "ny@ecit.no"}))
        assert data["epost"] == "ny@ecit.no"

    def test_update_rolle(self, admin_client):
        """Admin kan endre rolle for andre brukere."""
        uid = self._create_user(admin_client, epost="rolle-test@ecit.no")
        data = assert_json_ok(admin_client.put(f"/api/users/{uid}", json={"rolle": "admin"}))
        assert data["rolle"] == "admin"

    def test_update_multiple_fields(self, admin_client):
        """Flere felt kan oppdateres samtidig."""
        uid = self._create_user(admin_client, epost="multi@ecit.no")
        data = assert_json_ok(admin_client.put(f"/api/users/{uid}", json={
            "navn": "Helt Ny",
            "epost": "helt-ny@ecit.no",
        }))
        assert data["navn"] == "Helt Ny"
        assert data["epost"] == "helt-ny@ecit.no"

    def test_update_self_role_blocked(self, admin_client):
        """Admin kan ikke endre sin egen rolle."""
        resp = admin_client.put("/api/users/1", json={"rolle": "bruker"})
        assert resp.status_code == 400
        assert "egen rolle" in resp.json()["detail"].lower()

    def test_update_self_navn_ok(self, admin_client):
        """Admin kan endre sitt eget navn (bare ikke rolle)."""
        data = assert_json_ok(admin_client.put("/api/users/1", json={"navn": "Super Admin"}))
        assert data["navn"] == "Super Admin"

    def test_update_invalid_rolle(self, admin_client):
        """Ugyldig rolle gir 400."""
        uid = self._create_user(admin_client, epost="rolle-feil@ecit.no")
        resp = admin_client.put(f"/api/users/{uid}", json={"rolle": "superadmin"})
        assert resp.status_code == 400

    def test_update_empty_navn(self, admin_client):
        """Tomt navn gir 400."""
        uid = self._create_user(admin_client, epost="tomt-navn@ecit.no")
        resp = admin_client.put(f"/api/users/{uid}", json={"navn": "  "})
        assert resp.status_code == 400

    def test_update_empty_epost(self, admin_client):
        """Tom e-post gir 400."""
        uid = self._create_user(admin_client, epost="tom-epost@ecit.no")
        resp = admin_client.put(f"/api/users/{uid}", json={"epost": ""})
        assert resp.status_code == 400

    def test_update_duplicate_epost(self, admin_client):
        """Duplikat e-post gir 409."""
        self._create_user(admin_client, epost="eksisterer@ecit.no")
        uid2 = self._create_user(admin_client, epost="annen@ecit.no")
        resp = admin_client.put(f"/api/users/{uid2}", json={"epost": "eksisterer@ecit.no"})
        assert resp.status_code == 409

    def test_update_same_epost_ok(self, admin_client):
        """Å sende samme e-post som brukeren allerede har er OK (no-op)."""
        uid = self._create_user(admin_client, epost="same@ecit.no")
        data = assert_json_ok(admin_client.put(f"/api/users/{uid}", json={"epost": "same@ecit.no"}))
        assert data["epost"] == "same@ecit.no"

    def test_update_nonexistent_user(self, admin_client):
        """Oppdatering av ikke-eksisterende bruker gir 404."""
        resp = admin_client.put("/api/users/9999", json={"navn": "Ghost"})
        assert resp.status_code == 404

    def test_update_no_fields(self, admin_client):
        """Ingen felt å oppdatere gir 400."""
        uid = self._create_user(admin_client, epost="nofields@ecit.no")
        resp = admin_client.put(f"/api/users/{uid}", json={})
        assert resp.status_code == 400


# ===========================================================================
# BRUKER-SLETTING (myk)
# ===========================================================================

class TestDeleteUser:
    """Tester for DELETE /api/users/{id} (myk sletting)."""

    def _create_user(self, admin_client, navn="Slett Meg", epost="slett@ecit.no"):
        resp = admin_client.post("/api/users", json={"navn": navn, "epost": epost, "rolle": "bruker"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_delete_requires_auth(self, client):
        """Sletting uten innlogging gir 401."""
        resp = client.delete("/api/users/1")
        assert resp.status_code == 401

    def test_delete_requires_admin(self, bruker_client):
        """Vanlig bruker kan ikke slette brukere."""
        resp = bruker_client.delete("/api/users/1")
        assert resp.status_code == 403

    def test_delete_success(self, admin_client):
        """Admin kan deaktivere en bruker."""
        uid = self._create_user(admin_client)
        data = assert_json_ok(admin_client.delete(f"/api/users/{uid}"))
        assert data["ok"] is True
        assert "Slett Meg" in data["deaktivert"]

        # Brukeren dukker ikke opp i listen lenger
        users = assert_json_ok(admin_client.get("/api/users"))
        user_ids = [u["id"] for u in users]
        assert uid not in user_ids

    def test_delete_self_blocked(self, admin_client):
        """Admin kan ikke slette seg selv."""
        resp = admin_client.delete("/api/users/1")
        assert resp.status_code == 400
        assert "deg selv" in resp.json()["detail"].lower()

    def test_delete_nonexistent_user(self, admin_client):
        """Sletting av ikke-eksisterende bruker gir 404."""
        resp = admin_client.delete("/api/users/9999")
        assert resp.status_code == 404

    def test_delete_already_deactivated(self, admin_client):
        """Sletting av allerede deaktivert bruker gir 404."""
        uid = self._create_user(admin_client, epost="dobbel-slett@ecit.no")
        admin_client.delete(f"/api/users/{uid}")
        resp = admin_client.delete(f"/api/users/{uid}")
        assert resp.status_code == 404

    def test_deactivated_user_cannot_login(self, client, admin_client):
        """Deaktivert bruker kan ikke logge inn."""
        uid = self._create_user(admin_client, epost="no-login@ecit.no")
        admin_client.delete(f"/api/users/{uid}")

        # Logg ut admin
        client.post("/api/auth/logout")
        # Forsøk å logge inn som deaktivert bruker
        resp = client.post("/api/auth/login", json={"user_id": uid})
        assert resp.status_code == 404
# AUTENTISERING
# ===========================================================================

class TestAuth:
    """Tester for /api/auth/* endepunkter."""

    def test_login_success(self, client):
        """Vellykket innlogging returnerer brukerinfo og setter cookie."""
        resp = client.post("/api/auth/login", json={"user_id": 1})
        data = assert_json_ok(resp)
        assert data["navn"] == "Admin"
        assert data["rolle"] == "admin"
        # Cookie satt
        assert "user_id" in resp.cookies

    def test_login_nonexistent_user(self, client):
        """Innlogging med ukjent bruker-ID gir 404."""
        resp = client.post("/api/auth/login", json={"user_id": 9999})
        assert resp.status_code == 404

    def test_me_authenticated(self, admin_client):
        """/auth/me returnerer innlogget bruker."""
        data = assert_json_ok(admin_client.get("/api/auth/me"))
        assert data["navn"] == "Admin"
        assert data["rolle"] == "admin"

    def test_me_unauthenticated(self, client):
        """/auth/me uten innlogging gir 401."""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_logout(self, admin_client):
        """Utlogging fjerner cookie og påfølgende /me gir 401."""
        resp = admin_client.post("/api/auth/logout")
        assert_json_ok(resp)
        # Etter logout: /auth/me skal feile
        resp = admin_client.get("/api/auth/me")
        assert resp.status_code == 401


# ===========================================================================
# DASHBOARD-PROFILER
# ===========================================================================

class TestProfiles:
    """Tester for /api/dashboard/profiles endepunkter."""

    def test_list_profiles_requires_auth(self, client):
        """Profilliste krever innlogging."""
        resp = client.get("/api/dashboard/profiles")
        assert resp.status_code == 401

    def test_list_profiles_includes_mine_grafer(self, admin_client):
        """Profilliste inneholder 'Mine grafer' pseudo-profil pluss seed-profiler."""
        data = assert_json_ok(admin_client.get("/api/dashboard/profiles"))
        assert isinstance(data, list)
        # Første element er alltid 'Mine grafer'
        assert data[0]["navn"] == "Mine grafer"
        assert data[0]["id"] is None
        # Seed-profiler: HR-oversikt, Ledelse, Lønnsanalyse, Mangfold
        profile_names = [p["navn"] for p in data]
        assert "HR-oversikt" in profile_names
        assert "Ledelse" in profile_names
        assert "Lønnsanalyse" in profile_names
        assert "Mangfold" in profile_names

    def test_list_profiles_as_bruker(self, bruker_client):
        """Vanlig bruker ser profiler med synlig_for='alle'."""
        data = assert_json_ok(bruker_client.get("/api/dashboard/profiles"))
        assert data[0]["navn"] == "Mine grafer"
        # Seed-profiler har synlig_for='alle' (default)
        assert len(data) >= 5  # Mine grafer + 4 seed-profiler

    def test_create_profile_as_admin(self, admin_client):
        """Admin kan opprette ny profil."""
        data = assert_json_ok(
            admin_client.post("/api/dashboard/profiles", json={
                "navn": "Testprofil",
                "beskrivelse": "En testprofil",
            }),
            expected_status=201,
        )
        assert data["navn"] == "Testprofil"
        assert data["slug"] == "testprofil"
        assert "id" in data

    def test_create_profile_as_bruker_forbidden(self, bruker_client):
        """Vanlig bruker kan ikke opprette profiler."""
        resp = bruker_client.post("/api/dashboard/profiles", json={
            "navn": "Uautorisert profil",
        })
        assert resp.status_code == 403

    def test_create_profile_duplicate_slug(self, admin_client):
        """Duplikat slug gir 409."""
        admin_client.post("/api/dashboard/profiles", json={"navn": "Dup Test"})
        resp = admin_client.post("/api/dashboard/profiles", json={"navn": "Dup Test"})
        assert resp.status_code == 409

    def test_update_profile(self, admin_client):
        """Admin kan oppdatere profil."""
        # Opprett
        create_resp = assert_json_ok(
            admin_client.post("/api/dashboard/profiles", json={
                "navn": "Oppdater meg",
            }),
            expected_status=201,
        )
        pid = create_resp["id"]

        # Oppdater
        data = assert_json_ok(admin_client.put(
            f"/api/dashboard/profiles/{pid}",
            json={"navn": "Oppdatert", "beskrivelse": "Ny beskrivelse"},
        ))
        assert data["ok"] is True

    def test_update_nonexistent_profile(self, admin_client):
        """Oppdatering av ukjent profil gir 404."""
        resp = admin_client.put("/api/dashboard/profiles/9999", json={"navn": "X"})
        assert resp.status_code == 404

    def test_delete_profile(self, admin_client):
        """Admin kan slette profil."""
        create_resp = assert_json_ok(
            admin_client.post("/api/dashboard/profiles", json={
                "navn": "Slett meg",
            }),
            expected_status=201,
        )
        pid = create_resp["id"]

        data = assert_json_ok(admin_client.delete(f"/api/dashboard/profiles/{pid}"))
        assert data["ok"] is True

        # Verifiser at profilen er borte fra listen
        profiles = assert_json_ok(admin_client.get("/api/dashboard/profiles"))
        ids = [p["id"] for p in profiles]
        assert pid not in ids

    def test_delete_profile_cascades_pins(self, admin_client):
        """Sletting av profil fjerner også tilhørende pins."""
        # Opprett profil
        create_resp = assert_json_ok(
            admin_client.post("/api/dashboard/profiles", json={
                "navn": "Med Pins",
            }),
            expected_status=201,
        )
        pid = create_resp["id"]

        # Legg til en pin
        admin_client.post("/api/dashboard/pins", json={
            "profile_id": pid,
            "metric": "count",
            "group_by": "kjonn",
            "tittel": "Test pin",
        })

        # Slett profilen
        admin_client.delete(f"/api/dashboard/profiles/{pid}")

        # Pins for denne profilen skal være tomme
        pins = assert_json_ok(admin_client.get(
            f"/api/dashboard/pins?profile_id={pid}"
        ))
        assert len(pins) == 0

    def test_delete_nonexistent_profile(self, admin_client):
        """Sletting av ukjent profil gir 404."""
        resp = admin_client.delete("/api/dashboard/profiles/9999")
        assert resp.status_code == 404


# ===========================================================================
# PINS
# ===========================================================================

class TestPins:
    """Tester for /api/dashboard/pins endepunkter."""

    def test_list_pins_requires_auth(self, client):
        """Pins krever innlogging."""
        resp = client.get("/api/dashboard/pins")
        assert resp.status_code == 401

    def test_list_personal_pins_empty(self, admin_client):
        """Mine grafer er tomme til å begynne med."""
        data = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        assert data == []

    def test_list_seed_profile_pins(self, admin_client):
        """Seed-profiler har pins."""
        # Hent profiler for å finne HR-oversikt sin ID
        profiles = assert_json_ok(admin_client.get("/api/dashboard/profiles"))
        hr_profile = next(p for p in profiles if p["navn"] == "HR-oversikt")

        pins = assert_json_ok(admin_client.get(
            f"/api/dashboard/pins?profile_id={hr_profile['id']}"
        ))
        assert len(pins) == 4  # 4 pins i HR-oversikt seed
        assert pins[0]["tittel"] == "Ansatte per land"

    def test_create_personal_pin(self, admin_client):
        """Opprett pin i 'Mine grafer' (profile_id=None)."""
        data = assert_json_ok(
            admin_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "avdeling",
                "chart_type": "bar",
                "tittel": "Ansatte per avdeling",
            }),
            expected_status=201,
        )
        assert data["tittel"] == "Ansatte per avdeling"
        assert "id" in data

        # Verifiser at den dukker opp i listen
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        assert len(pins) == 1
        assert pins[0]["metric"] == "count"
        assert pins[0]["group_by"] == "avdeling"

    def test_create_profile_pin_as_admin(self, admin_client):
        """Admin kan legge til pin i en profil."""
        # Opprett en profil
        profile = assert_json_ok(
            admin_client.post("/api/dashboard/profiles", json={
                "navn": "Pin-testprofil",
            }),
            expected_status=201,
        )

        data = assert_json_ok(
            admin_client.post("/api/dashboard/pins", json={
                "profile_id": profile["id"],
                "metric": "avg_salary",
                "group_by": "kjonn",
                "tittel": "Snittlønn per kjønn",
            }),
            expected_status=201,
        )
        assert data["tittel"] == "Snittlønn per kjønn"

    def test_create_profile_pin_as_bruker_forbidden(self, bruker_client):
        """Vanlig bruker kan ikke legge til i profiler."""
        # Hent en profil-ID fra seed
        profiles = assert_json_ok(bruker_client.get("/api/dashboard/profiles"))
        profile_id = next(p["id"] for p in profiles if p["id"] is not None)

        resp = bruker_client.post("/api/dashboard/pins", json={
            "profile_id": profile_id,
            "metric": "count",
            "group_by": "kjonn",
            "tittel": "Uautorisert pin",
        })
        assert resp.status_code == 403

    def test_create_pin_nonexistent_profile(self, admin_client):
        """Pin i ukjent profil gir 404."""
        resp = admin_client.post("/api/dashboard/pins", json={
            "profile_id": 9999,
            "metric": "count",
            "group_by": "kjonn",
            "tittel": "Ugyldig",
        })
        assert resp.status_code == 404

    def test_duplicate_personal_pin_rejected(self, admin_client):
        """Duplikat personlig pin gir 409."""
        pin_data = {
            "metric": "count",
            "group_by": "kjonn",
            "tittel": "Kjønnsfordeling",
        }
        assert_json_ok(admin_client.post("/api/dashboard/pins", json=pin_data), 201)
        resp = admin_client.post("/api/dashboard/pins", json=pin_data)
        assert resp.status_code == 409

    def test_duplicate_profile_pin_rejected(self, admin_client):
        """Duplikat profil-pin gir 409."""
        profile = assert_json_ok(
            admin_client.post("/api/dashboard/profiles", json={"navn": "Dup-pin-test"}),
            expected_status=201,
        )
        pin_data = {
            "profile_id": profile["id"],
            "metric": "count",
            "group_by": "avdeling",
            "tittel": "Test",
        }
        assert_json_ok(admin_client.post("/api/dashboard/pins", json=pin_data), 201)
        resp = admin_client.post("/api/dashboard/pins", json=pin_data)
        assert resp.status_code == 409

    def test_same_metric_different_filter_allowed(self, admin_client):
        """Samme metrikk+gruppering men forskjellig filter er OK."""
        base = {
            "metric": "count",
            "group_by": "avdeling",
            "tittel": "Test",
        }
        assert_json_ok(admin_client.post("/api/dashboard/pins", json={
            **base, "filter_dim": "arbeidsland", "filter_val": "Norge",
        }), 201)
        resp = admin_client.post("/api/dashboard/pins", json={
            **base, "filter_dim": "arbeidsland", "filter_val": "Danmark",
        })
        assert resp.status_code == 201

    def test_create_pin_with_multi_filters(self, admin_client):
        """Pin med multi-select filters (JSON) lagres korrekt."""
        filters = {"arbeidsland": ["Norge", "Sverige"], "kjonn": ["Kvinne"]}
        data = assert_json_ok(
            admin_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "avdeling",
                "filters": filters,
                "tittel": "Multi-filter test",
            }),
            expected_status=201,
        )
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        pin = next(p for p in pins if p["id"] == data["id"])
        assert pin["filters"] == filters

    def test_pin_filters_duplicate_check(self, admin_client):
        """Pins med ulike filters-JSON er ikke duplikater."""
        base = {
            "metric": "count",
            "group_by": "avdeling",
            "tittel": "Dup-test",
        }
        assert_json_ok(admin_client.post("/api/dashboard/pins", json={
            **base, "filters": {"arbeidsland": ["Norge"]},
        }), 201)
        resp = admin_client.post("/api/dashboard/pins", json={
            **base, "filters": {"arbeidsland": ["Norge", "Danmark"]},
        })
        assert resp.status_code == 201

    def test_pin_backward_compat_filter_dim_to_filters(self, admin_client):
        """Pin med gammelt filter_dim/filter_val får filters bygget automatisk."""
        data = assert_json_ok(
            admin_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "kjonn",
                "filter_dim": "arbeidsland",
                "filter_val": "Norge",
                "tittel": "Compat test",
            }),
            expected_status=201,
        )
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        pin = next(p for p in pins if p["id"] == data["id"])
        assert pin["filters"] == {"arbeidsland": ["Norge"]}

    def test_create_pin_with_split_by(self, admin_client):
        """Pin med split_by lagres korrekt."""
        data = assert_json_ok(
            admin_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "avdeling",
                "split_by": "kjonn",
                "chart_type": "stacked",
                "tittel": "Avdeling per kjønn",
            }),
            expected_status=201,
        )
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        pin = next(p for p in pins if p["id"] == data["id"])
        assert pin["split_by"] == "kjonn"
        assert pin["chart_type"] == "stacked"

    def test_bruker_can_create_personal_pin(self, bruker_client):
        """Vanlig bruker kan pinne til 'Mine grafer'."""
        data = assert_json_ok(
            bruker_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "kjonn",
                "tittel": "Min graf",
            }),
            expected_status=201,
        )
        assert data["tittel"] == "Min graf"

    def test_delete_personal_pin(self, admin_client):
        """Bruker kan fjerne egne pins."""
        create = assert_json_ok(
            admin_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "kjonn",
                "tittel": "Slett meg",
            }),
            expected_status=201,
        )
        pin_id = create["id"]

        data = assert_json_ok(admin_client.delete(f"/api/dashboard/pins/{pin_id}"))
        assert data["ok"] is True

        # Verifiser borte
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        assert all(p["id"] != pin_id for p in pins)

    def test_delete_profile_pin_as_admin(self, admin_client):
        """Admin kan fjerne profil-pins."""
        profiles = assert_json_ok(admin_client.get("/api/dashboard/profiles"))
        hr_profile = next(p for p in profiles if p["navn"] == "HR-oversikt")

        pins = assert_json_ok(admin_client.get(
            f"/api/dashboard/pins?profile_id={hr_profile['id']}"
        ))
        pin_id = pins[0]["id"]

        data = assert_json_ok(admin_client.delete(f"/api/dashboard/pins/{pin_id}"))
        assert data["ok"] is True

    def test_delete_profile_pin_as_bruker_forbidden(self, bruker_client):
        """Vanlig bruker kan ikke fjerne profil-pins."""
        profiles = assert_json_ok(bruker_client.get("/api/dashboard/profiles"))
        hr_profile = next(p for p in profiles if p["navn"] == "HR-oversikt")

        pins = assert_json_ok(bruker_client.get(
            f"/api/dashboard/pins?profile_id={hr_profile['id']}"
        ))
        pin_id = pins[0]["id"]

        resp = bruker_client.delete(f"/api/dashboard/pins/{pin_id}")
        assert resp.status_code == 403

    def test_delete_nonexistent_pin(self, admin_client):
        """Sletting av ukjent pin gir 404."""
        resp = admin_client.delete("/api/dashboard/pins/9999")
        assert resp.status_code == 404

    def test_pin_sortering_increments(self, admin_client):
        """Pins får inkrementerende sortering."""
        for i in range(3):
            admin_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": ["kjonn", "avdeling", "arbeidsland"][i],
                "tittel": f"Pin {i}",
            })

        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        sorteringer = [p["sortering"] for p in pins]
        assert sorteringer == [0, 1, 2]


# ===========================================================================
# REORDER
# ===========================================================================

class TestReorder:
    """Tester for /api/dashboard/pins/reorder."""

    def test_reorder_pins(self, admin_client):
        """Endre rekkefølge på pins."""
        # Opprett 3 pins
        ids = []
        for i in range(3):
            resp = assert_json_ok(
                admin_client.post("/api/dashboard/pins", json={
                    "metric": "count",
                    "group_by": ["kjonn", "avdeling", "arbeidsland"][i],
                    "tittel": f"Reorder {i}",
                }),
                expected_status=201,
            )
            ids.append(resp["id"])

        # Reverser rekkefølgen
        reversed_ids = list(reversed(ids))
        data = assert_json_ok(admin_client.put(
            "/api/dashboard/pins/reorder",
            json={"pin_ids": reversed_ids},
        ))
        assert data["ok"] is True

        # Verifiser ny rekkefølge
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        for idx, pin in enumerate(pins):
            assert pin["id"] == reversed_ids[idx]
            assert pin["sortering"] == idx


# ===========================================================================
# MIGRERING FRA LOCALSTORAGE
# ===========================================================================

class TestMigrateLocal:
    """Tester for /api/dashboard/pins/migrate-local."""

    def test_migrate_pins(self, admin_client):
        """Migrering av localStorage-pins oppretter 'Mine grafer'-pins."""
        local_pins = [
            {
                "metric": "count",
                "group_by": "kjonn",
                "title": "Kjønnsfordeling",
                "chart_type": "pie",
            },
            {
                "metric": "avg_salary",
                "group_by": "avdeling",
                "title": "Snittlønn",
                "chart_type": "bar",
            },
        ]

        data = assert_json_ok(admin_client.post(
            "/api/dashboard/pins/migrate-local",
            json={"pins": local_pins},
        ))
        assert data["migrated"] == 2

        # Verifiser at de dukker opp som personlige pins
        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        assert len(pins) == 2

    def test_migrate_skips_duplicates(self, admin_client):
        """Duplikater fra localStorage hoppes over."""
        pin = {
            "metric": "count",
            "group_by": "kjonn",
            "title": "Kjønnsfordeling",
        }
        # Migrerer først
        admin_client.post("/api/dashboard/pins/migrate-local", json={"pins": [pin]})

        # Migrerer igjen — skal hoppe over
        data = assert_json_ok(admin_client.post(
            "/api/dashboard/pins/migrate-local",
            json={"pins": [pin]},
        ))
        assert data["migrated"] == 0

    def test_migrate_skips_invalid(self, admin_client):
        """Pins uten metric/group_by hoppes over."""
        pins = [
            {"title": "Mangler metric"},
            {"metric": "count", "title": "Mangler group_by"},
            {"metric": "count", "group_by": "kjonn", "title": "OK"},
        ]
        data = assert_json_ok(admin_client.post(
            "/api/dashboard/pins/migrate-local",
            json={"pins": pins},
        ))
        assert data["migrated"] == 1

    def test_migrate_requires_auth(self, client):
        """Migrering krever innlogging."""
        resp = client.post("/api/dashboard/pins/migrate-local", json={"pins": []})
        assert resp.status_code == 401

    def test_migrate_uses_tittel_field(self, admin_client):
        """Migrering aksepterer 'tittel' som alternativ til 'title'."""
        pin = {
            "metric": "count",
            "group_by": "avdeling",
            "tittel": "Norsk feltnavn",
        }
        data = assert_json_ok(admin_client.post(
            "/api/dashboard/pins/migrate-local",
            json={"pins": [pin]},
        ))
        assert data["migrated"] == 1

        pins = assert_json_ok(admin_client.get("/api/dashboard/pins"))
        assert pins[0]["tittel"] == "Norsk feltnavn"


# ===========================================================================
# TILGANGSKONTROLL (RBAC) — tverrgående tester
# ===========================================================================

class TestRBAC:
    """Verifiser at rollebasert tilgangskontroll fungerer konsistent."""

    def test_bruker_cannot_create_profiles(self, bruker_client):
        resp = bruker_client.post("/api/dashboard/profiles", json={"navn": "Nope"})
        assert resp.status_code == 403

    def test_bruker_cannot_update_profiles(self, bruker_client):
        profiles = assert_json_ok(bruker_client.get("/api/dashboard/profiles"))
        pid = next(p["id"] for p in profiles if p["id"] is not None)
        resp = bruker_client.put(f"/api/dashboard/profiles/{pid}", json={"navn": "Nope"})
        assert resp.status_code == 403

    def test_bruker_cannot_delete_profiles(self, bruker_client):
        profiles = assert_json_ok(bruker_client.get("/api/dashboard/profiles"))
        pid = next(p["id"] for p in profiles if p["id"] is not None)
        resp = bruker_client.delete(f"/api/dashboard/profiles/{pid}")
        assert resp.status_code == 403

    def test_bruker_cannot_create_users(self, bruker_client):
        resp = bruker_client.post("/api/users", json={
            "navn": "Nope",
            "epost": "nope@ecit.no",
        })
        assert resp.status_code == 403

    def test_bruker_can_pin_to_mine_grafer(self, bruker_client):
        """Vanlig bruker kan kun pinne til 'Mine grafer'."""
        data = assert_json_ok(
            bruker_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "kjonn",
                "tittel": "Min personlige graf",
            }),
            expected_status=201,
        )
        assert data["tittel"] == "Min personlige graf"

    def test_bruker_can_delete_own_pin(self, bruker_client):
        """Vanlig bruker kan fjerne sine egne pins."""
        create = assert_json_ok(
            bruker_client.post("/api/dashboard/pins", json={
                "metric": "count",
                "group_by": "avdeling",
                "tittel": "Min midlertidige",
            }),
            expected_status=201,
        )
        resp = bruker_client.delete(f"/api/dashboard/pins/{create['id']}")
        assert resp.status_code == 200


# ===========================================================================
# ANALYSE-MALER (templates)
# ===========================================================================

class TestTemplates:
    """Tester for /api/dashboard/templates endepunkter."""

    def test_list_templates_requires_auth(self, client):
        """Henting av maler krever innlogging."""
        resp = client.get("/api/dashboard/templates")
        assert resp.status_code == 401

    def test_list_templates_empty(self, admin_client):
        """Tom liste for ny bruker."""
        data = assert_json_ok(admin_client.get("/api/dashboard/templates"))
        assert data == []

    def test_create_template(self, admin_client):
        """Opprett en mal."""
        data = assert_json_ok(
            admin_client.post("/api/dashboard/templates", json={
                "navn": "Min mal",
                "metric": "count",
                "group_by": "avdeling",
                "split_by": "kjonn",
                "filters": {"arbeidsland": ["Norge"]},
                "chart_type": "bar",
            }),
            expected_status=201,
        )
        assert data["navn"] == "Min mal"
        assert data["updated"] is False
        assert "id" in data

    def test_create_template_overwrites_existing(self, admin_client):
        """Opprett mal med samme navn overskriver."""
        admin_client.post("/api/dashboard/templates", json={
            "navn": "Overskriv-test",
            "metric": "count",
            "group_by": "avdeling",
        })
        data = assert_json_ok(
            admin_client.post("/api/dashboard/templates", json={
                "navn": "Overskriv-test",
                "metric": "avg_salary",
                "group_by": "kjonn",
            }),
            expected_status=201,
        )
        assert data["updated"] is True

        # Verifiser at det bare finnes én mal med det navnet
        templates = assert_json_ok(admin_client.get("/api/dashboard/templates"))
        matching = [t for t in templates if t["navn"] == "Overskriv-test"]
        assert len(matching) == 1
        assert matching[0]["metric"] == "avg_salary"

    def test_list_templates_returns_created(self, admin_client):
        """Liste inneholder opprettede maler."""
        admin_client.post("/api/dashboard/templates", json={
            "navn": "Mal A",
            "metric": "count",
            "group_by": "arbeidsland",
        })
        admin_client.post("/api/dashboard/templates", json={
            "navn": "Mal B",
            "metric": "avg_salary",
            "group_by": "kjonn",
            "filters": {"avdeling": ["Regnskap", "IT"]},
        })
        data = assert_json_ok(admin_client.get("/api/dashboard/templates"))
        assert len(data) >= 2
        names = [t["navn"] for t in data]
        assert "Mal A" in names
        assert "Mal B" in names

        # Sjekk at filtre deserialiseres til dict
        mal_b = next(t for t in data if t["navn"] == "Mal B")
        assert isinstance(mal_b["filters"], dict)
        assert mal_b["filters"]["avdeling"] == ["Regnskap", "IT"]

    def test_delete_template(self, admin_client):
        """Slett en mal."""
        create = assert_json_ok(
            admin_client.post("/api/dashboard/templates", json={
                "navn": "Slett-test",
                "metric": "count",
                "group_by": "avdeling",
            }),
            expected_status=201,
        )
        resp = admin_client.delete(f"/api/dashboard/templates/{create['id']}")
        assert resp.status_code == 200

        # Verifiser at den er borte
        templates = assert_json_ok(admin_client.get("/api/dashboard/templates"))
        assert all(t["navn"] != "Slett-test" for t in templates)

    def test_delete_nonexistent_template(self, admin_client):
        """Sletting av ikke-eksisterende mal gir 404."""
        resp = admin_client.delete("/api/dashboard/templates/99999")
        assert resp.status_code == 404

    def test_templates_are_user_scoped(self, client, test_db):
        """Maler er isolert per bruker."""
        # Logg inn som admin og opprett en mal
        client.post("/api/auth/login", json={"user_id": 1})
        client.post("/api/dashboard/templates", json={
            "navn": "Admin-mal",
            "metric": "count",
            "group_by": "avdeling",
        })

        # Opprett en vanlig bruker
        resp = client.post("/api/users", json={
            "navn": "Malbruker",
            "epost": "malbruker@ecit.no",
            "rolle": "bruker",
        })
        bruker_id = resp.json()["id"]

        # Logg ut admin, logg inn som bruker
        client.post("/api/auth/logout")
        client.post("/api/auth/login", json={"user_id": bruker_id})

        # Brukeren skal ikke se admin sin mal
        bruker_templates = assert_json_ok(client.get("/api/dashboard/templates"))
        assert all(t["navn"] != "Admin-mal" for t in bruker_templates)

    def test_migrate_templates(self, admin_client):
        """Migrer maler fra localStorage-format."""
        local_templates = [
            {
                "name": "Lokal mal 1",
                "metric": "count",
                "group_by": "arbeidsland",
                "split_by": None,
                "filters": None,
                "chart_type": "pie",
            },
            {
                "name": "Lokal mal 2",
                "metric": "avg_salary",
                "group_by": "kjonn",
                "filters": {"avdeling": ["IT"]},
                "chart_type": "bar",
            },
        ]
        data = assert_json_ok(
            admin_client.post("/api/dashboard/templates/migrate", json={
                "templates": local_templates,
            }),
        )
        assert data["migrated"] == 2

        # Verifiser
        templates = assert_json_ok(admin_client.get("/api/dashboard/templates"))
        names = [t["navn"] for t in templates]
        assert "Lokal mal 1" in names
        assert "Lokal mal 2" in names

    def test_migrate_skips_duplicates(self, admin_client):
        """Migrer hopper over maler som allerede finnes."""
        admin_client.post("/api/dashboard/templates", json={
            "navn": "Allerede der",
            "metric": "count",
            "group_by": "avdeling",
        })
        data = assert_json_ok(
            admin_client.post("/api/dashboard/templates/migrate", json={
                "templates": [{"name": "Allerede der", "metric": "count", "group_by": "avdeling"}],
            }),
        )
        assert data["migrated"] == 0


# ===========================================================================
# ALDERSKATEGORIER (konfigurerbare)
# ===========================================================================

class TestAgeCategories:
    """Tester for /api/age-categories endepunkter."""

    def test_list_age_categories_no_auth_required(self, client):
        """GET /age-categories er offentlig tilgjengelig."""
        data = assert_json_ok(client.get("/api/age-categories"))
        assert isinstance(data, list)
        assert len(data) == 6  # default seed

    def test_list_age_categories_returns_defaults(self, client):
        """Standard seed-kategorier returneres sortert."""
        data = assert_json_ok(client.get("/api/age-categories"))
        labels = [c["etikett"] for c in data]
        assert labels == ["Under 25", "25-34", "35-44", "45-54", "55-64", "65+"]

    def test_list_age_categories_has_expected_fields(self, client):
        """Hver kategori har id, min_alder, maks_alder, etikett, sortering."""
        data = assert_json_ok(client.get("/api/age-categories"))
        for cat in data:
            assert "id" in cat
            assert "min_alder" in cat
            assert "maks_alder" in cat
            assert "etikett" in cat
            assert "sortering" in cat

    def test_update_requires_admin(self, client):
        """PUT /age-categories krever admin-rolle."""
        resp = client.put("/api/age-categories", json={
            "kategorier": [{"min_alder": 0, "maks_alder": 30, "etikett": "Ung"}]
        })
        assert resp.status_code == 401

    def test_update_requires_admin_not_bruker(self, bruker_client):
        """Vanlig bruker kan ikke oppdatere alderskategorier."""
        resp = bruker_client.put("/api/age-categories", json={
            "kategorier": [{"min_alder": 0, "maks_alder": 30, "etikett": "Ung"}]
        })
        assert resp.status_code == 403

    def test_update_success(self, admin_client):
        """Admin kan erstatte alle kategorier."""
        new_cats = [
            {"min_alder": 0, "maks_alder": 29, "etikett": "Under 30"},
            {"min_alder": 30, "maks_alder": 49, "etikett": "30-49"},
            {"min_alder": 50, "maks_alder": 150, "etikett": "50+"},
        ]
        data = assert_json_ok(admin_client.put("/api/age-categories", json={
            "kategorier": new_cats,
        }))
        assert data["ok"] is True
        assert data["antall"] == 3

        # Verify persisted
        cats = assert_json_ok(admin_client.get("/api/age-categories"))
        labels = [c["etikett"] for c in cats]
        assert labels == ["Under 30", "30-49", "50+"]

    def test_update_sorts_by_min_alder(self, admin_client):
        """Kategorier sorteres etter min_alder uavhengig av input-rekkefølge."""
        new_cats = [
            {"min_alder": 50, "maks_alder": 150, "etikett": "50+"},
            {"min_alder": 0, "maks_alder": 29, "etikett": "Under 30"},
            {"min_alder": 30, "maks_alder": 49, "etikett": "30-49"},
        ]
        assert_json_ok(admin_client.put("/api/age-categories", json={
            "kategorier": new_cats,
        }))
        cats = assert_json_ok(admin_client.get("/api/age-categories"))
        mins = [c["min_alder"] for c in cats]
        assert mins == [0, 30, 50]

    def test_update_rejects_empty_list(self, admin_client):
        """Minst en kategori er pakrevd."""
        resp = admin_client.put("/api/age-categories", json={"kategorier": []})
        assert resp.status_code == 400

    def test_update_rejects_empty_label(self, admin_client):
        """Tom etikett er ikke tillatt."""
        resp = admin_client.put("/api/age-categories", json={
            "kategorier": [{"min_alder": 0, "maks_alder": 30, "etikett": "  "}]
        })
        assert resp.status_code == 400

    def test_update_rejects_negative_min(self, admin_client):
        """Negativ min_alder er ugyldig."""
        resp = admin_client.put("/api/age-categories", json={
            "kategorier": [{"min_alder": -1, "maks_alder": 30, "etikett": "Feil"}]
        })
        assert resp.status_code == 400

    def test_update_rejects_min_greater_than_max(self, admin_client):
        """min_alder > maks_alder er ugyldig."""
        resp = admin_client.put("/api/age-categories", json={
            "kategorier": [{"min_alder": 50, "maks_alder": 30, "etikett": "Feil"}]
        })
        assert resp.status_code == 400

    def test_update_rejects_overlapping_categories(self, admin_client):
        """Overlappende kategorier avvises."""
        resp = admin_client.put("/api/age-categories", json={
            "kategorier": [
                {"min_alder": 0, "maks_alder": 34, "etikett": "Ung"},
                {"min_alder": 30, "maks_alder": 60, "etikett": "Midt"},
            ]
        })
        assert resp.status_code == 400
        assert "overlapper" in resp.json()["detail"].lower()

    def test_update_allows_gaps(self, admin_client):
        """Kategorier med gap mellom seg er tillatt."""
        cats = [
            {"min_alder": 0, "maks_alder": 24, "etikett": "Ung"},
            {"min_alder": 30, "maks_alder": 60, "etikett": "Midt"},
        ]
        data = assert_json_ok(admin_client.put("/api/age-categories", json={
            "kategorier": cats,
        }))
        assert data["antall"] == 2

    def test_update_allows_adjacent(self, admin_client):
        """Kategorier som grenser til hverandre (25-34, 35-44) er OK."""
        cats = [
            {"min_alder": 25, "maks_alder": 34, "etikett": "25-34"},
            {"min_alder": 35, "maks_alder": 44, "etikett": "35-44"},
        ]
        data = assert_json_ok(admin_client.put("/api/age-categories", json={
            "kategorier": cats,
        }))
        assert data["antall"] == 2


# ===========================================================================
# ALDERSKATEGORIER — analytics integration
# ===========================================================================

class TestAgeCategoriesAnalytics:
    """Verify analytics uses DB-stored age categories."""

    def test_load_age_categories_from_db(self, test_db):
        """load_age_categories() reads from the DB."""
        from hr.analytics import load_age_categories
        cats = load_age_categories(test_db)
        assert len(cats) == 6
        assert cats[0] == (0, 24, "Under 25")
        assert cats[-1] == (65, 150, "65+")

    def test_load_age_categories_fallback_on_empty(self, test_db):
        """Falls back to defaults when table has no rows."""
        from hr.analytics import load_age_categories, _DEFAULT_AGE_CATEGORIES

        # Delete all rows
        conn = get_connection(test_db)
        conn.execute("DELETE FROM alderskategorier")
        conn.commit()
        conn.close()

        cats = load_age_categories(test_db)
        assert cats == list(_DEFAULT_AGE_CATEGORIES)

    def test_custom_categories_used_by_analytics(self, test_db):
        """Analytics methods pick up custom categories from DB."""
        from hr.analytics import HRAnalytics

        # Replace categories with 2 wider bands
        conn = get_connection(test_db)
        conn.execute("DELETE FROM alderskategorier")
        conn.execute(
            "INSERT INTO alderskategorier (min_alder, maks_alder, etikett, sortering) "
            "VALUES (0, 39, 'Under 40', 0)"
        )
        conn.execute(
            "INSERT INTO alderskategorier (min_alder, maks_alder, etikett, sortering) "
            "VALUES (40, 150, '40+', 1)"
        )
        conn.commit()
        conn.close()

        ha = HRAnalytics(db_path=test_db)
        dist = ha.age_distribution()
        # age_distribution returns Dict[str, int] — label -> count
        assert "Under 40" in dist
        assert "40+" in dist
        # Should NOT have default categories
        assert "25-34" not in dist
