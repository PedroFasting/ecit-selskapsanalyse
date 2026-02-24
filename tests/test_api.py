"""
API-tester for FastAPI-endepunktene.

Bruker FastAPI TestClient med en midlertidig testdatabase,
slik at testene kjører isolert uten å påvirke produksjonsdata.
"""

import os
import io
import openpyxl
from pathlib import Path
from unittest.mock import patch
from datetime import date

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
    db_path = tmp_path / "test_api.db"
    init_database(db_path)
    seed_employees(db_path)
    return db_path


@pytest.fixture
def client(test_db):
    """
    FastAPI TestClient med testdatabase.

    Patcher DEFAULT_DB_PATH slik at lifespan-funksjonen
    (init_database + HRAnalytics) bruker testdatabasen.
    Patcher også i import_routes (som viser DB-sti i /api/status).
    """
    import web.app as web_app_module
    import web.routes.import_routes as import_routes_module

    # Patch DEFAULT_DB_PATH OVERALT — inkludert i database-modulen
    # som brukes av init_database() og HRAnalytics() i lifespan.
    with patch("hr.database.DEFAULT_DB_PATH", test_db), \
         patch.object(import_routes_module, "DEFAULT_DB_PATH", test_db):

        with TestClient(web_app_module.app, raise_server_exceptions=False) as c:
            # Etter lifespan har kjørt, sørg for at analytics bruker testdatabasen
            web_app_module.analytics = HRAnalytics(db_path=test_db)
            yield c


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------

def assert_json_ok(response, expected_status=200):
    """Verifiser at respons er gyldig JSON med riktig statuskode."""
    assert response.status_code == expected_status, (
        f"Forventet {expected_status}, fikk {response.status_code}: {response.text[:200]}"
    )
    return response.json()


# ===========================================================================
# OVERSIKT
# ===========================================================================

class TestOverview:
    """Tester for /api/overview/* endepunkter."""

    def test_summary(self, client):
        data = assert_json_ok(client.get("/api/overview/summary"))
        assert "aktive" in data
        assert "nye_siste_3_mnd" in data
        assert "sluttede" in data
        assert "gjennomsnitt_alder" in data


# ===========================================================================
# CHURN
# ===========================================================================

class TestChurn:
    """Tester for /api/churn/* endepunkter."""

    def test_calculate_total(self, client):
        data = assert_json_ok(client.get(
            "/api/churn/calculate?start_date=2024-01-01&end_date=2025-12-31"
        ))
        assert isinstance(data, dict)

    def test_calculate_by_country(self, client):
        data = assert_json_ok(client.get(
            "/api/churn/calculate?start_date=2024-01-01&end_date=2025-12-31&by=country"
        ))

    def test_calculate_missing_params(self, client):
        """Manglende obligatoriske parametere gir 422."""
        resp = client.get("/api/churn/calculate")
        assert resp.status_code == 422

    def test_monthly(self, client):
        data = assert_json_ok(client.get("/api/churn/monthly?year=2025"))
        assert isinstance(data, list)

    def test_monthly_default_year(self, client):
        """Uten year-parameter brukes inneværende år."""
        data = assert_json_ok(client.get("/api/churn/monthly"))
        assert isinstance(data, list)

    def test_by_age(self, client):
        data = assert_json_ok(client.get(
            "/api/churn/by-age?start_date=2024-01-01&end_date=2025-12-31"
        ))

    def test_by_country(self, client):
        data = assert_json_ok(client.get(
            "/api/churn/by-country?start_date=2024-01-01&end_date=2025-12-31"
        ))

    def test_by_gender(self, client):
        data = assert_json_ok(client.get(
            "/api/churn/by-gender?start_date=2024-01-01&end_date=2025-12-31"
        ))

    def test_reasons(self, client):
        data = assert_json_ok(client.get("/api/churn/reasons"))
        assert isinstance(data, dict)

    def test_reasons_with_dates(self, client):
        data = assert_json_ok(client.get(
            "/api/churn/reasons?start_date=2024-01-01&end_date=2025-12-31"
        ))
        assert isinstance(data, dict)


# ===========================================================================
# TENURE
# ===========================================================================

