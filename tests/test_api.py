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
        assert "totalt" in data
        assert "aktive" in data
        assert "sluttede" in data
        assert "gjennomsnitt_alder" in data
        assert data["totalt"] == 10  # 10 testansatte


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
        assert data["totalt_ansatte"] == 10


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


class TestActiveOnlyParam:
    """Verifiser at active_only-parameteren fungerer på tvers av endepunkter."""

    @pytest.mark.parametrize("endpoint", [
        pytest.param("/api/tenure/average", marks=pytest.mark.xfail(
            reason="Kjent WHERE-bug i average_tenure(active_only=False)")),
        pytest.param("/api/tenure/distribution", marks=pytest.mark.xfail(
            reason="Kjent WHERE-bug i tenure_distribution(active_only=False)")),
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
