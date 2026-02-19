"""
Tests for hr_database.analytics module.

Test data (from conftest.py) contains 10 employees:
  - 6 in Norge, 3 in Danmark, 1 in Sverige
  - Active: 8 (M008 terminated 2025-06-30, M009 terminated 2024-12-31)
    Note: M010 has slutdato 2027-06-30 (future) so is active
  - Genders: 6 Mann, 4 Kvinne
  - Ages: 24, 28, 30, 33, 35, 38, 42, 48, 55, 62
  - Companies: ECIT AS (4), ECIT DK (3), ECIT Consulting (2), ECIT SE (1)
  - Departments: Regnskap (6), IT (3), Salg (1)
  - Leaders: 2 (Kari M002, Lars M005)
"""

from datetime import date

import pytest


# =========================================================================
# Basic stats
# =========================================================================

class TestTotalEmployees:

    def test_active_count(self, analytics):
        # M008 (slutt 2025-06-30) and M009 (slutt 2024-12-31) are inactive
        # M010 (slutt 2027-06-30) is active (future date)
        assert analytics.total_employees(active_only=True) == 8

    def test_total_count(self, analytics):
        assert analytics.total_employees(active_only=False) == 10


class TestEmployeesSummary:

    def test_summary_keys(self, analytics):
        summary = analytics.employees_summary()
        assert "totalt" in summary
        assert "aktive" in summary
        assert "sluttede" in summary
        assert "gjennomsnitt_alder" in summary

    def test_summary_counts(self, analytics):
        summary = analytics.employees_summary()
        assert summary["totalt"] == 10
        assert summary["aktive"] == 8
        assert summary["sluttede"] == 2

    def test_average_age(self, analytics):
        summary = analytics.employees_summary()
        # Active ages: 30, 42, 55, 28, 35, 38, 24, 62 = 314 / 8 = 39.25
        assert summary["gjennomsnitt_alder"] == 39.2


# =========================================================================
# Age analysis
# =========================================================================

class TestAgeDistribution:

    def test_returns_all_categories(self, analytics):
        dist = analytics.age_distribution()
        expected_keys = {"Under 25", "25-34", "35-44", "45-54", "55-64", "65+", "Ukjent"}
        assert set(dist.keys()) == expected_keys

    def test_active_distribution(self, analytics):
        dist = analytics.age_distribution(active_only=True)
        # Active: 24(Under25), 28(25-34), 30(25-34), 35(35-44), 38(35-44), 42(35-44), 55(55-64), 62(55-64)
        assert dist["Under 25"] == 1
        assert dist["25-34"] == 2
        assert dist["35-44"] == 3
        assert dist["45-54"] == 0
        assert dist["55-64"] == 2
        assert dist["65+"] == 0

    def test_percentage(self, analytics):
        pct = analytics.age_distribution_pct(active_only=True)
        assert pct["Under 25"] == 12.5  # 1/8
        total = sum(pct.values())
        assert abs(total - 100.0) < 0.5  # should sum to ~100%


class TestAgeDistributionByCountry:

    def test_returns_countries(self, analytics):
        result = analytics.age_distribution_by_country()
        assert "Norge" in result
        assert "Danmark" in result
        assert "Sverige" in result

    def test_norge_distribution(self, analytics):
        result = analytics.age_distribution_by_country()
        norge = result["Norge"]
        # Active Norge: 30(25-34), 42(35-44), 55(55-64), 24(Under25), 62(55-64) = 5
        assert norge["Under 25"] == 1
        assert norge["25-34"] == 1
        assert norge["35-44"] == 1
        assert norge["55-64"] == 2


# =========================================================================
# Geographic analysis
# =========================================================================

class TestEmployeesByCountry:

    def test_active_by_country(self, analytics):
        by_country = analytics.employees_by_country()
        assert by_country["Norge"] == 5
        assert by_country["Danmark"] == 2
        assert by_country["Sverige"] == 1

    def test_all_by_country(self, analytics):
        by_country = analytics.employees_by_country(active_only=False)
        assert by_country["Norge"] == 6
        assert by_country["Danmark"] == 3
        assert by_country["Sverige"] == 1

    def test_no_duplicate_countries(self, analytics):
        """Regression: GROUP BY land vs arbeidsland bug caused split countries."""
        by_country = analytics.employees_by_country()
        country_names = list(by_country.keys())
        assert len(country_names) == len(set(country_names)), "Duplicate country names found"

    def test_total_matches_employee_count(self, analytics):
        by_country = analytics.employees_by_country()
        total = sum(by_country.values())
        assert total == analytics.total_employees(active_only=True)


class TestEmployeesByCompany:

    def test_active_by_company(self, analytics):
        by_company = analytics.employees_by_company()
        # Active: ECIT AS (Ola, Kari, Morten = 3), ECIT DK (Anna, Lars = 2),
        # ECIT Consulting (Erik, Vidar = 2), ECIT SE (Sofia = 1)
        assert by_company["ECIT AS"] == 3
        assert by_company["ECIT DK"] == 2
        assert by_company["ECIT Consulting"] == 2
        assert by_company["ECIT SE"] == 1


