# Tasks: Custom Analysis Builder

## Fase 1: Backend — Analyzer-modul
> Ny `analyzer.py` med whitelists og query-builder

- [x] Opprett `hr_database/analyzer.py` med METRICS, DIMENSIONS, FILTERS whitelists
- [x] Implementer `AGE_CASE_EXPR` SQL CASE-uttrykk for aldersgrupper
- [x] Implementer `build_analysis_query()` — bygger sikker SQL fra validerte params
- [x] Implementer `run_analysis()` — kjører query og returnerer strukturert resultat
- [x] Implementer `get_filter_values()` — henter unike verdier per dimensjon fra DB
- [x] Eksporter fra `hr_database/__init__.py`

## Fase 2: Backend — API-endepunkter
> Ny route-fil `web/routes/analyze.py`

- [x] Opprett `web/routes/analyze.py` med router
- [x] Implementer `GET /api/analyze` — hovedendepunkt med metric, group_by, split_by, filtre
- [x] Implementer `GET /api/analyze/options` — returnerer metrikker, dimensjoner, filterverdier
- [x] Registrer analyze-router i `web/app.py`
- [x] Valider at ugyldige params gir HTTP 400 med tydelig melding

## Fase 3: Backend — Tester
> Nye tester i `test_analyzer.py` + utvidelse av `test_api.py`

- [x] Opprett `tests/test_analyzer.py`
- [x] Test: `build_analysis_query()` med 1 dimensjon → riktig SQL
- [x] Test: `build_analysis_query()` med 2 dimensjoner (split_by) → riktig SQL
- [x] Test: `build_analysis_query()` med filter → riktig WHERE-clause
- [x] Test: `build_analysis_query()` med aldersgruppe → CASE-uttrykk i SQL
- [x] Test: ugyldig metric → ValueError
- [x] Test: ugyldig dimension → ValueError
- [x] Test: `run_analysis()` med testdata → riktig respons-format (1 dim)
- [x] Test: `run_analysis()` med testdata → riktig respons-format (2 dim)
- [x] Test: `get_filter_values()` → returnerer unike verdier
- [x] Test API: `GET /api/analyze?metric=count&group_by=kjonn` → 200
- [x] Test API: `GET /api/analyze?metric=invalid` → 400
- [x] Test API: `GET /api/analyze/options` → returnerer struktur med metrics/dimensions
- [x] Kjør alle tester — sikre at eksisterende tester fortsatt passerer (216 passed, 2 xfailed)

## Fase 4: Frontend — HTML + Analyse-tab
> Ny tab i `index.html`

- [x] Legg til "Analyse"-tab-knapp i nav (mellom "Jobbfamilier" og "Søk")
- [x] Legg til `<section id="tab-analyse">` med:
  - Dropdowns: Metrikk, Gruppering, Inndeling (valgfri), Filter-dimensjon, Filter-verdi
  - Pill-buttons for graftype (skjult til data er lastet)
  - Knapper: "Vis analyse", "Lagre mal"
  - Template-dropdown + "Slett"-knapp
  - Chart canvas

## Fase 5: Frontend — JavaScript-logikk
> Analyse-logikk i `app.js`

- [x] Legg til `loadAnalyse()` i `loadTabData()` switch
- [x] Implementer `loadAnalyseOptions()` — henter `/api/analyze/options`, populerer dropdowns
- [x] Implementer `runAnalysis()` — bygger query-params fra dropdowns, henter data, rendrer graf
- [x] Implementer `suggestChartType(data, hasSplitBy)` — returnerer default + tilgjengelige typer
- [x] Implementer graftype pill-buttons — oppdateres etter data-lasting, overstyrbar
- [x] Implementer filter-kaskade: velg dimensjon → populer verdi-dropdown
- [x] Implementer `renderGroupedBarChart()` i `charts.js` (bar uten stacking)
- [x] Implementer template-lagring: `saveTemplate()`, `loadTemplate()`, `deleteTemplate()`
- [x] Implementer template-dropdown som oppdateres fra localStorage

## Fase 6: Frontend — CSS
> Styling for analyse-tab

- [x] Style analyse-kontrollers (dropdowns i rad, responsivt)
- [x] Style graftype pill-buttons (pill-lignende, markert valg)
- [x] Style template-seksjon (dropdown + knapper)

## Fase 7: Integrasjon + Docker
> Rebuild og verifiser

- [x] Kjør alle tester lokalt (216 passed, 2 xfailed)
- [ ] `docker compose build && docker compose up -d`
- [ ] Manuell test i nettleser: bygg en analyse, bytt graftype, lagre template
