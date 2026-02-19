"""
API-ruter for HR-analyser.

Kun endepunkter med unik logikk som den egendefinerte analyse-fanen
(custom analyzer) ikke kan gjenskape, pluss nøkkeltall/oppsummeringer.
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


@router.get("/salary/by-gender")
async def salary_by_gender(active_only: bool = Query(True)):
    """Lønn per kjønn med lønnsgap-beregning."""
    return get_analytics().salary_by_gender(active_only=active_only)