class TestEmployeesByDepartment:

    def test_active_by_department(self, analytics):
        by_dept = analytics.employees_by_department()
        # Active Regnskap: Ola, Kari, Anna, Sofia = 4
        # Active IT: Erik, Morten, Vidar = 3
        # Active Salg: Lars = 1
        assert by_dept["Regnskap"] == 4
        assert by_dept["IT"] == 3
        assert by_dept["Salg"] == 1


# =========================================================================
# Gender analysis
# =========================================================================

class TestGenderDistribution:

    def test_active_gender(self, analytics):
        gender = analytics.gender_distribution()
        # Active: Mann (Ola, Erik, Lars, Morten, Vidar) = 5, Kvinne (Kari, Anna, Sofia) = 3
        assert gender["Mann"] == 5
        assert gender["Kvinne"] == 3

    def test_all_gender(self, analytics):
        gender = analytics.gender_distribution(active_only=False)
        assert gender["Mann"] == 6
        assert gender["Kvinne"] == 4


class TestGenderByCountry:

    def test_norge_gender(self, analytics):
        result = analytics.gender_by_country()
        assert "Norge" in result
        # Active Norge: Mann (Ola, Erik, Morten, Vidar) = 4, Kvinne (Kari) = 1
        assert result["Norge"]["Mann"] == 4
        assert result["Norge"]["Kvinne"] == 1

    def test_no_duplicate_countries(self, analytics):
        """Regression: GROUP BY ambiguity bug."""
        result = analytics.gender_by_country()
        countries = list(result.keys())
        assert len(countries) == len(set(countries))


# =========================================================================
# Churn / turnover
# =========================================================================

class TestChurn:

    def test_churn_total(self, analytics):
        # M009 terminated 2024-12-31
        churn = analytics.calculate_churn("2024-01-01", "2024-12-31")
        assert churn["antall_sluttet"] == 1

    def test_churn_2025(self, analytics):
        # M008 terminated 2025-06-30
        churn = analytics.calculate_churn("2025-01-01", "2025-12-31")
        assert churn["antall_sluttet"] == 1

    def test_churn_no_terminations(self, analytics):
        churn = analytics.calculate_churn("2023-01-01", "2023-12-31")
        assert churn["antall_sluttet"] == 0

    def test_churn_by_country(self, analytics):
        result = analytics.churn_by_country("2024-01-01", "2024-12-31")
        # M009 was in Danmark
        assert "Danmark" in result
        assert result["Danmark"]["sluttet"] == 1

    def test_churn_by_age(self, analytics):
        result = analytics.churn_by_age("2025-01-01", "2025-12-31")
        # M008 age 48 -> category 45-54
        assert result["45-54"]["sluttet"] == 1

    def test_churn_by_gender(self, analytics):
        result = analytics.churn_by_gender("2024-01-01", "2024-12-31")
        # M009 Lise is Kvinne
        assert result["Kvinne"]["sluttet"] == 1


class TestMonthlyChurn:

    def test_returns_12_months(self, analytics):
        result = analytics.monthly_churn(2025)
        assert len(result) == 12

    def test_june_2025_termination(self, analytics):
        result = analytics.monthly_churn(2025)
        # M008 terminated 2025-06-30, month index 5 (June)
        june = result[5]
        assert june["måned"] == "2025-06"
        assert june["sluttet"] == 1

    def test_months_with_no_activity(self, analytics):
        result = analytics.monthly_churn(2023)
        for month in result:
            assert month["sluttet"] == 0
            assert month["nyansatte"] == 0


class TestTerminationReasons:

    def test_reasons(self, analytics):
        reasons = analytics.get_termination_reasons()
        assert "Frivillig" in reasons
        assert "Ufrivillig" in reasons
        assert reasons["Frivillig"] == 1
        assert reasons["Ufrivillig"] == 1


# =========================================================================
# Tenure
# =========================================================================

class TestTenure:

    def test_average_tenure_positive(self, analytics):
        tenure = analytics.average_tenure()
        assert tenure > 0

    def test_distribution_categories(self, analytics):
        dist = analytics.tenure_distribution()
        expected_keys = {"Under 1 år", "1-2 år", "2-5 år", "5-10 år", "Over 10 år"}
        assert set(dist.keys()) == expected_keys

    def test_distribution_sums_to_active(self, analytics):
        dist = analytics.tenure_distribution()
        total = sum(dist.values())
        assert total == analytics.total_employees(active_only=True)


# =========================================================================
# Employment type
# =========================================================================

