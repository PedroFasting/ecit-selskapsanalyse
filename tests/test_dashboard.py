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
