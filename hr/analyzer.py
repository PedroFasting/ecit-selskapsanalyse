"""
Generisk analyse-motor for HR-data.
Bygger sikre SQL-spørringer fra forhåndsgodkjente metrikker, dimensjoner og filtre.
All bruker-input valideres mot whitelists — ingen rå SQL fra brukeren.
"""

from typing import Optional, Union
from pathlib import Path
from collections import defaultdict
from statistics import median as _median

from .database import get_connection, DEFAULT_DB_PATH
from .analytics import load_age_categories


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
    "divisjon":          ("divisjon", "Divisjon"),
    "juridisk_selskap":  ("juridisk_selskap", "Selskap"),
    "arbeidsland":       ("arbeidsland", "Land"),
    "kjonn":             ("kjonn", "Kjønn"),
    "aldersgruppe":      (None, "Aldersgruppe"),
    "jobbfamilie":       ("jobbfamilie", "Jobbfamilie"),
    "rolle":             ("rolle", "Rolle"),
    "ansettelsetype":    ("ansettelsetype", "Ansettelsestype"),
    "er_leder":          ("er_leder", "Leder/ikke-leder"),
    "kostsenter":        ("kostsenter", "Kostsenter"),
    "tenure_gruppe":     (None, "Ansiennitetsgruppe"),
    "ansettelsesniva":   ("ansettelsesniva", "Ansettelsesnivå"),
    "nasjonalitet":      ("nasjonalitet", "Nasjonalitet"),
    "arbeidssted":       ("arbeidssted", "Arbeidssted"),
}

# SQL CASE-uttrykk for aldersgrupper (bygges dynamisk fra DB)
def _build_age_case_expr(db_path: Optional[Path] = None) -> str:
    """Bygg SQL CASE-uttrykk for aldersgrupper fra DB-kategorier."""
    cats = load_age_categories(db_path)
    parts = []
    for min_a, max_a, label in cats:
        if min_a == 0:
            parts.append(f"WHEN alder < {max_a + 1} THEN '{label}'")
        elif max_a >= 150:
            parts.append(f"WHEN alder >= {min_a} THEN '{label}'")
        else:
            parts.append(f"WHEN alder BETWEEN {min_a} AND {max_a} THEN '{label}'")
    lines = "\n    ".join(parts)
    return f"CASE\n    {lines}\n    ELSE 'Ukjent'\nEND"

# Bakoverkompatibilitet: statisk fallback for import
AGE_CASE_EXPR = _build_age_case_expr()

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


def _resolve_dimension(dim_key: str, db_path: Optional[Path] = None) -> str:
    """
    Returner SQL-uttrykk for en dimensjon.
    Vanlige kolonner returneres med COALESCE, beregnede dimensjoner med CASE.
    """
    if dim_key == "aldersgruppe":
        return _build_age_case_expr(db_path)
    if dim_key == "tenure_gruppe":
        return TENURE_CASE_EXPR
    col = DIMENSIONS[dim_key][0]
    return f"COALESCE({col}, 'Ukjent')"


def _validate_date_as_of(date_as_of: Optional[str]) -> Optional[str]:
    """Valider og normaliser date_as_of parameter (YYYY-MM-DD format)."""
    if date_as_of is None:
        return None
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_as_of):
        raise ValueError(
            f"Ugyldig datoformat: '{date_as_of}'. Bruk YYYY-MM-DD (f.eks. 2025-06-01)."
        )
    return date_as_of


