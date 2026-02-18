# Tasks: Local Web App

## Fase 1: Prosjektinfrastruktur

### 1.1 Opprett requirements.txt
- [x] Deklarér alle avhengigheter med versjoner: `pandas`, `numpy`, `openpyxl`, `matplotlib`, `fastapi`, `uvicorn`, `python-multipart`
- [x] Verifiser at `pip install -r requirements.txt` fungerer i et rent virtualenv

### 1.2 Opprett mappestruktur for web
- [x] Opprett `konsern-database/web/` med undermapper: `routes/`, `static/css/`, `static/js/`, `templates/`
- [x] Opprett `__init__.py`-filer der nødvendig

### 1.3 Legg til .gitignore
- [x] Opprett `.gitignore` i prosjektrot med mønstre for: `*.db`, `*.xlsx`, `~$*`, `__pycache__/`, `.pytest_cache/`, `rapporter/`, `.env`, `*.pyc`, `node_modules/`

### 1.4 Miljøvariabel-støtte i database.py
- [x] Les `DB_PATH` fra `os.environ` med fallback til eksisterende `DEFAULT_DB_PATH`
- [x] Verifiser at eksisterende CLI og tester ikke påvirkes

---

## Fase 2: FastAPI Backend

### 2.1 Opprett FastAPI-applikasjon (`web/app.py`)
- [x] Initialiser FastAPI-app med tittel og beskrivelse
- [x] Monter statiske filer (`/static`)
- [x] Konfigurer Jinja2-templates
- [x] Legg til CORS-middleware (for lokal utvikling)
- [x] Opprett rot-rute som serverer `index.html`
- [x] Inkluder alle route-moduler
- [x] Les `HOST` og `PORT` fra miljøvariabler
- [x] Opprett `HRAnalytics`-instans ved oppstart (app lifespan)

### 2.2 Analytics-ruter (`web/routes/analytics.py`)
- [x] Opprett ruter for oversikt: `/api/overview/summary`, `/api/overview/by-country`, `/api/overview/by-company`, `/api/overview/by-department`
- [x] Opprett ruter for alder: `/api/age/distribution`, `/api/age/distribution-pct`, `/api/age/by-country`
- [x] Opprett ruter for kjønn: `/api/gender/distribution`, `/api/gender/by-country`
- [x] Opprett ruter for churn: `/api/churn/calculate`, `/api/churn/monthly`, `/api/churn/by-age`, `/api/churn/by-country`, `/api/churn/by-gender`, `/api/churn/reasons`
- [x] Opprett ruter for tenure: `/api/tenure/average`, `/api/tenure/distribution`
- [x] Opprett ruter for ansettelsestype: `/api/employment/types`, `/api/employment/fulltime-parttime`
- [x] Opprett ruter for ledelse: `/api/management/ratio`
- [x] Opprett ruter for søk: `/api/search`
- [x] Opprett ruter for kombinert: `/api/combined/summary`, `/api/combined/age-gender-country`
- [x] Opprett ruter for planlagte avganger: `/api/departures/planned`
- [x] Opprett ruter for lønn: `/api/salary/summary`, `/api/salary/by-department`, `/api/salary/by-country`, `/api/salary/by-gender`, `/api/salary/by-age`, `/api/salary/by-job-family`
- [x] Opprett ruter for jobbfamilier: `/api/job-family/distribution`, `/api/job-family/by-country`, `/api/job-family/by-gender`
- [x] Legg til `active_only` query-parameter med default `True` på alle relevante ruter
- [x] Verifiser at alle ruter returnerer korrekt JSON via Swagger UI (`/docs`)

### 2.3 Import-ruter (`web/routes/import_routes.py`)
- [x] `POST /api/import/upload` — motta Excel-fil via multipart form data
- [x] Lagre opplastet fil til temp-mappe, kall `import_excel()`, slett temp-fil
- [x] Returner JSON med antall importerte rader og eventuelle feil
- [x] Støtt `clear_existing` parameter (boolean)
- [x] `GET /api/import/history` — returner import-logg som JSON
- [x] `GET /api/status` — returner database-status (antall ansatte, aktive, siste import)

### 2.4 Rapport-ruter (`web/routes/report.py`)
- [x] `GET /api/report/pdf` — generer PDF og returner som `FileResponse`
- [x] Støtt `year` query-parameter for churn-del av rapport
- [x] Sett riktig Content-Type og filnavn-header for nedlasting
- [x] Rydd opp temp-fil etter sending

---

## Fase 3: Frontend

### 3.1 HTML-layout (`web/templates/index.html`)
- [x] Responsive layout med header, tab-navigasjon og innholdsområde
- [x] 10 tabs: Oversikt, Alder, Geografi, Kjønn, Churn, Tenure, Lønn, Jobbfamilier, Søk, Import
- [x] "Last ned PDF"-knapp i headeren
- [x] Drag-and-drop-sone på Import-fanen
- [x] Lasteindikator for datahenting
- [x] Tom-tilstand ("Ingen data — importer en Excel-fil for å komme i gang")
- [x] Inkluder Chart.js lokalt (ikke CDN — offline-støtte)
- [x] Norskspråklige labels overalt

