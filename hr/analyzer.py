"""
Generisk analyse-motor for HR-data.
Bygger sikre SQL-spørringer fra forhåndsgodkjente metrikker, dimensjoner og filtre.
All bruker-input valideres mot whitelists — ingen rå SQL fra brukeren.
"""

from typing import Optional
from pathlib import Path
from collections import defaultdict
from statistics import median as _median

from .database import get_connection, DEFAULT_DB_PATH


# === WHITELISTS ===

# Tillatte metrikker → (SQL-aggregering | None, visningsnavn)
# Metrikker merket med None som SQL har spesialhåndtering i run_analysis()
METRICS: dict[str, tuple[Optional[str], str]] = {
    "count":           ("COUNT(*)",  "Antall ansatte"),
    "avg_salary":      ("AVG(lonn)", "Gjennomsnittslønn"),
    "min_salary":      ("MIN(lonn)", "Laveste lønn"),
    "max_salary":      ("MAX(lonn)", "Høyeste lønn"),
    "median_salary":   (None, "Median lønn"),
    "sum_salary":      ("SUM(lonn)", "Total lønnsmasse"),
    "avg_age":         ("AVG(alder)", "Gjennomsnittsalder"),
    "avg_tenure":      (
        "AVG(JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) "
        "- JULIANDAY(ansettelsens_startdato)) / 365.25",
        "Snitt ansiennitet (år)",
    ),
    "avg_work_hours":  ("AVG(arbeidstid_per_uke)", "Snitt arbeidstid (t/uke)"),
    "pct_female":      (
        "AVG(CASE WHEN kjonn = 'Kvinne' THEN 100.0 ELSE 0.0 END)",
        "Andel kvinner (%)",
    ),
    "pct_leaders":     (
        "AVG(CASE WHEN er_leder IN ('Ja', 'ja', 'yes', 'Yes', '1', 'true') "
        "THEN 100.0 ELSE 0.0 END)",
        "Andel ledere (%)",
    ),
}

# Tillatte grupperingsdimensjoner → (kolonnenavn | None, visningsnavn)
# None betyr beregnet felt (spesialhåndtering i _resolve_dimension)
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
    "tenure_gruppe":     (None, "Ansiennitetsgruppe"),
    "ansettelsesniva":   ("ansettelsesniva", "Ansettelsesnivå"),
    "nasjonalitet":      ("nasjonalitet", "Nasjonalitet"),
    "arbeidssted":       ("arbeidssted", "Arbeidssted"),
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

# SQL CASE-uttrykk for ansiennitetsgrupper (beregnet dimensjon)
TENURE_CASE_EXPR = """CASE
    WHEN (JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - JULIANDAY(ansettelsens_startdato)) / 365.25 < 1 THEN 'Under 1 år'
    WHEN (JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - JULIANDAY(ansettelsens_startdato)) / 365.25 < 2 THEN '1-2 år'
    WHEN (JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - JULIANDAY(ansettelsens_startdato)) / 365.25 < 5 THEN '2-5 år'
    WHEN (JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - JULIANDAY(ansettelsens_startdato)) / 365.25 < 10 THEN '5-10 år'
    WHEN (JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - JULIANDAY(ansettelsens_startdato)) / 365.25 >= 10 THEN 'Over 10 år'
    ELSE 'Ukjent'
END"""

# Tillatte filterdimensjoner → kolonnenavn (bare de med faktisk kolonne)
FILTERS: dict[str, str] = {
    k: v[0] for k, v in DIMENSIONS.items() if v[0] is not None
}