class TestTenure:
    """Tester for /api/tenure/* endepunkter."""

    def test_average(self, client):
        data = assert_json_ok(client.get("/api/tenure/average"))
        assert "gjennomsnitt_ar" in data
        assert isinstance(data["gjennomsnitt_ar"], (int, float))

    def test_distribution(self, client):
        data = assert_json_ok(client.get("/api/tenure/distribution"))
        assert isinstance(data, dict)


# ===========================================================================
# ANSETTELSESTYPE
# ===========================================================================

class TestEmployment:
    """Tester for /api/employment/* endepunkter."""

    def test_types(self, client):
        data = assert_json_ok(client.get("/api/employment/types"))
        assert isinstance(data, dict)

    def test_fulltime_parttime(self, client):
        data = assert_json_ok(client.get("/api/employment/fulltime-parttime"))
        assert isinstance(data, dict)


# ===========================================================================
# LEDELSE
# ===========================================================================

class TestManagement:
    """Tester for /api/management/* endepunkter."""

    def test_ratio(self, client):
        data = assert_json_ok(client.get("/api/management/ratio"))
        assert isinstance(data, dict)


# ===========================================================================
# SØK
# ===========================================================================

class TestSearch:
    """Tester for /api/search endepunktet."""

    def test_search_by_name(self, client):
        data = assert_json_ok(client.get("/api/search?name=Ola"))
        assert isinstance(data, list)
        assert len(data) >= 1
        # Ola Nordmann skal finnes
        names = [f"{d.get('fornavn', '')} {d.get('etternavn', '')}" for d in data]
        assert any("Ola" in n for n in names)

    def test_search_by_department(self, client):
        data = assert_json_ok(client.get("/api/search?department=Regnskap"))
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_search_by_country(self, client):
        data = assert_json_ok(client.get("/api/search?country=Danmark"))
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_search_no_results(self, client):
        data = assert_json_ok(client.get("/api/search?name=Xyznonexistent"))
        assert isinstance(data, list)
        assert len(data) == 0

    def test_search_with_limit(self, client):
        data = assert_json_ok(client.get("/api/search?limit=2"))
        assert isinstance(data, list)
        assert len(data) <= 2


# ===========================================================================
# PLANLAGTE AVGANGER
# ===========================================================================

class TestDepartures:
    """Tester for /api/departures/* endepunkter."""

    def test_planned(self, client):
        data = assert_json_ok(client.get("/api/departures/planned"))
        assert isinstance(data, list)

    def test_planned_short_horizon(self, client):
        data = assert_json_ok(client.get("/api/departures/planned?months_ahead=1"))
        assert isinstance(data, list)


# ===========================================================================
# LØNN
# ===========================================================================

class TestSalary:
    """Tester for /api/salary/* endepunkter."""

    def test_summary(self, client):
        data = assert_json_ok(client.get("/api/salary/summary"))
        assert isinstance(data, dict)

    def test_by_gender(self, client):
        data = assert_json_ok(client.get("/api/salary/by-gender"))
        assert isinstance(data, dict)

    def test_by_department(self, client):
        data = assert_json_ok(client.get("/api/salary/by-department"))
        assert isinstance(data, dict)
        # Alle verdier har gjennomsnitt, min, maks
        for key, val in data.items():
            assert 'gjennomsnitt' in val
            assert 'min' in val
            assert 'maks' in val

    def test_by_country(self, client):
        data = assert_json_ok(client.get("/api/salary/by-country"))
        assert isinstance(data, dict)

    def test_by_age(self, client):
        data = assert_json_ok(client.get("/api/salary/by-age"))
        assert isinstance(data, dict)

    def test_by_job_family(self, client):
        data = assert_json_ok(client.get("/api/salary/by-job-family"))
        assert isinstance(data, dict)

    @pytest.mark.parametrize("endpoint", [
        "/api/salary/summary",
        "/api/salary/by-gender",
        "/api/salary/by-department",
        "/api/salary/by-country",
        "/api/salary/by-age",
        "/api/salary/by-job-family",
    ])
    def test_salary_active_only_false(self, client, endpoint):
        """Alle lønnsendepunkter aksepterer active_only=false."""
        data = assert_json_ok(client.get(f"{endpoint}?active_only=false"))
        assert isinstance(data, dict)


