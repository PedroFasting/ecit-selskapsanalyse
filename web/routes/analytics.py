"""
API-ruter for alle HR-analyser.
Direkte 1:1-mapping mellom HRAnalytics-metoder og GET-endepunkter.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from web.app import get_analytics

router = APIRouter()


# === OVERSIKT ===

@router.get("/overview/summary")
async def overview_summary():
    """Generell oversikt over ansatte."""
    return get_analytics().employees_summary()


@router.get("/overview/by-country")
async def overview_by_country(active_only: bool = Query(True)):
    """Antall ansatte per land."""
    return get_analytics().employees_by_country(active_only=active_only)


@router.get("/overview/by-company")
async def overview_by_company(active_only: bool = Query(True)):
    """Antall ansatte per juridisk selskap."""
    return get_analytics().employees_by_company(active_only=active_only)


@router.get("/overview/by-department")
async def overview_by_department(active_only: bool = Query(True)):
    """Antall ansatte per avdeling."""
    return get_analytics().employees_by_department(active_only=active_only)


# === ALDER ===

@router.get("/age/distribution")
async def age_distribution(active_only: bool = Query(True)):
    """Aldersfordeling i kategorier."""
    return get_analytics().age_distribution(active_only=active_only)


@router.get("/age/distribution-pct")
async def age_distribution_pct(active_only: bool = Query(True)):
    """Aldersfordeling i prosent."""
    return get_analytics().age_distribution_pct(active_only=active_only)


@router.get("/age/by-country")
async def age_by_country(active_only: bool = Query(True)):
    """Aldersfordeling per land."""
    return get_analytics().age_distribution_by_country(active_only=active_only)


# === KJØNN ===

@router.get("/gender/distribution")
async def gender_distribution(active_only: bool = Query(True)):
    """Kjønnsfordeling."""
    return get_analytics().gender_distribution(active_only=active_only)


@router.get("/gender/by-country")
async def gender_by_country(active_only: bool = Query(True)):
    """Kjønnsfordeling per land."""
    return get_analytics().gender_by_country(active_only=active_only)


# === CHURN ===

@router.get("/churn/calculate")
async def churn_calculate(
    start_date: str = Query(..., description="Startdato (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Sluttdato (YYYY-MM-DD)"),
    by: str = Query("total", description="Gruppering: total, country, company, department"),
):
    """Beregn churn/turnover for en periode."""
    return get_analytics().calculate_churn(start_date=start_date, end_date=end_date, by=by)


@router.get("/churn/monthly")
async def churn_monthly(year: Optional[int] = Query(None)):
    """Månedlig churn for et gitt år."""
    yr = year or date.today().year
    return get_analytics().monthly_churn(year=yr)


@router.get("/churn/by-age")
async def churn_by_age(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Churn fordelt på alderskategorier."""
    return get_analytics().churn_by_age(start_date=start_date, end_date=end_date)


@router.get("/churn/by-country")
async def churn_by_country(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Churn fordelt på land."""
    return get_analytics().churn_by_country(start_date=start_date, end_date=end_date)


@router.get("/churn/by-gender")
async def churn_by_gender(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Churn fordelt på kjønn."""
    return get_analytics().churn_by_gender(start_date=start_date, end_date=end_date)


@router.get("/churn/reasons")
async def churn_reasons(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Oppsigelsesårsaker."""
    return get_analytics().get_termination_reasons(start_date=start_date, end_date=end_date)


# === TENURE ===

@router.get("/tenure/average")
async def tenure_average(active_only: bool = Query(True)):
    """Gjennomsnittlig ansettelsestid i år."""
    return {"gjennomsnitt_ar": get_analytics().average_tenure(active_only=active_only)}


@router.get("/tenure/distribution")
async def tenure_distribution(active_only: bool = Query(True)):
    """Fordeling av ansettelsestid."""
    return get_analytics().tenure_distribution(active_only=active_only)


# === ANSETTELSESTYPE ===

@router.get("/employment/types")
async def employment_types(active_only: bool = Query(True)):
    """Fordeling av ansettelsestyper."""
    return get_analytics().employment_type_distribution(active_only=active_only)


@router.get("/employment/fulltime-parttime")
async def fulltime_parttime(active_only: bool = Query(True)):
    """Heltid vs deltid."""
    return get_analytics().fulltime_vs_parttime(active_only=active_only)


# === LEDELSE ===

@router.get("/management/ratio")
async def management_ratio(active_only: bool = Query(True)):
    """Lederandel."""
    return get_analytics().manager_ratio(active_only=active_only)


# === SØK ===

@router.get("/search")
async def search_employees(
    name: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=500),
):
    """Søk etter ansatte."""
    return get_analytics().search_employees(
        name=name, department=department, country=country,
        company=company, active_only=active_only, limit=limit,
    )


# === KOMBINERT ===

@router.get("/combined/summary")
async def combined_summary(
    country: Optional[str] = Query(None),
    active_only: bool = Query(True),
):
    """Kombinert sammendrag med alle nøkkeltall."""
    return get_analytics().combined_summary(country=country, active_only=active_only)


@router.get("/combined/age-gender-country")
async def age_gender_country(active_only: bool = Query(True)):
    """Kombinert oversikt: alder og kjønn per land."""
    return get_analytics().age_and_gender_by_country(active_only=active_only)


# === PLANLAGTE AVGANGER ===

@router.get("/departures/planned")
async def planned_departures(months_ahead: int = Query(12, ge=1, le=60)):
    """Ansatte med planlagt slutdato."""
    return get_analytics().planned_departures(months_ahead=months_ahead)


# === LØNN ===

@router.get("/salary/summary")
async def salary_summary(active_only: bool = Query(True)):
    """Oppsummering av lønnsdata."""
    return get_analytics().salary_summary(active_only=active_only)


@router.get("/salary/by-department")
async def salary_by_department(active_only: bool = Query(True)):
    """Gjennomsnittlig lønn per avdeling."""
    return get_analytics().salary_by_department(active_only=active_only)


@router.get("/salary/by-country")
async def salary_by_country(active_only: bool = Query(True)):
    """Gjennomsnittlig lønn per land."""
    return get_analytics().salary_by_country(active_only=active_only)


@router.get("/salary/by-gender")
async def salary_by_gender(active_only: bool = Query(True)):
    """Lønn per kjønn med lønnsgap-beregning."""
    return get_analytics().salary_by_gender(active_only=active_only)


@router.get("/salary/by-age")
async def salary_by_age(active_only: bool = Query(True)):
    """Gjennomsnittlig lønn per alderskategori."""
    return get_analytics().salary_by_age(active_only=active_only)


@router.get("/salary/by-job-family")
async def salary_by_job_family(active_only: bool = Query(True)):
    """Gjennomsnittlig lønn per jobbfamilie."""
    return get_analytics().salary_by_job_family(active_only=active_only)


# === JOBBFAMILIER ===

@router.get("/job-family/distribution")
async def job_family_distribution(active_only: bool = Query(True)):
    """Fordeling av ansatte per jobbfamilie."""
    return get_analytics().job_family_distribution(active_only=active_only)


@router.get("/job-family/by-country")
async def job_family_by_country(active_only: bool = Query(True)):
    """Jobbfamilier per land."""
    return get_analytics().job_family_by_country(active_only=active_only)


@router.get("/job-family/by-gender")
async def job_family_by_gender(active_only: bool = Query(True)):
    """Kjønnsfordeling per jobbfamilie."""
    return get_analytics().job_family_by_gender(active_only=active_only)
