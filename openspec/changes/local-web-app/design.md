# Design: Local Web App

## Approach

Bygge et web-lag over den eksisterende `hr_database/`-pakken uten å endre forretningslogikk. Gjenbruk av analytics, importer og report_generator er 100%. Ny kode er: API-ruter, HTML-sider, JavaScript for grafer, og Docker-konfigurasjon.

## Arkitektur

```
ecit-selskapsanalyse/
├── konsern-database/
│   ├── hr_database/              # UENDRET
│   │   ├── analytics.py          # 30 metoder, returnerer dicts/lists
│   │   ├── database.py           # SQLite init/connect/reset
│   │   ├── importer.py           # Excel → SQLite
│   │   ├── report_generator.py   # matplotlib → PDF
│   │   └── __init__.py
│   │
│   ├── web/                      # NY — alt web-relatert
│   │   ├── app.py                # FastAPI-applikasjon
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── analytics.py      # GET-endepunkter for alle analyser
│   │   │   ├── import_routes.py  # POST /api/import (fileopplasting)
│   │   │   └── report.py         # GET /api/report/pdf (generér og last ned)
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   └── style.css
│   │   │   └── js/
│   │   │       ├── app.js        # Navigasjon, datahenting
│   │   │       └── charts.js     # Chart.js wrapper-funksjoner
│   │   └── templates/
│   │       └── index.html        # Enkel SPA-aktig side
│   │
│   ├── hr_cli.py                 # UENDRET — CLI fungerer fortsatt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── tests/                    # Eksisterende + nye API-tester
```

## Key Decisions

### 1. FastAPI som backend-rammeverk

**Valg:** FastAPI fremfor Flask, Django, eller Streamlit.

**Begrunnelse:**
- Automatisk JSON-serialisering av dicts (analytics returnerer allerede dicts)
- Automatisk API-dokumentasjon via Swagger UI (`/docs`) — nyttig for debugging
- Async-støtte innebygd (relevant for fremtidig flerbruker)
- Enkel fileopplasting med `UploadFile`
- Lett (få avhengigheter, raskt oppstart)

Streamlit ble vurdert men avvist: gir for lite kontroll over UX, vanskelig å style for ikke-tekniske brukere, og låser oss til Streamlit sin deploy-modell.

### 2. Vanilla HTML/JS frontend (ingen React/Vue)

**Valg:** Enkel HTML med Chart.js, ingen JavaScript-rammeverk.

**Begrunnelse:**
- Ingen build-steg, ingen node_modules, ingen bundler
- HR-folk trenger ikke SPA-funksjonalitet
- Chart.js fra CDN — ett script-tag
- Enklere å vedlikeholde for en liten app
- Kan alltid migrere til React/Vue senere om behovet oppstår

### 3. API-design: Én rute per analytics-metode

Direkte 1:1-mapping mellom `HRAnalytics`-metoder og API-endepunkter:

| Analytics-metode | HTTP-endepunkt | Query params |
|-----------------|----------------|--------------|
| `employees_summary()` | `GET /api/overview/summary` | — |
| `employees_by_country()` | `GET /api/overview/by-country` | `active_only` |
| `employees_by_company()` | `GET /api/overview/by-company` | `active_only` |
| `employees_by_department()` | `GET /api/overview/by-department` | `active_only` |
| `age_distribution()` | `GET /api/age/distribution` | `active_only` |
| `age_distribution_pct()` | `GET /api/age/distribution-pct` | `active_only` |
| `age_distribution_by_country()` | `GET /api/age/by-country` | `active_only` |
| `gender_distribution()` | `GET /api/gender/distribution` | `active_only` |
| `gender_by_country()` | `GET /api/gender/by-country` | `active_only` |
| `calculate_churn()` | `GET /api/churn/calculate` | `start_date`, `end_date`, `by` |
| `monthly_churn()` | `GET /api/churn/monthly` | `year` |
| `churn_by_age()` | `GET /api/churn/by-age` | `start_date`, `end_date` |
| `churn_by_country()` | `GET /api/churn/by-country` | `start_date`, `end_date` |
| `churn_by_gender()` | `GET /api/churn/by-gender` | `start_date`, `end_date` |
| `get_termination_reasons()` | `GET /api/churn/reasons` | `start_date`, `end_date` |
| `average_tenure()` | `GET /api/tenure/average` | `active_only` |
| `tenure_distribution()` | `GET /api/tenure/distribution` | `active_only` |
| `employment_type_distribution()` | `GET /api/employment/types` | `active_only` |
| `fulltime_vs_parttime()` | `GET /api/employment/fulltime-parttime` | `active_only` |
| `manager_ratio()` | `GET /api/management/ratio` | `active_only` |
| `search_employees()` | `GET /api/search` | `name`, `department`, `country`, `company`, `active_only`, `limit` |
| `planned_departures()` | `GET /api/departures/planned` | `months_ahead` |
| `combined_summary()` | `GET /api/combined/summary` | `country`, `active_only` |
| `age_and_gender_by_country()` | `GET /api/combined/age-gender-country` | `active_only` |
| `salary_summary()` | `GET /api/salary/summary` | `active_only` |
| `salary_by_department()` | `GET /api/salary/by-department` | `active_only` |
| `salary_by_country()` | `GET /api/salary/by-country` | `active_only` |
| `salary_by_gender()` | `GET /api/salary/by-gender` | `active_only` |
| `salary_by_age()` | `GET /api/salary/by-age` | `active_only` |
| `salary_by_job_family()` | `GET /api/salary/by-job-family` | `active_only` |
| `job_family_distribution()` | `GET /api/job-family/distribution` | `active_only` |
| `job_family_by_country()` | `GET /api/job-family/by-country` | `active_only` |
| `job_family_by_gender()` | `GET /api/job-family/by-gender` | `active_only` |
| — | `POST /api/import/upload` | multipart file + `clear_existing` |
| — | `GET /api/import/history` | — |
| — | `GET /api/report/pdf` | `year` |
| — | `GET /api/status` | — |