def build_analysis_query(
    metric: str,
    group_by: str,
    split_by: Optional[str] = None,
    filters: Optional[dict[str, Union[str, list[str]]]] = None,
    active_only: bool = True,
    date_as_of: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> tuple[str, tuple]:
    """
    Bygg sikker SQL-spørring fra validerte parametere.

    Args:
        metric: Nøkkel fra METRICS (f.eks. 'count', 'avg_salary')
        group_by: Nøkkel fra DIMENSIONS (f.eks. 'avdeling', 'kjonn')
        split_by: Valgfri ekstra dimensjon fra DIMENSIONS
        filters: Dict med {dimensjon_nøkkel: verdi_eller_liste} for WHERE-filtre.
                 Enkeltverdi: "Norge" → col = ?
                 Liste: ["Norge", "Sverige"] → col IN (?, ?)
        active_only: Bare aktive ansatte (ignoreres hvis date_as_of er satt)
        date_as_of: Snapshot-dato (YYYY-MM-DD) — vis ansatte som var aktive per denne datoen

    Returns:
        (sql_string, params_tuple)

    Raises:
        ValueError: Hvis metric, group_by, split_by eller filter-nøkkel er ugyldig
    """
    # Valider date_as_of
    date_as_of = _validate_date_as_of(date_as_of)

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

    # Dato-snapshot: vis ansatte som var aktive per angitt dato
    # Overstyrer active_only når satt
    if date_as_of:
        where_parts.append("ansettelsens_startdato IS NOT NULL")
        where_parts.append("ansettelsens_startdato <= ?")
        params.append(date_as_of)
        where_parts.append(
            "(slutdato_ansettelse IS NULL OR slutdato_ansettelse > ?)"
        )
        params.append(date_as_of)
    elif active_only:
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
            # Støtt både enkeltverdi (str) og flerverdier (list)
            if isinstance(value, list):
                if len(value) == 0:
                    continue  # Tom liste = ingen filtrering
                if len(value) == 1:
                    where_parts.append(f"{col} = ?")
                    params.append(value[0])
                else:
                    placeholders = ", ".join(["?"] * len(value))
                    where_parts.append(f"{col} IN ({placeholders})")
                    params.extend(value)
            else:
                where_parts.append(f"{col} = ?")
                params.append(value)

    # Bygg SQL
    agg_func = METRICS[metric][0]

    # Når date_as_of er satt, bruk snapshot-datoen i stedet for date('now')
    # for ansiennitetsberegninger
    if date_as_of and metric == "avg_tenure":
        agg_func = (
            f"AVG(JULIANDAY(COALESCE(slutdato_ansettelse, '{date_as_of}')) "
            f"- JULIANDAY(ansettelsens_startdato)) / 365.25"
        )

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    # Spesialhåndtering: metrikker med None som SQL (f.eks. median)
    # Henter rådata per gruppe i stedet for aggregat — beregnes i run_analysis()
    if agg_func is None:
        if group_by == "alle":
            sql = f"SELECT lonn AS verdi FROM ansatte {where_clause}"
            return sql, tuple(params)

        group_expr = _resolve_dimension(group_by, db_path)
        select_parts = [f"{group_expr} AS gruppe"]

        if split_by:
            split_expr = _resolve_dimension(split_by, db_path)
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

    group_expr = _resolve_dimension(group_by, db_path)
    group_alias = "gruppe"

    select_parts = [f"{group_expr} AS {group_alias}"]
    group_by_parts = [group_alias]

    if split_by:
        split_expr = _resolve_dimension(split_by, db_path)
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
    filters: Optional[dict[str, Union[str, list[str]]]],
    rows: list,
    date_as_of: Optional[str] = None,
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
        "date_as_of": date_as_of,
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
    filters: Optional[dict[str, Union[str, list[str]]]] = None,
    active_only: bool = True,
    db_path: Optional[Path] = None,
    date_as_of: Optional[str] = None,
) -> dict:
    """
    Kjør en analyse og returner strukturert resultat.

    Args:
        date_as_of: Snapshot-dato (YYYY-MM-DD) — vis ansatte som var aktive per denne datoen.
                    Overstyrer active_only.

    Returns:
        {
            "meta": { metric, metric_label, group_by, group_by_label, ..., date_as_of },
            "data": { "Gruppe1": verdi, ... } eller { "Gruppe1": {"Split1": v, ...}, ... }
        }
    """
    sql, params = build_analysis_query(
        metric=metric,
        group_by=group_by,
        split_by=split_by,
        filters=filters,
        active_only=active_only,
        date_as_of=date_as_of,
        db_path=db_path,
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
        return _compute_special_metric(metric, group_by, split_by, filters, rows, date_as_of)

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
            "date_as_of": date_as_of,
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
        "date_as_of": date_as_of,
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
    date_as_of: Optional[str] = None,
) -> dict[str, list[str]]:
    """
    Hent unike verdier for alle filtrerbare dimensjoner.
    Brukes til å populere filter-dropdowns i frontend.

    Args:
        date_as_of: Snapshot-dato — vis verdier for ansatte aktive per denne datoen.
    """
    date_as_of = _validate_date_as_of(date_as_of)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Bygg WHERE-betingelse
    if date_as_of:
        where = (
            "WHERE ansettelsens_startdato IS NOT NULL "
            "AND ansettelsens_startdato <= ? "
            "AND (slutdato_ansettelse IS NULL OR slutdato_ansettelse > ?)"
        )
        base_params = [date_as_of, date_as_of]
    elif active_only:
        where = "WHERE er_aktiv = 1"
        base_params = []
    else:
        where = ""
        base_params = []

    result: dict[str, list[str]] = {}

    for key, col in FILTERS.items():
        if where:
            sql = (
                f"SELECT DISTINCT {col} FROM ansatte {where} "
                f"AND {col} IS NOT NULL ORDER BY {col}"
            )
        else:
            sql = (
                f"SELECT DISTINCT {col} FROM ansatte "
                f"WHERE {col} IS NOT NULL ORDER BY {col}"
            )
        cursor.execute(sql, base_params)
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
