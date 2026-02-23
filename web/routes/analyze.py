"""
API-ruter for generisk analyse-bygger.
Lar brukeren kombinere metrikker, dimensjoner og filtre fritt.
"""

from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from hr.analyzer import (
    run_analysis, get_filter_values,
    METRICS, DIMENSIONS, FILTERS,
)

router = APIRouter()


@router.get("/analyze")
async def analyze(
    metric: str = Query(..., description="Metrikk: count, avg_salary, min_salary, max_salary, sum_salary, avg_age, avg_tenure, avg_work_hours, pct_female, pct_leaders"),
    group_by: str = Query(..., description="Gruppering: alle, avdeling, juridisk_selskap, arbeidsland, kjonn, aldersgruppe, jobbfamilie, ansettelsetype, er_leder, kostsenter, tenure_gruppe, ansettelsesniva, nasjonalitet, arbeidssted"),
    split_by: Optional[str] = Query(None, description="Valgfri ekstra inndeling (samme valg som group_by)"),
    active_only: bool = Query(True, description="Bare aktive ansatte"),
    filter_avdeling: Optional[str] = Query(None),
    filter_arbeidsland: Optional[str] = Query(None),
    filter_juridisk_selskap: Optional[str] = Query(None),
    filter_kjonn: Optional[str] = Query(None),
    filter_jobbfamilie: Optional[str] = Query(None),
    filter_ansettelsetype: Optional[str] = Query(None),
    filter_kostsenter: Optional[str] = Query(None),
    filter_er_leder: Optional[str] = Query(None),
    filter_ansettelsesniva: Optional[str] = Query(None),
    filter_nasjonalitet: Optional[str] = Query(None),
    filter_arbeidssted: Optional[str] = Query(None),
):
    """
    Generisk analyse-endepunkt.
    Kombinerer en metrikk med 1-2 dimensjoner og valgfrie filtre.
    """
    # Bygg filter-dict fra query-params
    filters: dict[str, str] = {}
    filter_params = {
        "avdeling": filter_avdeling,
        "arbeidsland": filter_arbeidsland,
        "juridisk_selskap": filter_juridisk_selskap,
        "kjonn": filter_kjonn,
        "jobbfamilie": filter_jobbfamilie,
        "ansettelsetype": filter_ansettelsetype,
        "kostsenter": filter_kostsenter,
        "er_leder": filter_er_leder,
        "ansettelsesniva": filter_ansettelsesniva,
        "nasjonalitet": filter_nasjonalitet,
        "arbeidssted": filter_arbeidssted,
    }
    for key, value in filter_params.items():
        if value is not None:
            filters[key] = value

    try:
        result = run_analysis(
            metric=metric,
            group_by=group_by,
            split_by=split_by,
            filters=filters if filters else None,
            active_only=active_only,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analyze/options")
async def analyze_options(active_only: bool = Query(True)):
    """
    Returnerer tilgjengelige metrikker, dimensjoner og unike filterverdier.
    Brukes til å populere dropdowns i frontend.
    """
    filter_values = get_filter_values(active_only=active_only)

    return {
        "metrics": [
            {"id": k, "label": v[1]} for k, v in METRICS.items()
        ],
        "dimensions": [
            {"id": k, "label": v[1]} for k, v in DIMENSIONS.items()
        ] + [
            {"id": "alle", "label": "Alle (total)"},
        ],
        "filter_dimensions": [
            {"id": k, "label": DIMENSIONS[k][1]}
            for k in FILTERS.keys()
        ],
        "filter_values": filter_values,
    }