def _resolve_dimension(dim_key: str) -> str:
    """
    Returner SQL-uttrykk for en dimensjon.
    Vanlige kolonner returneres med COALESCE, beregnede dimensjoner med CASE.
    """
    if dim_key == "aldersgruppe":
        return AGE_CASE_EXPR
    if dim_key == "tenure_gruppe":
        return TENURE_CASE_EXPR
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
    if group_by != "alle" and group_by not in DIMENSIONS:
        raise ValueError(
            f"Ugyldig gruppering: '{group_by}'. Tillatte: alle, {', '.join(DIMENSIONS.keys())}"
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
    salary_metrics = {"avg_salary", "min_salary", "max_salary", "median_salary", "sum_salary"}
    if metric in salary_metrics:
        where_parts.append("lonn IS NOT NULL")

    # Metrikker som krever alder trenger alder IS NOT NULL
    if metric == "avg_age":
        where_parts.append("alder IS NOT NULL")

    # Ansiennitet krever ansettelsesdato
    if metric == "avg_tenure":
        where_parts.append("ansettelsens_startdato IS NOT NULL")

    # Arbeidstid krever arbeidstid_per_uke
    if metric == "avg_work_hours":
        where_parts.append("arbeidstid_per_uke IS NOT NULL")

    # Aldersgruppe-dimensjon krever alder IS NOT NULL
    if group_by == "aldersgruppe" or split_by == "aldersgruppe":
        where_parts.append("alder IS NOT NULL")

    # Ansiennitetsgruppe-dimensjon krever ansettelsesdato
    if group_by == "tenure_gruppe" or split_by == "tenure_gruppe":
        where_parts.append("ansettelsens_startdato IS NOT NULL")

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

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    # Spesialhåndtering: metrikker med None som SQL (f.eks. median)
    # Henter rådata per gruppe i stedet for aggregat — beregnes i run_analysis()
    if agg_func is None:
        if group_by == "alle":
            sql = f"SELECT lonn AS verdi FROM ansatte {where_clause}"
            return sql, tuple(params)

        group_expr = _resolve_dimension(group_by)
        select_parts = [f"{group_expr} AS gruppe"]

        if split_by:
            split_expr = _resolve_dimension(split_by)
            select_parts.append(f"{split_expr} AS inndeling")

        select_parts.append("lonn AS verdi")
        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM ansatte "
            f"{where_clause} "
            f"ORDER BY gruppe"
        )
        return sql, tuple(params)

    # Spesialhåndtering: "alle" = ingen GROUP BY, bare aggregering
    if group_by == "alle":
        sql = f"SELECT {agg_func} AS verdi FROM ansatte {where_clause}"
        return sql, tuple(params)

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

    sql = (
        f"SELECT {', '.join(select_parts)} "
        f"FROM ansatte "
        f"{where_clause} "
        f"GROUP BY {', '.join(group_by_parts)} "
        f"ORDER BY {group_alias}"
    )

    return sql, tuple(params)


def _compute_special_metric(
    metric: str,
    group_by: str,
    split_by: Optional[str],
    filters: Optional[dict[str, str]],
    rows: list,
) -> dict:
    """
    Beregn metrikker som ikke kan uttrykkes som SQL-aggregat (f.eks. median).
    Rådataene (gruppe [, inndeling], verdi) grupperes og beregnes i Python.
    """
    meta = {
        "metric": metric,
        "metric_label": METRICS[metric][1],
        "group_by": group_by,
        "group_by_label": (
            "Alle (total)" if group_by == "alle"
            else DIMENSIONS[group_by][1]
        ),
        "split_by": split_by,
        "split_by_label": DIMENSIONS[split_by][1] if split_by else None,
        "filters": filters or {},
    }

    if group_by == "alle":
        values = [row[0] for row in rows if row[0] is not None]
        result = _median(values) if values else 0
        meta["total_groups"] = 1
        return {"meta": meta, "data": {"Alle": _round_value(result, metric)}}

    if split_by:
        grouped: dict[str, dict[str, list[float]]] = {}
        for row in rows:
            gruppe, inndeling, verdi = row[0], row[1], row[2]
            if verdi is None:
                continue
            if gruppe not in grouped:
                grouped[gruppe] = {}
            if inndeling not in grouped[gruppe]:
                grouped[gruppe][inndeling] = []
            grouped[gruppe][inndeling].append(verdi)

        data: dict = {}
        for gruppe, splits in grouped.items():
            data[gruppe] = {
                k: _round_value(_median(v), metric)
                for k, v in splits.items() if v
            }
        meta["total_groups"] = len(data)
    else:
        grouped_flat: dict[str, list[float]] = {}
        for row in rows:
            gruppe, verdi = row[0], row[1]
            if verdi is None:
                continue
            if gruppe not in grouped_flat:
                grouped_flat[gruppe] = []
            grouped_flat[gruppe].append(verdi)

        data = {
            k: _round_value(_median(v), metric)
            for k, v in grouped_flat.items() if v
        }
        meta["total_groups"] = len(data)

    return {"meta": meta, "data": data}


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

    agg_func = METRICS[metric][0]

    # Spesialhåndtering: metrikker med None som SQL (f.eks. median)
    # Rådataene er hentet per rad — vi grupperer og beregner i Python.
    if agg_func is None:
        return _compute_special_metric(metric, group_by, split_by, filters, rows)

    # Spesialhåndtering: "alle" returnerer én enkelt verdi
    if group_by == "alle":
        value = rows[0][0] if rows else 0
        meta = {
            "metric": metric,
            "metric_label": METRICS[metric][1],
            "group_by": "alle",
            "group_by_label": "Alle (total)",
            "split_by": None,
            "split_by_label": None,
            "filters": filters or {},
            "total_groups": 1,
        }
        return {"meta": meta, "data": {"Alle": _round_value(value, metric)}}

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
    # Prosent- og ansiennitetsmetrikker: 1 desimal
    if metric in {"pct_female", "pct_leaders", "avg_tenure"}:
        return round(float(value), 1)
    return round(float(value), 0)
