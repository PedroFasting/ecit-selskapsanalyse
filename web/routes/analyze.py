"""
API-ruter for generisk analyse-bygger.
Lar brukeren kombinere metrikker, dimensjoner og filtre fritt.
Støtter multivalg-filtre (kommaseparerte verdier) på alle dimensjoner.
"""

from typing import Optional, Union

from fastapi import APIRouter, Query, HTTPException

from hr.analyzer import (
    run_analysis, get_filter_values,
    METRICS, DIMENSIONS, FILTERS,
)

router = APIRouter()


def _parse_filter_value(value: Optional[str]) -> Optional[Union[str, list[str]]]:
    """Parse en filterverdi — kommaseparerte verdier blir en liste."""
    if value is None:
        return None
    if "," in value:
        parts = [v.strip() for v in value.split(",") if v.strip()]
        return parts if len(parts) > 1 else (parts[0] if parts else None)
    return value


@router.get("/analyze")
async def analyze(
    metric: str = Query(..., description="Metrikk: count, avg_salary, min_salary, max_salary, sum_salary, avg_age, avg_tenure, avg_work_hours, pct_female, pct_leaders"),
    group_by: str = Query(..., description="Gruppering: alle, avdeling, juridisk_selskap, arbeidsland, kjonn, aldersgruppe, jobbfamilie, ansettelsetype, er_leder, kostsenter, tenure_gruppe, ansettelsesniva, nasjonalitet, arbeidssted"),
    split_by: Optional[str] = Query(None, description="Valgfri ekstra inndeling (samme valg som group_by)"),
    active_only: bool = Query(True, description="Bare aktive ansatte (ignoreres hvis date_as_of er satt)"),
    date_as_of: Optional[str] = Query(None, description="Snapshot-dato (YYYY-MM-DD): vis ansatte aktive per denne datoen"),
    filter_avdeling: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_arbeidsland: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_juridisk_selskap: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_kjonn: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_jobbfamilie: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_ansettelsetype: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_kostsenter: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_er_leder: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_ansettelsesniva: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_nasjonalitet: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_arbeidssted: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_divisjon: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
    filter_rolle: Optional[str] = Query(None, description="Kommaseparert for flervalg"),
):
    """
    Generisk analyse-endepunkt.
    Kombinerer en metrikk med 1-2 dimensjoner og valgfrie filtre.
    Støtter dato-snapshot via date_as_of (YYYY-MM-DD).

    Filtre støtter kommaseparerte verdier for flervalg, f.eks.:
    filter_arbeidsland=Norge,Sverige → IN ('Norge', 'Sverige')
    """
    # Bygg filter-dict fra query-params, med støtte for flervalg
    filters: dict[str, Union[str, list[str]]] = {}
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
        "divisjon": filter_divisjon,
        "rolle": filter_rolle,
    }
    for key, raw_value in filter_params.items():
        parsed = _parse_filter_value(raw_value)
        if parsed is not None:
            filters[key] = parsed

    try:
        result = run_analysis(
            metric=metric,
            group_by=group_by,
            split_by=split_by,
            filters=filters if filters else None,
            active_only=active_only,
            date_as_of=date_as_of,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analyze/options")
async def analyze_options(
    active_only: bool = Query(True),
    date_as_of: Optional[str] = Query(None, description="Snapshot-dato for filterverdier"),
):
    """
    Returnerer tilgjengelige metrikker, dimensjoner og unike filterverdier.
    Brukes til å populere dropdowns i frontend.
    """
    try:
        filter_values = get_filter_values(
            active_only=active_only,
            date_as_of=date_as_of,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