### 3.2 Styling (`web/static/css/style.css`)
- [x] Ren, profesjonell stil — ingen rammeverk, bare CSS
- [x] Fargeskjema som matcher PDF-rapporten (COLORS-paletten fra report_generator.py)
- [x] Responsiv: fungerer på 1280px+ (typisk kontorskjerm)
- [x] Kort- og tabellstiler for nøkkeltall
- [x] Drag-and-drop-sone med visuell feedback
- [x] Tab-navigasjon med aktiv-indikator

### 3.3 JavaScript — Navigasjon og data (`web/static/js/app.js`)
- [x] Tab-bytting med URL-hash (`#oversikt`, `#alder`, etc.)
- [x] Generisk `fetchData(url)` med feilhåndtering og lasteindikator
- [x] Populer hver tab med data fra API ved klikk (lazy loading)
- [x] Nøkkeltall-kort med tall fra `/api/overview/summary`
- [x] Import-funksjon: drag-and-drop + filvelger, POST til API, vis resultat
- [x] Søkeside: inputfelt + filtre, vis resultater i tabell
- [x] PDF-nedlastingknapp: hent `/api/report/pdf` og trigger browser-download
- [x] Churn-fane: periodevalg (dropdowns for start/slutt eller forhåndsdefinerte perioder)

### 3.4 JavaScript — Grafer (`web/static/js/charts.js`)
- [x] Wrapper-funksjoner for Chart.js med konsistent stil
- [x] `renderBarChart(canvasId, labels, data, options)` — brukes for de fleste fordelinger
- [x] `renderHorizontalBarChart(canvasId, labels, data, options)` — lønn per avdeling, jobbfamilier
- [x] `renderPieChart(canvasId, labels, data, options)` — kjønnsfordeling
- [x] `renderLineChart(canvasId, labels, datasets, options)` — månedlig churn
- [x] `renderStackedBarChart(canvasId, labels, datasets, options)` — kjønn per land, jobbfam per land
- [x] Norske etiketter og tallformat (mellomrom som tusenskilletegn)
- [x] Fargeskjema som matcher PDF-rapport (COLORS og CATEGORY_PALETTE)
- [x] Tooltip med detaljer ved hover
- [x] Automatisk ødelegg eksisterende chart før re-render (unngå Chart.js memory leak)

---

## Fase 4: Docker

### 4.1 Opprett Dockerfile
- [x] Basert på `python:3.13-slim`
- [x] Kopier kode og installer avhengigheter
- [x] Pre-bygg matplotlib font cache (`python -c "import matplotlib.pyplot"`)
- [x] Eksponer port 8080
- [x] Kjør med `uvicorn web.app:app --host 0.0.0.0 --port 8080`
- [x] Sett `WORKDIR /app`
- [x] Verifiser image-størrelse — 623 MB (matplotlib/numpy/pandas er store; akseptabelt)

### 4.2 Opprett docker-compose.yml
- [x] Definer `hr-analyse`-service med port-mapping og named volume
- [x] Volume for `/app/data` (SQLite-persistens)
- [x] Miljøvariabler: `DB_PATH=/app/data/ansatte.db`

### 4.3 Bygg og test
- [x] `docker build -t hr-analyse .`
- [x] `docker run -p 8080:8080 hr-analyse`
- [x] Verifiser at appen starter og er tilgjengelig på `http://localhost:8080`
- [x] Test import via web-UI
- [x] Test alle analyse-faner
- [x] Test PDF-nedlasting
- [x] Stopp og restart container — verifiser at data overlever

---

## Fase 5: Testing og kvalitetssikring

### 5.1 API-tester
- [x] Opprett `tests/test_api.py` med FastAPI TestClient
- [x] Test alle analytics-endepunkter mot test-databasen (gjenbruk conftest-fixtures)
- [x] Test import-endepunkt med feilhåndtering (ugyldig filtype, manglende fil)
- [x] Test rapport-endepunkt (verifiser PDF-respons)
- [x] Test feilhåndtering (ugyldig fil, tom database, ukjente parametere)
- [x] Test active_only-parameter på alle relevante endepunkter (19 endepunkter parametrisert)
- [x] Test frontend-servering (index.html, statiske filer, Swagger docs)

### 5.2 Verifiser eksisterende tester
- [x] `python -m pytest tests/ -v` — 164 tester passerer (91 eksisterende + 73 nye + 2 ekstra database-tester), 2 xfail
- [x] Ingen endringer i analytics/importer/database krevd

### 5.3 Manuell brukertesting
- [ ] Test hele flyten som en HR-bruker: åpne nettleseren → import → naviger analyser → last ned PDF
- [ ] Verifiser at grensesnittet er forståelig uten opplæring
- [ ] Sjekk at alle grafer viser korrekte tall (sammenlign med CLI-output)

---

## Avhengigheter mellom faser

```
Fase 1 (infrastruktur) ──► Fase 2 (backend) ──► Fase 3 (frontend) ──► Fase 5 (testing)
                                                                   │
                                       Fase 4 (Docker) ◄──────────┘
```

Fase 1 og 2 kan delvis overlappende utvikles. Fase 3 krever fungerende API. Fase 4 krever at alt annet fungerer. Fase 5 går parallelt med fase 3 og 4.
