"""
Tester for den generiske analyse-motoren (hr/analyzer.py).

Dekker query-bygging, validering, kjøring mot testdata,
og henting av filterverdier.
"""

import pytest

from hr.analyzer import (
    build_analysis_query, run_analysis, get_filter_values,
    METRICS, DIMENSIONS, FILTERS, AGE_CASE_EXPR,
)


# ===========================================================================
# build_analysis_query — SQL-bygging
# ===========================================================================

class TestBuildQuery:
    """Tester for build_analysis_query()."""

    def test_single_dimension(self):
        """Enkel gruppering: count per kjønn."""
        sql, params = build_analysis_query(metric="count", group_by="kjonn")
        assert "COUNT(*) AS verdi" in sql
        assert "GROUP BY gruppe" in sql
        assert "COALESCE(kjonn, 'Ukjent') AS gruppe" in sql
        assert "er_aktiv = 1" in sql
        assert params == ()

    def test_two_dimensions(self):
        """Gruppering + inndeling: count per avdeling, splittet på kjønn."""
        sql, params = build_analysis_query(
            metric="count", group_by="avdeling", split_by="kjonn"
        )
        assert "AS gruppe" in sql
        assert "AS inndeling" in sql
        assert "GROUP BY gruppe, inndeling" in sql

    def test_with_filter(self):
        """Filter legger til WHERE-klausul med parameterisert verdi."""
        sql, params = build_analysis_query(
            metric="avg_salary", group_by="avdeling",
            filters={"arbeidsland": "Norge"}
        )
        assert "arbeidsland = ?" in sql
        assert "lonn IS NOT NULL" in sql
        assert params == ("Norge",)

    def test_multiple_filters(self):
        """Flere filtre kombineres med AND."""
        sql, params = build_analysis_query(
            metric="count", group_by="avdeling",
            filters={"arbeidsland": "Norge", "kjonn": "Mann"}
        )
        assert "arbeidsland = ?" in sql
        assert "kjonn = ?" in sql
        assert len(params) == 2

    def test_aldersgruppe_uses_case(self):
        """Aldersgruppe-dimensjon bruker CASE-uttrykk i stedet for kolonnenavn."""
        sql, params = build_analysis_query(metric="count", group_by="aldersgruppe")
        assert "CASE" in sql
        assert "WHEN alder" in sql
        assert "alder IS NOT NULL" in sql

    def test_aldersgruppe_as_split_by(self):
        """Aldersgruppe som split_by bruker CASE-uttrykk."""
        sql, params = build_analysis_query(
            metric="count", group_by="avdeling", split_by="aldersgruppe"
        )
        assert "CASE" in sql
        assert "alder IS NOT NULL" in sql

    def test_salary_metric_filters_null_lonn(self):
        """Lønnsmetrikker legger til 'lonn IS NOT NULL'."""
        for m in ["avg_salary", "min_salary", "max_salary", "sum_salary"]:
            sql, _ = build_analysis_query(metric=m, group_by="avdeling")
            assert "lonn IS NOT NULL" in sql, f"Mangler lonn-filter for {m}"

    def test_avg_age_filters_null_alder(self):
        """avg_age legger til 'alder IS NOT NULL'."""
        sql, _ = build_analysis_query(metric="avg_age", group_by="avdeling")
        assert "alder IS NOT NULL" in sql

    def test_active_only_false(self):
        """active_only=False utelater er_aktiv-filteret."""
        sql, _ = build_analysis_query(
            metric="count", group_by="kjonn", active_only=False
        )
        assert "er_aktiv" not in sql

    def test_invalid_metric_raises(self):
        """Ugyldig metrikk gir ValueError."""
        with pytest.raises(ValueError, match="Ugyldig metrikk"):
            build_analysis_query(metric="invalid", group_by="kjonn")

    def test_invalid_group_by_raises(self):
        """Ugyldig gruppering gir ValueError."""
        with pytest.raises(ValueError, match="Ugyldig gruppering"):
            build_analysis_query(metric="count", group_by="invalid")

    def test_invalid_split_by_raises(self):
        """Ugyldig inndeling gir ValueError."""
        with pytest.raises(ValueError, match="Ugyldig inndeling"):
            build_analysis_query(metric="count", group_by="kjonn", split_by="invalid")

    def test_invalid_filter_key_raises(self):
        """Ugyldig filter-nøkkel gir ValueError."""
        with pytest.raises(ValueError, match="Ugyldig filter"):
            build_analysis_query(
                metric="count", group_by="kjonn",
                filters={"aldersgruppe": "25-34"}  # aldersgruppe er ikke filtrerbar
            )


# ===========================================================================
# run_analysis — kjøring mot testdata
# ===========================================================================