### 4. Frontend-struktur: Tab-basert dashboard

En enkeltside med tabs som speiler CLI-menyen:

```
┌──────────────────────────────────────────────────────┐
│  HR Analyse                              [Last ned PDF] │
├──────────────────────────────────────────────────────┤
│  Oversikt │ Alder │ Geografi │ Churn │ Lønn │ ...   │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────┐  ┌─────────────────────────┐   │
│  │ Nøkkeltall       │  │ Ansatte per land (graf) │   │
│  │ Aktive: 62       │  │ ████████ Norge 40      │   │
│  │ Snitt alder: 38  │  │ ████ Danmark 15        │   │
│  │ Lederandel: 12%  │  │ ██ Sverige 7           │   │
│  └─────────────────┘  └─────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Kjønnsfordeling (kakediagram)                │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

Tabs:
1. **Oversikt** — Nøkkeltall, ansatte per land, per selskap, ansettelsestyper, lederandel
2. **Alder** — Aldersfordeling, per land
3. **Geografi** — Per land, per selskap, per avdeling
4. **Kjønn** — Fordeling, per land
5. **Churn** — Periodevalg, månedlig linje, oppsigelsesårsaker
6. **Tenure** — Snitt, fordeling, heltid/deltid
7. **Lønn** — Snitt, per avdeling/land/kjønn/alder/jobbfamilie, lønnsgap
8. **Jobbfamilier** — Fordeling, per land, kjønnsbalanse
9. **Søk** — Fritekst-søk med filtre
10. **Import** — Drag-and-drop Excel, import-historikk

### 5. Datahåndtering i Docker

```yaml
# docker-compose.yml
services:
  hr-analyse:
    image: hr-analyse:latest
    ports:
      - "8080:8080"
    volumes:
      - hr-data:/app/data    # SQLite-filen overlever restart
    environment:
      - DB_PATH=/app/data/ansatte.db

volumes:
  hr-data:
```

SQLite-databasen mountes som et named volume. Brukeren mister ikke data ved oppgradering av containeren.

### 6. Konfigurasjon via miljøvariabler

For containerisering innføres env-variabler (med fornuftige defaults):

| Variabel | Default | Beskrivelse |
|----------|---------|-------------|
| `DB_PATH` | `./ansatte.db` | Sti til SQLite-databasen |
| `HOST` | `0.0.0.0` | Lytteadresse |
| `PORT` | `8080` | Portnummer |

Disse leses i `web/app.py` med fallback til eksisterende `DEFAULT_DB_PATH`-logikk.

## Endringer i eksisterende kode

### Ingen endringer i forretningslogikk

`analytics.py`, `importer.py`, `database.py` og `report_generator.py` forblir uendret. All ny kode er i `web/`-mappen.

### Minimale tilpasninger

| Fil | Endring | Grunn |
|-----|---------|-------|
| `database.py` | Les `DB_PATH` env-variabel med fallback | Volume mount i Docker |
| `importer.py` | Ingen | `import_excel()` tar allerede `filepath` som parameter |
| `report_generator.py` | Ingen | `generate_report()` tar allerede `output_path` som parameter |
| `__init__.py` | Ingen | Eksporterer allerede alt vi trenger |

### Ny kode

| Komponent | Estimert størrelse | Kompleksitet |
|-----------|-------------------|-------------|
| `web/app.py` | ~50 linjer | Lav — FastAPI setup, CORS, static files |
| `web/routes/analytics.py` | ~200 linjer | Lav — mekanisk mapping av metoder til ruter |
| `web/routes/import_routes.py` | ~60 linjer | Medium — filhåndtering, temp-fil, feilhåndtering |
| `web/routes/report.py` | ~30 linjer | Lav — kall generate_report, returner FileResponse |
| `web/templates/index.html` | ~200 linjer | Medium — layout, tabs, dragområde |
| `web/static/css/style.css` | ~150 linjer | Lav — enkel, ren styling |
| `web/static/js/app.js` | ~200 linjer | Medium — tab-navigasjon, API-kall, feilhåndtering |
| `web/static/js/charts.js` | ~300 linjer | Medium — Chart.js-konfigurasjoner per graftype |
| `Dockerfile` | ~20 linjer | Lav |
| `docker-compose.yml` | ~15 linjer | Lav |
| `requirements.txt` | ~10 linjer | Lav |

**Totalt ny kode: ~1200 linjer**

## Risks

| Risiko | Konsekvens | Tiltak |
|--------|-----------|--------|
| SQLite tåler ikke samtidige skrivinger | Import midt i analyse kan krasje | Kun én bruker per instans (i scope). Senere: PostgreSQL eller write-lock. |
| Matplotlib er tregt i container (font cache) | Første PDF tar lang tid | Pre-bygg font cache i Dockerfile |
| Docker Desktop kreves på brukerens maskin | Ekstra installasjonssteg | Dokumenter tydelig. Vurder Podman som alternativ. |
| PII i SQLite uten kryptering | Sensitiv data tilgjengelig via filsystem | Dokumentert som out-of-scope. Adresseres i neste fase. |
| Chart.js fra CDN krever internett | Offline-bruk feiler | Bunt Chart.js lokalt i static/ |
| Excel-format endres fra Verismo HR | Import feiler | Eksisterende COLUMN_MAPPING håndterer dette; feilmelding vises i UI |