class TestEmploymentType:

    def test_types(self, analytics):
        types = analytics.employment_type_distribution()
        assert "Fast" in types
        assert "Vikar" in types

    def test_fulltime_vs_parttime(self, analytics):
        result = analytics.fulltime_vs_parttime()
        # Morten has 20h/week vs 37.5 fulltime -> Deltid
        assert "Deltid" in result or "Heltid" in result


# =========================================================================
# Manager ratio
# =========================================================================

class TestManagerRatio:

    def test_manager_count(self, analytics):
        result = analytics.manager_ratio()
        # Kari (Ja) and Lars (Ja) are leaders among active
        assert result["ledere"] == 2

    def test_ratio(self, analytics):
        result = analytics.manager_ratio()
        assert result["ansatte_per_leder"] > 0
        assert result["leder_andel_pct"] > 0


# =========================================================================
# Search
# =========================================================================

class TestSearch:

    def test_search_by_name(self, analytics):
        results = analytics.search_employees(name="Ola")
        assert len(results) >= 1
        assert results[0]["fornavn"] == "Ola"

    def test_search_by_country(self, analytics):
        results = analytics.search_employees(country="Danmark")
        # Active in Danmark: Anna, Lars
        assert len(results) == 2

    def test_search_by_department(self, analytics):
        results = analytics.search_employees(department="IT")
        assert len(results) >= 1

    def test_search_no_results(self, analytics):
        results = analytics.search_employees(name="Nonexistent")
        assert len(results) == 0


# =========================================================================
# Salary analysis
# =========================================================================

class TestSalary:

    def test_summary(self, analytics):
        result = analytics.salary_summary()
        assert result["antall_med_lonn"] == 8  # active employees with salary
        assert result["gjennomsnitt"] > 0
        assert result["min"] > 0
        assert result["maks"] >= result["min"]
        assert result["total_lonnsmasse"] > 0

    def test_by_department(self, analytics):
        result = analytics.salary_by_department()
        assert "Regnskap" in result
        assert "IT" in result
        assert result["Regnskap"]["antall"] > 0

    def test_by_country(self, analytics):
        result = analytics.salary_by_country()
        assert "Norge" in result
        # No duplicate countries (regression test)
        countries = list(result.keys())
        assert len(countries) == len(set(countries))

    def test_by_gender(self, analytics):
        result = analytics.salary_by_gender()
        assert "Mann" in result
        assert "Kvinne" in result

    def test_pay_gap_calculated(self, analytics):
        result = analytics.salary_by_gender()
        assert "lønnsgap_pct" in result

    def test_by_age(self, analytics):
        result = analytics.salary_by_age()
        assert len(result) > 0

    def test_by_job_family(self, analytics):
        result = analytics.salary_by_job_family()
        assert "Finance" in result
        assert "Technology" in result


# =========================================================================
# Job family analysis
# =========================================================================

class TestJobFamily:

    def test_distribution(self, analytics):
        result = analytics.job_family_distribution()
        assert "Finance" in result
        assert "Technology" in result
        assert "Commercial" in result

    def test_by_country(self, analytics):
        result = analytics.job_family_by_country()
        assert "Norge" in result
        # No duplicate countries (regression)
        countries = list(result.keys())
        assert len(countries) == len(set(countries))

    def test_by_gender(self, analytics):
        result = analytics.job_family_by_gender()
        assert "Finance" in result
        assert "total" in result["Finance"]
        assert "kvinne_andel_pct" in result["Finance"]


# =========================================================================
# Combined analyses
# =========================================================================

class TestCombinedAnalyses:

    def test_age_and_gender_by_country(self, analytics):
        result = analytics.age_and_gender_by_country()
        assert "Norge" in result
        assert result["Norge"]["total"] == 5
        assert "kjønn" in result["Norge"]
        assert "alder" in result["Norge"]
        assert isinstance(result["Norge"]["snitt_alder"], float)

    def test_combined_summary_all(self, analytics):
        result = analytics.combined_summary()
        assert result["antall"] == 8
        assert "kjønnsfordeling" in result
        assert "aldersfordeling" in result

    def test_combined_summary_filtered(self, analytics):
        result = analytics.combined_summary(country="Norge")
        assert result["antall"] == 5
        assert "kjønnsfordeling" in result

    def test_combined_summary_nonexistent_country(self, analytics):
        result = analytics.combined_summary(country="Narnia")
        assert "feil" in result


# =========================================================================
# Planned departures
# =========================================================================

class TestPlannedDepartures:

    def test_finds_future_departures(self, analytics):
        # M010 has slutdato 2027-06-30
        result = analytics.planned_departures(months_ahead=36)
        names = [r["fornavn"] for r in result]
        assert "Vidar" in names

    def test_short_window_may_exclude(self, analytics):
        # With a very short window, M010 (2027) might not show up
        result = analytics.planned_departures(months_ahead=1)
        names = [r["fornavn"] for r in result]
        # Should not include already-terminated employees
        assert "Per" not in names
        assert "Lise" not in names