# ===========================================================================
# IMPORT
# ===========================================================================

class TestImport:
    """Tester for /api/import/* endepunkter."""

    def test_upload_invalid_filetype(self, client):
        """Avvis filer som ikke er Excel."""
        resp = client.post(
            "/api/import/upload",
            files={"file": ("test.txt", b"not excel", "text/plain")},
        )
        assert resp.status_code == 400
        assert "Excel" in resp.json()["detail"]

    def test_upload_no_file(self, client):
        """Manglende fil gir 422."""
        resp = client.post("/api/import/upload")
        assert resp.status_code == 422

    def test_history(self, client):
        data = assert_json_ok(client.get("/api/import/history"))
        assert isinstance(data, list)

    def _make_excel(self, headers, rows=None):
        """Lag en minimal Excel-fil i minnet med gitt header-rad."""
        wb = openpyxl.Workbook()
        ws = wb.active
        # Row 1: category header (ignored by importer, which reads header=1)
        ws.append(["Grunnleggende informasjon"] + [None] * (len(headers) - 1))
        # Row 2: actual column headers
        ws.append(headers)
        # Row 3+: data rows
        if rows:
            for row in rows:
                ws.append(row)
        else:
            ws.append([f"val{i}" for i in range(len(headers))])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue()

    def test_upload_returns_validation(self, client):
        """Suksessfull import returnerer valideringsinfo."""
        excel = self._make_excel(["Fornavn", "Etternavn", "Medarbeidernummer"],
                                 [["Ola", "Nordmann", "TEST001"]])
        resp = client.post(
            "/api/import/upload",
            files={"file": ("test.xlsx", excel,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        data = assert_json_ok(resp)
        assert "validering" in data
        v = data["validering"]
        assert v["matchede_kolonner"] == 3
        assert v["match_prosent"] > 0
        assert isinstance(v["manglende"], list)

    def test_upload_partial_match_has_warnings(self, client):
        """Delvis match gir advarsler i respons."""
        # Only 2 of ~52 expected columns => very low match => warning
        excel = self._make_excel(["Fornavn", "Etternavn"],
                                 [["Ola", "Nordmann"]])
        resp = client.post(
            "/api/import/upload",
            files={"file": ("partial.xlsx", excel,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        data = assert_json_ok(resp)
        assert "advarsler" in data
        assert len(data["advarsler"]) > 0
        assert data["validering"]["match_prosent"] < 50


# ===========================================================================
# STATUS
# ===========================================================================

class TestStatus:
    """Tester for /api/status endepunktet."""

    def test_status(self, client):
        data = assert_json_ok(client.get("/api/status"))
        assert "totalt_ansatte" in data
        assert "aktive_ansatte" in data
        assert data["aktive_ansatte"] == 8


# ===========================================================================
# RAPPORT
# ===========================================================================

class TestReport:
    """Tester for /api/report/* endepunkter."""

    def test_pdf_generation(self, client):
        """Generer PDF-rapport og verifiser respons."""
        resp = client.get("/api/report/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF starter alltid med %PDF
        assert resp.content[:4] == b"%PDF"

    def test_pdf_with_year(self, client):
        """Generer PDF med spesifikt år."""
        resp = client.get("/api/report/pdf?year=2025")
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"


# ===========================================================================
# FRONTEND
# ===========================================================================

class TestFrontend:
    """Tester for frontend-servering."""

    def test_index_page(self, client):
        """Hovedsiden returnerer HTML."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "HR Analyse" in resp.text

    def test_static_css(self, client):
        """CSS-filen er tilgjengelig."""
        resp = client.get("/static/css/style.css")
        assert resp.status_code == 200

    def test_static_js_app(self, client):
        """app.js er tilgjengelig."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200

    def test_static_js_charts(self, client):
        """charts.js er tilgjengelig."""
        resp = client.get("/static/js/charts.js")
        assert resp.status_code == 200

    def test_static_chartjs(self, client):
        """Chart.js-biblioteket er tilgjengelig."""
        resp = client.get("/static/js/chart.min.js")
        assert resp.status_code == 200

    def test_swagger_docs(self, client):
        """Swagger UI er tilgjengelig."""
        resp = client.get("/docs")
        assert resp.status_code == 200


# ===========================================================================
# ACTIVE_ONLY-PARAMETER
# ===========================================================================

# ===========================================================================
# ANALYSE (Custom Analysis Builder)
# ===========================================================================

class TestAnalyze:
    """Tester for /api/analyze/* endepunkter."""

    def test_analyze_count_by_kjonn(self, client):
        """Enkel analyse: count per kjønn."""
        data = assert_json_ok(client.get("/api/analyze?metric=count&group_by=kjonn"))
        assert "meta" in data
        assert "data" in data
        assert data["meta"]["metric"] == "count"
        assert data["meta"]["group_by"] == "kjonn"
        assert isinstance(data["data"], dict)
        assert len(data["data"]) > 0

    def test_analyze_avg_salary_by_avdeling(self, client):
        """Gjennomsnittslønn per avdeling."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=avg_salary&group_by=avdeling"
        ))
        assert data["meta"]["metric_label"] == "Gjennomsnittslønn"
        for val in data["data"].values():
            assert isinstance(val, (int, float))

    def test_analyze_with_split_by(self, client):
        """Analyse med to dimensjoner (split_by)."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling&split_by=kjonn"
        ))
        assert data["meta"]["split_by"] == "kjonn"
        assert data["meta"]["split_by_label"] == "Kjønn"
        # data bør være nested: {avdeling: {kjønn: antall}}
        for group, splits in data["data"].items():
            assert isinstance(splits, dict)

    def test_analyze_with_filter(self, client):
        """Analyse med filter."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling&filter_arbeidsland=Norge"
        ))
        # Kun norske ansatte
        total = sum(data["data"].values())
        assert total > 0

    def test_analyze_aldersgruppe(self, client):
        """Aldersgruppe som dimensjon."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=aldersgruppe"
        ))
        valid_groups = {"Under 25", "25-34", "35-44", "45-54", "55-64", "65+", "Ukjent"}
        for group in data["data"].keys():
            assert group in valid_groups

    def test_analyze_invalid_metric(self, client):
        """Ugyldig metrikk gir 400."""
        resp = client.get("/api/analyze?metric=invalid&group_by=kjonn")
        assert resp.status_code == 400
        assert "Ugyldig metrikk" in resp.json()["detail"]

    def test_analyze_invalid_group_by(self, client):
        """Ugyldig gruppering gir 400."""
        resp = client.get("/api/analyze?metric=count&group_by=invalid")
        assert resp.status_code == 400
        assert "Ugyldig gruppering" in resp.json()["detail"]

    def test_analyze_invalid_split_by(self, client):
        """Ugyldig inndeling gir 400."""
        resp = client.get(
            "/api/analyze?metric=count&group_by=kjonn&split_by=invalid"
        )
        assert resp.status_code == 400
        assert "Ugyldig inndeling" in resp.json()["detail"]

    def test_analyze_missing_required(self, client):
        """Manglende obligatoriske params gir 422."""
        resp = client.get("/api/analyze")
        assert resp.status_code == 422

    def test_analyze_options(self, client):
        """Options-endepunkt returnerer forventet struktur."""
        data = assert_json_ok(client.get("/api/analyze/options"))
        assert "metrics" in data
        assert "dimensions" in data
        assert "filter_dimensions" in data
        assert "filter_values" in data
        # Sjekk at metrics er en liste med id/label
        assert len(data["metrics"]) > 0
        assert "id" in data["metrics"][0]
        assert "label" in data["metrics"][0]
        # Sjekk filter_values inneholder nøkler
        assert isinstance(data["filter_values"], dict)
        assert "kjonn" in data["filter_values"]

    def test_analyze_active_only_false(self, client):
        """active_only=false inkluderer sluttede."""
        active = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=kjonn"
        ))
        all_emps = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=kjonn&active_only=false"
        ))
        active_total = sum(active["data"].values())
        all_total = sum(all_emps["data"].values())
        assert all_total >= active_total

    def test_analyze_alle_total(self, client):
        """group_by=alle returnerer én totalverdi."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle"
        ))
        assert data["meta"]["group_by"] == "alle"
        assert data["meta"]["group_by_label"] == "Alle (total)"
        assert "Alle" in data["data"]
        assert isinstance(data["data"]["Alle"], int)
        assert data["data"]["Alle"] > 0

    def test_analyze_alle_with_filter(self, client):
        """group_by=alle med filter returnerer filtrert total."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&filter_arbeidsland=Norge"
        ))
        assert "Alle" in data["data"]
        assert data["data"]["Alle"] > 0

    def test_analyze_options_includes_alle(self, client):
        """Options inkluderer 'alle' som siste dimensjon."""
        data = assert_json_ok(client.get("/api/analyze/options"))
        dims = data["dimensions"]
        assert dims[-1]["id"] == "alle"
        assert dims[-1]["label"] == "Alle (total)"

    # --- Nye metrikker ---

    def test_analyze_avg_tenure(self, client):
        """avg_tenure returnerer ansiennitet i år."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=avg_tenure&group_by=avdeling"
        ))
        assert data["meta"]["metric"] == "avg_tenure"
        assert data["meta"]["metric_label"] == "Snitt ansiennitet (år)"
        for val in data["data"].values():
            assert isinstance(val, (int, float))

    def test_analyze_avg_work_hours(self, client):
        """avg_work_hours returnerer arbeidstid."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=avg_work_hours&group_by=avdeling"
        ))
        assert data["meta"]["metric"] == "avg_work_hours"
        for val in data["data"].values():
            assert isinstance(val, (int, float))
            assert val > 0

    def test_analyze_pct_female(self, client):
        """pct_female returnerer andel kvinner i prosent."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=pct_female&group_by=avdeling"
        ))
        assert data["meta"]["metric"] == "pct_female"
        for val in data["data"].values():
            assert 0 <= val <= 100

    def test_analyze_pct_leaders(self, client):
        """pct_leaders returnerer andel ledere i prosent."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=pct_leaders&group_by=avdeling"
        ))
        assert data["meta"]["metric"] == "pct_leaders"
        for val in data["data"].values():
            assert 0 <= val <= 100

    # --- Nye dimensjoner ---

    def test_analyze_tenure_gruppe(self, client):
        """tenure_gruppe som dimensjon."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=tenure_gruppe"
        ))
        valid_groups = {"Under 1 år", "1-2 år", "2-5 år", "5-10 år", "Over 10 år", "Ukjent"}
        for group in data["data"].keys():
            assert group in valid_groups

    def test_analyze_nasjonalitet(self, client):
        """nasjonalitet som dimensjon."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=nasjonalitet"
        ))
        assert len(data["data"]) > 0

    def test_analyze_ansettelsesniva(self, client):
        """ansettelsesniva som dimensjon."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=ansettelsesniva"
        ))
        assert len(data["data"]) > 0

    def test_analyze_arbeidssted(self, client):
        """arbeidssted som dimensjon."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=arbeidssted"
        ))
        assert len(data["data"]) > 0

    def test_analyze_options_includes_new_metrics(self, client):
        """Options inkluderer nye metrikker."""
        data = assert_json_ok(client.get("/api/analyze/options"))
        metric_ids = [m["id"] for m in data["metrics"]]
        assert "avg_tenure" in metric_ids
        assert "avg_work_hours" in metric_ids
        assert "pct_female" in metric_ids
        assert "pct_leaders" in metric_ids

    def test_analyze_options_includes_new_dimensions(self, client):
        """Options inkluderer nye dimensjoner."""
        data = assert_json_ok(client.get("/api/analyze/options"))
        dim_ids = [d["id"] for d in data["dimensions"]]
        assert "tenure_gruppe" in dim_ids
        assert "ansettelsesniva" in dim_ids
        assert "nasjonalitet" in dim_ids
        assert "arbeidssted" in dim_ids

    def test_analyze_filter_nasjonalitet(self, client):
        """Filter på nasjonalitet fungerer."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling&filter_nasjonalitet=Norsk"
        ))
        assert len(data["data"]) > 0

    def test_analyze_group_by_divisjon(self, client):
        """Gruppering per divisjon fungerer."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=divisjon"
        ))
        assert "Økonomi" in data["data"]
        assert "Teknologi" in data["data"]
        assert data["meta"]["group_by_label"] == "Divisjon"

    def test_analyze_group_by_rolle(self, client):
        """Gruppering per rolle fungerer."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=rolle"
        ))
        assert "Regnskapsfører" in data["data"]
        assert data["meta"]["group_by_label"] == "Rolle"

    def test_analyze_filter_divisjon(self, client):
        """Filter på divisjon fungerer."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&filter_divisjon=Teknologi"
        ))
        # Teknologi: Erik, Morten, Vidar (alle aktive)
        assert data["data"]["Alle"] == 3

    def test_analyze_filter_rolle(self, client):
        """Filter på rolle fungerer."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&filter_rolle=Leder"
        ))
        # Aktive ledere: Kari, Lars
        assert data["data"]["Alle"] == 2

    def test_analyze_options_includes_divisjon_rolle(self, client):
        """Options-endepunkt inkluderer divisjon og rolle."""
        data = assert_json_ok(client.get("/api/analyze/options"))
        dim_ids = [d["id"] for d in data["dimensions"]]
        filter_dim_ids = [d["id"] for d in data["filter_dimensions"]]
        assert "divisjon" in dim_ids
        assert "rolle" in dim_ids
        assert "divisjon" in filter_dim_ids
        assert "rolle" in filter_dim_ids
        assert "divisjon" in data["filter_values"]
        assert "rolle" in data["filter_values"]

    # ----- date_as_of snapshot tests -----

    def test_analyze_date_as_of_snapshot(self, client):
        """Snapshot per 2025-01-01: Lise (sluttet 2024-12-31) er ekskludert, Per (slutter 2025-06-30) er med."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&date_as_of=2025-01-01"
        ))
        # 10 total minus Lise = 9
        assert data["data"]["Alle"] == 9
        assert data["meta"]["date_as_of"] == "2025-01-01"

    def test_analyze_date_as_of_excludes_not_yet_started(self, client):
        """Snapshot per 2020-06-01: bare ansatte startet før/på denne datoen."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&date_as_of=2020-06-01"
        ))
        # Started on or before 2020-06-01 with end NULL or end > 2020-06-01:
        # Ola (2020-01-01), Kari (2018-06-01), Erik (2015-03-15),
        # Lars (2019-08-01), Per (2017-01-15), Lise (2020-03-01), Vidar (2010-01-01)
        # Sofia started 2021-02-01 → NOT included, Anna 2022-01-10 → NOT, Morten 2024-06-01 → NOT
        assert data["data"]["Alle"] == 7

    def test_analyze_date_as_of_with_filter(self, client):
        """Snapshot med filter fungerer sammen."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling&date_as_of=2025-01-01"
            "&filter_arbeidsland=Norge"
        ))
        # Norge-ansatte per 2025-01-01: Ola, Kari, Erik, Per, Morten, Vidar = 6
        # (Lise er dansk og sluttet, men er DK uansett)
        total = sum(data["data"].values())
        assert total == 6

    def test_analyze_date_as_of_avg_tenure(self, client):
        """avg_tenure med date_as_of bruker snapshot-datoen for beregning."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=avg_tenure&group_by=alle&date_as_of=2025-01-01"
        ))
        # Skal returnere et tall > 0
        assert data["data"]["Alle"] > 0
        assert data["meta"]["date_as_of"] == "2025-01-01"

    def test_analyze_date_as_of_invalid_format(self, client):
        """Ugyldig datoformat gir 400."""
        resp = client.get(
            "/api/analyze?metric=count&group_by=alle&date_as_of=01-01-2025"
        )
        assert resp.status_code == 400

    def test_analyze_date_as_of_options(self, client):
        """Filter-options med date_as_of returnerer verdier for aktive per snapshot."""
        data = assert_json_ok(client.get(
            "/api/analyze/options?date_as_of=2020-06-01"
        ))
        # Skal ha filter_values med arbeidsland osv.
        assert "filter_values" in data
        # Per 2020-06-01: ingen svenske (Sofia startet 2021-02-01)
        arbeidsland_vals = data["filter_values"].get("arbeidsland", [])
        assert "Sverige" not in arbeidsland_vals
        assert "Norge" in arbeidsland_vals


class TestMultiSelectFilters:
    """Tester for multi-select filtre (kommaseparerte verdier)."""

    def test_multi_value_single_dimension(self, client):
        """Flervalg på én dimensjon: filter_arbeidsland=Norge,Danmark."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=arbeidsland&filter_arbeidsland=Norge,Danmark"
        ))
        # Kun Norge og Danmark skal være i resultatet
        assert set(data["data"].keys()) <= {"Norge", "Danmark"}
        assert "Sverige" not in data["data"]
        # Skal finne ansatte i begge land
        total = sum(data["data"].values())
        assert total > 0

    def test_multi_value_two_countries(self, client):
        """Flervalg: Norge+Sverige — teller aktive ansatte."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=arbeidsland&filter_arbeidsland=Norge,Sverige"
        ))
        assert "Norge" in data["data"]
        assert "Sverige" in data["data"]
        assert "Danmark" not in data["data"]

    def test_multi_value_multiple_dimensions(self, client):
        """Filtre på to dimensjoner samtidig (AND-logikk mellom dimensjoner)."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling"
            "&filter_arbeidsland=Norge&filter_kjonn=Mann"
        ))
        # Bare norske menn — summen skal være > 0
        total = sum(data["data"].values())
        assert total > 0
        # Norske menn i testdata: Ola (Regnskap), Erik (IT), Morten (IT), Vidar (IT)
        assert total <= 4

    def test_multi_value_with_split_by(self, client):
        """Flervalg-filter med split_by fungerer."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling&split_by=kjonn"
            "&filter_arbeidsland=Norge,Danmark"
        ))
        # Bør ha nested data
        for group, splits in data["data"].items():
            assert isinstance(splits, dict)

    def test_single_value_still_works(self, client):
        """Enkeltverdi-filter (uten komma) fungerer fortsatt."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=avdeling&filter_arbeidsland=Norge"
        ))
        total = sum(data["data"].values())
        assert total > 0

    def test_multi_value_with_date_as_of(self, client):
        """Flervalg-filter med date_as_of snapshot."""
        data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=arbeidsland"
            "&filter_arbeidsland=Norge,Danmark&date_as_of=2024-06-01"
        ))
        # Per 2024-06-01: Lise (DK) er fortsatt aktiv, Per (NO) er aktiv
        total = sum(data["data"].values())
        assert total > 0

    def test_multi_value_count_accuracy(self, client):
        """Verifier eksakt telling med flervalg-filter."""
        # Bare Norge, aktive
        no_data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&filter_arbeidsland=Norge"
        ))
        # Bare Danmark, aktive
        dk_data = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&filter_arbeidsland=Danmark"
        ))
        # Norge + Danmark kombinerert
        combined = assert_json_ok(client.get(
            "/api/analyze?metric=count&group_by=alle&filter_arbeidsland=Norge,Danmark"
        ))
        no_count = list(no_data["data"].values())[0]
        dk_count = list(dk_data["data"].values())[0]
        combined_count = list(combined["data"].values())[0]
        assert combined_count == no_count + dk_count


class TestActiveOnlyParam:
    """Verifiser at active_only-parameteren fungerer på tvers av endepunkter."""

    @pytest.mark.parametrize("endpoint", [
        "/api/tenure/average",
        "/api/tenure/distribution",
        "/api/employment/types",
        "/api/employment/fulltime-parttime",
        "/api/management/ratio",
        "/api/salary/summary",
        "/api/salary/by-gender",
    ])
    def test_active_only_false(self, client, endpoint):
        """Alle endepunkter med active_only aksepterer false."""
        resp = client.get(f"{endpoint}?active_only=false")
        assert resp.status_code == 200, f"{endpoint} feilet: {resp.text[:200]}"
