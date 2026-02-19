"""
Generisk analyse-motor for HR-data.
Bygger sikre SQL-spørringer fra forhåndsgodkjente metrikker, dimensjoner og filtre.
All bruker-input valideres mot whitelists — ingen rå SQL fra brukeren.
"""

from typing import Optional
from pathlib import Path
from collections import defaultdict

from .database import get_connection, DEFAULT_DB_PATH


# === WHITELISTS ===

# Tillatte metrikker → (SQL-aggregering, visningsnavn)
METRICS: dict[str, tuple[str, str]] = {
    "count":       ("COUNT(*)",  "Antall ansatte"),
    "avg_salary":  ("AVG(lonn)", "Gjennomsnittslønn"),
    "min_salary":  ("MIN(lonn)", "Laveste lønn"),
    "max_salary":  ("MAX(lonn)", "Høyeste lønn"),
    "sum_salary":  ("SUM(lonn)", "Total lønnsmasse"),
    "avg_age":     ("AVG(alder)", "Gjennomsnittsalder"),
}

# Tillatte grupperingsdimensjoner → (kolonnenavn | None, visningsnavn)
# None betyr beregnet felt (spesialhåndtering)
DIMENSIONS: dict[str, tuple[Optional[str], str]] = {
    "avdeling":          ("avdeling", "Avdeling"),
    "juridisk_selskap":  ("juridisk_selskap", "Selskap"),
    "arbeidsland":       ("arbeidsland", "Land"),
    "kjonn":             ("kjonn", "Kjønn"),
    "aldersgruppe":      (None, "Aldersgruppe"),
    "jobbfamilie":       ("jobbfamilie", "Jobbfamilie"),
    "ansettelsetype":    ("ansettelsetype", "Ansettelsestype"),
    "er_leder":          ("er_leder", "Leder/ikke-leder"),
    "kostsenter":        ("kostsenter", "Kostsenter"),
}

# SQL CASE-uttrykk for aldersgrupper (beregnet dimensjon)
AGE_CASE_EXPR = """CASE
    WHEN alder < 25 THEN 'Under 25'
    WHEN alder BETWEEN 25 AND 34 THEN '25-34'
    WHEN alder BETWEEN 35 AND 44 THEN '35-44'
    WHEN alder BETWEEN 45 AND 54 THEN '45-54'
    WHEN alder BETWEEN 55 AND 64 THEN '55-64'
    WHEN alder >= 65 THEN '65+'
    ELSE 'Ukjent'
END"""

# Tillatte filterdimensjoner → kolonnenavn (bare de med faktisk kolonne)
FILTERS: dict[str, str] = {
    k: v[0] for k, v in DIMENSIONS.items() if v[0] is not None
}


def _resolve_dimension(dim_key: str) -> str:
    """
    Returner SQL-uttrykk for en dimensjon.
    Vanlige kolonner returneres med COALESCE, aldersgruppe med CASE.
    """
    if dim_key == "aldersgruppe":
        return AGE_CASE_EXPR
    col = DIMENSIONS[dim_key][0]
    return f"COALESCE({col}, 'Ukjent')"


