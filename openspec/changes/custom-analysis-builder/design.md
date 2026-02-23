# Design: Custom Analysis Builder

## Arkitektur-oversikt

```
[Bruker: velger metrikk/dimensjoner/filter/graftype]
        ↓
[Frontend: bygger query-params, sender request]
        ↓
[API: GET /api/analyze?metric=...&group_by=...&split_by=...&filter_*=...]
        ↓
[Backend: validerer mot whitelist → bygger SQL → kjører query]
        ↓
[API: returnerer strukturert JSON]
        ↓
[Frontend: velger graftype (auto/manuell) → rendrer med Chart.js]
```

## 1. Backend — Generisk analyse-endepunkt

### 1.1 Whitelists (sikkerhet)

Alle tillatte verdier defineres som konstanter i en ny fil `hr_database/analyzer.py`:

```python
# Tillatte metrikker → SQL-aggregeringsfunksjon
METRICS = {
    "count":       ("COUNT(*)", "Antall ansatte"),
    "avg_salary":  ("AVG(lonn)", "Gjennomsnittslønn"),
    "min_salary":  ("MIN(lonn)", "Laveste lønn"),
    "max_salary":  ("MAX(lonn)", "Høyeste lønn"),
    "sum_salary":  ("SUM(lonn)", "Total lønnsmasse"),
    "avg_age":     ("AVG(alder)", "Gjennomsnittsalder"),
}

# Tillatte grupperingsdimensjoner → (kolonnenavn, visningsnavn)
DIMENSIONS = {
    "avdeling":          ("avdeling", "Avdeling"),
    "juridisk_selskap":  ("juridisk_selskap", "Selskap"),
    "arbeidsland":       ("arbeidsland", "Land"),
    "kjonn":             ("kjonn", "Kjønn"),
    "aldersgruppe":      (None, "Aldersgruppe"),  # Beregnet felt, spesialhåndtering
    "jobbfamilie":       ("jobbfamilie", "Jobbfamilie"),
    "ansettelsetype":    ("ansettelsetype", "Ansettelsestype"),
    "er_leder":          ("er_leder", "Leder/ikke-leder"),
    "kostsenter":        ("kostsenter", "Kostsenter"),
}

# Tillatte filterdimensjoner → kolonnenavn (samme som DIMENSIONS minus aldersgruppe)
FILTERS = {k: v[0] for k, v in DIMENSIONS.items() if v[0] is not None}
```

### 1.2 Aldersgruppe-håndtering

`aldersgruppe` er et beregnet felt (ikke en kolonne). Håndteres med en CASE-uttrykk i SQL:

```sql
CASE
    WHEN alder < 25 THEN 'Under 25'
    WHEN alder BETWEEN 25 AND 34 THEN '25-34'
    WHEN alder BETWEEN 35 AND 44 THEN '35-44'
    WHEN alder BETWEEN 45 AND 54 THEN '45-54'
    WHEN alder BETWEEN 55 AND 64 THEN '55-64'
    WHEN alder >= 65 THEN '65+'
    ELSE 'Ukjent'
END
```

### 1.3 Query-bygging

```python
def build_analysis_query(
    metric: str,
    group_by: str,
    split_by: str | None = None,
    filters: dict[str, str] | None = None,
    active_only: bool = True,
) -> tuple[str, tuple]:
    """
    Bygg sikker SQL-spørring fra validerte parametere.
    Returnerer (sql_string, params_tuple).
    """
```

Logikk:
1. Valider `metric` mot `METRICS` — 400 hvis ugyldig
2. Valider `group_by` mot `DIMENSIONS` — 400 hvis ugyldig
3. Valider `split_by` mot `DIMENSIONS` (hvis angitt) — 400 hvis ugyldig
4. Valider alle filter-nøkler mot `FILTERS` — 400 hvis ugyldig
5. Bygg SELECT: `group_by_col, [split_by_col,] aggregate_func AS verdi`
6. Bygg WHERE: `er_aktiv = 1` (hvis active_only) + filter-betingelser (parameterisert `?`)
7. Bygg GROUP BY: `group_by_col [, split_by_col]`
8. ORDER BY: `group_by_col`

### 1.4 Respons-format

**Uten split_by (1 dimensjon):**
```json
{
    "meta": {
        "metric": "avg_salary",
        "metric_label": "Gjennomsnittslønn",
        "group_by": "avdeling",
        "group_by_label": "Avdeling",
        "split_by": null,
        "filters": {},
        "total_groups": 5
    },
    "data": {
        "IT": 650000,
        "HR": 580000,
        "Salg": 520000
    }
}
```

**Med split_by (2 dimensjoner):**
```json
{
    "meta": {
        "metric": "count",
        "metric_label": "Antall ansatte",
        "group_by": "avdeling",
        "group_by_label": "Avdeling",
        "split_by": "kjonn",
        "split_by_label": "Kjønn",
        "filters": {},
        "total_groups": 5
    },
    "data": {
        "IT": {"Mann": 12, "Kvinne": 8},
        "HR": {"Mann": 3, "Kvinne": 7},
        "Salg": {"Mann": 6, "Kvinne": 5}
    }
}
```

### 1.5 API-endepunkt