class TestRunAnalysis:
    """Tester for run_analysis() med ekte testdata."""

    def test_count_by_kjonn(self, test_db):
        """Count per kjønn returnerer riktig format."""
        result = run_analysis(
            metric="count", group_by="kjonn", db_path=test_db
        )
        assert "meta" in result
        assert "data" in result
        assert result["meta"]["metric"] == "count"
        assert result["meta"]["metric_label"] == "Antall ansatte"
        assert result["meta"]["group_by"] == "kjonn"
        assert result["meta"]["split_by"] is None

        # Testdata: 6 menn og 4 kvinner er aktive (Per sluttet, Lise sluttet)
        # Aktive: Ola, Kari, Erik, Anna, Lars, Sofia, Morten, Vidar = 5 menn + 3 kvinner
        data = result["data"]
        assert "Mann" in data
        assert "Kvinne" in data
        assert isinstance(data["Mann"], int)

    def test_avg_salary_by_avdeling(self, test_db):
        """Gjennomsnittslønn per avdeling returnerer tall."""
        result = run_analysis(
            metric="avg_salary", group_by="avdeling", db_path=test_db
        )
        data = result["data"]
        assert len(data) > 0
        for key, val in data.items():
            assert isinstance(val, (int, float))
            assert val > 0

    def test_two_dimensions(self, test_db):
        """To dimensjoner returnerer nested dict."""
        result = run_analysis(
            metric="count", group_by="avdeling", split_by="kjonn",
            db_path=test_db
        )
        assert result["meta"]["split_by"] == "kjonn"
        assert result["meta"]["split_by_label"] == "Kjønn"

        data = result["data"]
        # data skal være {avdeling: {kjønn: antall}}
        for group, splits in data.items():
            assert isinstance(splits, dict)
            for split_key, val in splits.items():
                assert isinstance(val, (int, float))

    def test_with_filter(self, test_db):
        """Filter begrenser resultater korrekt."""
        # Bare Norge → 6 aktive fra Norge (Ola, Kari, Erik, Morten, Vidar + Per sluttet)
        result = run_analysis(
            metric="count", group_by="avdeling",
            filters={"arbeidsland": "Norge"},
            db_path=test_db
        )
        total = sum(result["data"].values())
        # Aktive i Norge: Ola, Kari, Erik, Morten, Vidar = 5
        assert total == 5

    def test_count_active_vs_all(self, test_db):
        """active_only=False inkluderer sluttede ansatte."""
        active = run_analysis(
            metric="count", group_by="kjonn", db_path=test_db
        )
        all_emps = run_analysis(
            metric="count", group_by="kjonn",
            active_only=False, db_path=test_db
        )
        active_total = sum(active["data"].values())
        all_total = sum(all_emps["data"].values())
        assert all_total > active_total

    def test_aldersgruppe_dimension(self, test_db):
        """Aldersgruppe-dimensjon returnerer beregnede grupper."""
        result = run_analysis(
            metric="count", group_by="aldersgruppe", db_path=test_db
        )
        data = result["data"]
        # Forventede grupper basert på testdata (aldre: 30,42,55,28,35,38,24,48,33,62)
        # Aktive: 30,42,55,28,35,38,24,62
        valid_groups = {"Under 25", "25-34", "35-44", "45-54", "55-64", "65+", "Ukjent"}
        for group in data.keys():
            assert group in valid_groups, f"Uventet aldersgruppe: {group}"


# ===========================================================================
# get_filter_values
# ===========================================================================

class TestGetFilterValues:
    """Tester for get_filter_values()."""

    def test_returns_all_filter_dimensions(self, test_db):
        """Returnerer verdier for alle filtrerbare dimensjoner."""
        result = get_filter_values(db_path=test_db)
        for key in FILTERS:
            assert key in result, f"Mangler filterdimensjon: {key}"
            assert isinstance(result[key], list)

    def test_kjonn_values(self, test_db):
        """Kjønn-filter inneholder forventede verdier."""
        result = get_filter_values(db_path=test_db)
        assert "Mann" in result["kjonn"]
        assert "Kvinne" in result["kjonn"]

    def test_active_only_excludes_terminated(self, test_db):
        """active_only filtrerer bort sluttede ansattes verdier."""
        active = get_filter_values(db_path=test_db, active_only=True)
        all_vals = get_filter_values(db_path=test_db, active_only=False)
        # Alle unike verdier med active_only=False bør være >= active_only=True
        for key in FILTERS:
            assert len(all_vals[key]) >= len(active[key])


# ===========================================================================
# Whitelists — integritetstester
# ===========================================================================

class TestWhitelists:
    """Verifiser at whitelists er konsistente."""

    def test_filters_subset_of_dimensions(self):
        """Alle filter-nøkler finnes i DIMENSIONS."""
        for key in FILTERS:
            assert key in DIMENSIONS

    def test_aldersgruppe_not_in_filters(self):
        """aldersgruppe er en beregnet dimensjon og skal ikke være filtrerbar."""
        assert "aldersgruppe" not in FILTERS

    def test_all_metrics_have_labels(self):
        """Alle metrikker har SQL-funksjon og visningsnavn."""
        for key, (sql_func, label) in METRICS.items():
            assert len(sql_func) > 0
            assert len(label) > 0

    def test_all_dimensions_have_labels(self):
        """Alle dimensjoner har visningsnavn."""
        for key, (col, label) in DIMENSIONS.items():
            assert len(label) > 0