def build_analysis_query(
    metric: str,
    group_by: str,
    split_by: Optional[str] = None,
    filters: Optional[dict[str, str]] = None,
    active_only: bool = True,
) -> tuple[str, tuple]:
    """
    Bygg sikker SQL-spørring fra validerte parametere.

    Args:
        metric: Nøkkel fra METRICS (f.eks. 'count', 'avg_salary')
        group_by: Nøkkel fra DIMENSIONS (f.eks. 'avdeling', 'kjonn')
        split_by: Valgfri ekstra dimensjon fra DIMENSIONS
        filters: Dict med {dimensjon_nøkkel: verdi} for WHERE-filtre
        active_only: Bare aktive ansatte

    Returns:
        (sql_string, params_tuple)

    Raises:
        ValueError: Hvis metric, group_by, split_by eller filter-nøkkel er ugyldig
    """
    # Valider metrikk
    if metric not in METRICS:
        raise ValueError(
            f"Ugyldig metrikk: '{metric}'. Tillatte: {', '.join(METRICS.keys())}"
        )

    # Valider group_by
    if group_by not in DIMENSIONS:
        raise ValueError(
            f"Ugyldig gruppering: '{group_by}'. Tillatte: {', '.join(DIMENSIONS.keys())}"
        )

    # Valider split_by
    if split_by is not None and split_by not in DIMENSIONS:
        raise ValueError(
            f"Ugyldig inndeling: '{split_by}'. Tillatte: {', '.join(DIMENSIONS.keys())}"
        )

    # Valider filtre
    params: list = []
    where_parts: list[str] = []

    if active_only:
        where_parts.append("er_aktiv = 1")

    # Metrikker som krever lønn trenger lonn IS NOT NULL
    salary_metrics = {"avg_salary", "min_salary", "max_salary", "sum_salary"}
    if metric in salary_metrics:
        where_parts.append("lonn IS NOT NULL")

    # Metrikker som krever alder trenger alder IS NOT NULL
    if metric == "avg_age":
        where_parts.append("alder IS NOT NULL")

    # Aldersgruppe-dimensjon krever alder IS NOT NULL
    if group_by == "aldersgruppe" or split_by == "aldersgruppe":
        where_parts.append("alder IS NOT NULL")

    if filters:
        for key, value in filters.items():
            if key not in FILTERS:
                raise ValueError(
                    f"Ugyldig filter: '{key}'. Tillatte: {', '.join(FILTERS.keys())}"
                )
            col = FILTERS[key]
            where_parts.append(f"{col} = ?")
            params.append(value)

    # Bygg SQL
    agg_func = METRICS[metric][0]
    group_expr = _resolve_dimension(group_by)
    group_alias = "gruppe"

    select_parts = [f"{group_expr} AS {group_alias}"]
    group_by_parts = [group_alias]

    if split_by:
        split_expr = _resolve_dimension(split_by)
        split_alias = "inndeling"
        select_parts.append(f"{split_expr} AS {split_alias}")
        group_by_parts.append(split_alias)

    select_parts.append(f"{agg_func} AS verdi")

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    sql = (
        f"SELECT {', '.join(select_parts)} "
        f"FROM ansatte "
        f"{where_clause} "
        f"GROUP BY {', '.join(group_by_parts)} "
        f"ORDER BY {group_alias}"
    )

    return sql, tuple(params)


def run_analysis(
    metric: str,
    group_by: str,
    split_by: Optional[str] = None,
    filters: Optional[dict[str, str]] = None,
    active_only: bool = True,
    db_path: Optional[Path] = None,
) -> dict:
    """
    Kjør en analyse og returner strukturert resultat.

    Returns:
        {
            "meta": { metric, metric_label, group_by, group_by_label, ... },
            "data": { "Gruppe1": verdi, ... } eller { "Gruppe1": {"Split1": v, ...}, ... }
        }
    """
    sql, params = build_analysis_query(
        metric=metric,
        group_by=group_by,
        split_by=split_by,
        filters=filters,
        active_only=active_only,
    )

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    # Bygg meta
    meta = {
        "metric": metric,
        "metric_label": METRICS[metric][1],
        "group_by": group_by,
        "group_by_label": DIMENSIONS[group_by][1],
        "split_by": split_by,
        "split_by_label": DIMENSIONS[split_by][1] if split_by else None,
        "filters": filters or {},
    }

    # Bygg data
    if split_by:
        data: dict = {}
        for row in rows:
            gruppe = row[0]
            inndeling = row[1]
            verdi = row[2]
            if gruppe not in data:
                data[gruppe] = {}
            data[gruppe][inndeling] = _round_value(verdi, metric)
        meta["total_groups"] = len(data)
    else:
        data = {}
        for row in rows:
            data[row[0]] = _round_value(row[1], metric)
        meta["total_groups"] = len(data)

    return {"meta": meta, "data": data}


def get_filter_values(
    db_path: Optional[Path] = None,
    active_only: bool = True,
) -> dict[str, list[str]]:
    """
    Hent unike verdier for alle filtrerbare dimensjoner.
    Brukes til å populere filter-dropdowns i frontend.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    where = "WHERE er_aktiv = 1" if active_only else ""
    result: dict[str, list[str]] = {}

    for key, col in FILTERS.items():
        cursor.execute(
            f"SELECT DISTINCT {col} FROM ansatte {where} "
            f"AND {col} IS NOT NULL ORDER BY {col}"
            if where else
            f"SELECT DISTINCT {col} FROM ansatte "
            f"WHERE {col} IS NOT NULL ORDER BY {col}"
        )
        result[key] = [row[0] for row in cursor.fetchall()]

    conn.close()
    return result


def _round_value(value, metric: str):
    """Rund av verdier basert på metrikk-type."""
    if value is None:
        return 0
    if metric == "count":
        return int(value)
    return round(float(value), 0)