```python
# web/routes/analyze.py
@router.get("/analyze")
async def analyze(
    metric: str = Query(..., description="Metrikk: count, avg_salary, etc."),
    group_by: str = Query(..., description="Gruppering: avdeling, kjonn, etc."),
    split_by: str | None = Query(None, description="Ekstra inndeling"),
    active_only: bool = Query(True),
    # Dynamiske filtre:
    filter_avdeling: str | None = Query(None),
    filter_arbeidsland: str | None = Query(None),
    filter_juridisk_selskap: str | None = Query(None),
    filter_kjonn: str | None = Query(None),
    filter_jobbfamilie: str | None = Query(None),
    filter_ansettelsetype: str | None = Query(None),
    filter_kostsenter: str | None = Query(None),
    filter_er_leder: str | None = Query(None),
):
```

### 1.6 Metadata-endepunkt

For å populere dropdowns dynamisk:

```python
@router.get("/analyze/options")
async def analyze_options():
    """Returnerer tilgjengelige metrikker, dimensjoner, og unike verdier for filtre."""
    return {
        "metrics": [{"id": k, "label": v[1]} for k, v in METRICS.items()],
        "dimensions": [{"id": k, "label": v[1]} for k, v in DIMENSIONS.items()],
        "filter_values": {
            "avdeling": [...],        # Unike verdier fra DB
            "arbeidsland": [...],
            "juridisk_selskap": [...],
            ...
        }
    }
```

## 2. Frontend — Analyse-tab

### 2.1 UI-layout

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │ Metrikk  │ │Gruppering│ │Inndeling │ │  Filter  │           │
│ │[dropdown]│ │[dropdown]│ │[dropdown]│ │[dropdown]│           │
│ │          │ │          │ │(valgfri) │ │(valgfri) │           │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                 │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│ │Filter-   │  │[Vis      │  │[Lagre    │  │[Templates│        │
│ │verdi     │  │ analyse] │  │ template]│  │ ▼       ]│        │
│ │[dropdown]│  │ (knapp)  │  │ (knapp)  │  │(dropdown)│        │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                 │
│  Graftype: ○ Bar  ○ Horisontal  ○ Stacked  ○ Pie  ○ Doughnut  │
│            (auto-valgt, kan overstyres)                         │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                                                             │ │
│ │                    [CHART CANVAS]                            │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Graftype-logikk

Automatisk default-valg basert på data:

| Situasjon | Default graftype | Andre tilgjengelige |
|-----------|-----------------|-------------------|
| 1 dim, ≤6 kategorier | Pie | Bar, Horisontal bar, Doughnut |
| 1 dim, >6 kategorier | Bar | Horisontal bar, Pie, Doughnut |
| 2 dim (split_by) | Stacked bar | Grouped bar, Horisontal bar |
| 1 dim, >15 kategorier | Horisontal bar | Bar |

Implementeres som:
```javascript
function suggestChartType(data, hasSplitBy) {
    const groupCount = Object.keys(data).length;
    if (hasSplitBy) return { default: 'stacked', available: ['stacked', 'grouped', 'horizontalBar'] };
    if (groupCount <= 6) return { default: 'pie', available: ['pie', 'bar', 'horizontalBar', 'doughnut'] };
    if (groupCount > 15) return { default: 'horizontalBar', available: ['horizontalBar', 'bar'] };
    return { default: 'bar', available: ['bar', 'horizontalBar', 'pie', 'doughnut'] };
}
```

Graftype-valget vises som radio-buttons under dropdowns. Default er forhåndsvalgt, men brukeren kan klikke en annen. Når data oppdateres, resettes valget til auto-default (med mindre brukeren har låst det).

### 2.3 Template-lagring (localStorage)

```javascript
// Lagre
const template = {
    name: "Lønn per avdeling (kvinner, Norge)",
    metric: "avg_salary",
    group_by: "avdeling",
    split_by: null,
    filters: { arbeidsland: "Norge", kjonn: "Kvinne" },
    chart_type: "bar",  // null = auto
    created: "2026-02-19T12:00:00"
};
localStorage.setItem('analysis_templates', JSON.stringify([...existing, template]));

// Laste inn → populer dropdowns → kjør analyse
```

### 2.4 Filter-kaskade

Når brukeren velger en filter-dimensjon (f.eks. "Land"), populeres filter-verdi-dropdownen med unike verdier fra `/api/analyze/options`. Disse hentes én gang ved tab-innlasting og caches.

## 3. Ny filstruktur

```
hr_database/
    analyzer.py          (NY: whitelists, query-builder, analyze-funksjon)
web/routes/
    analyze.py           (NY: /api/analyze og /api/analyze/options endepunkter)
web/static/js/
    app.js               (ENDRET: ny loadAnalyse() funksjon, template-logikk)
    charts.js            (ENDRET: evt. ny renderGroupedBarChart())
web/templates/
    index.html           (ENDRET: ny "Analyse"-tab med UI)
web/
    app.py               (ENDRET: registrer analyze-router)
tests/
    test_analyzer.py     (NY: tester for analyzer.py)
    test_api.py          (ENDRET: tester for /api/analyze endepunktet)
```

## 4. Sikkerhet

- **Ingen bruker-input i SQL direkte** — alle kolonne- og funksjonsnavn hentes fra whitelists
- Filter-verdier sendes som parameteriserte `?`-verdier (standard SQLite injection-sikring)
- Validering av alle input-verdier skjer FØR SQL bygges
- Ugyldig input gir HTTP 400 med tydelig feilmelding
