# Tasks: Dashboard UX Improvements

## Implementeringsrekkefølge

Småfikser og backend først, deretter frontend i logisk rekkefølge.
Hver oppgave har tester der det er relevant.

---

## Task 1: Småfikser — duplikat tab + farge-bug
**Filer:** `web/templates/index.html`, `web/static/js/charts.js`, `web/static/js/app.js`

### 1a. Fjern duplikat Analyse-tab
- Fjern linje 30 i `index.html` (den andre `<button class="tab" data-tab="analyse">Analyse</button>`)

### 1b. Farge-fix for bar/horizontalBar
- `charts.js`: Endre `renderBarChart()` — default `backgroundColor` til `labels.map((_, i) => PALETTE[i % PALETTE.length])` når `options.colors` ikke er satt
- `charts.js`: Samme endring i `renderHorizontalBarChart()`
- Behold muligheten for callere å sende enkelt farge-streng (churn-grafer bruker `COLORS.negative`)

### 1c. Fjern hardkodet farge i analyse
- `app.js`: I `renderAnalyseChart()` — fjern `{ colors: COLORS.secondary }` fra horizontalBar-caset, slik at PALETTE-default brukes

### Verifikasjon
- Visuell sjekk: bar/horizontalBar i Analyse viser ulike farger per bar
- Eksisterende tester passerer (`pytest tests/`)

---

## Task 2: Backend — "Alle" som gruppering
**Filer:** `hr/analyzer.py`, `web/routes/analyze.py`, `tests/test_analyzer.py`, `tests/test_api.py`

### 2a. analyzer.py — spesialhåndtering i `build_analysis_query()`
- Når `group_by == "alle"`: bygg SQL uten GROUP BY, kun aggregering
- Returner `SELECT {agg_func} AS verdi FROM ansatte {where_clause}`
- Håndter filter (WHERE-clause) som vanlig

### 2b. analyzer.py — `run_analysis()` tilpasning
- Når `group_by == "alle"`: returner `{"data": {"Alle": <verdi>}}`
- `meta` inkluderer `group_by: "alle"` og `group_by_label: "Alle (total)"`

### 2c. analyze.py — inkluder "Alle" i options
- I `/api/analyze/options`-endepunktet: legg til `{"id": "alle", "label": "Alle (total)"}` først i dimensions-listen

### 2d. Tester
- `tests/test_analyzer.py`: Test `build_analysis_query(metric="count", group_by="alle")` — verifiser at SQL ikke har GROUP BY
- `tests/test_analyzer.py`: Test `run_analysis(metric="count", group_by="alle")` — verifiser retur `{"Alle": N}`
- `tests/test_api.py`: Test `GET /api/analyze?metric=count&group_by=alle` — verifiser 200 + korrekt respons
- `tests/test_api.py`: Test at `/api/analyze/options` inkluderer "alle" i dimensions

### Verifikasjon
- `pytest tests/test_analyzer.py tests/test_api.py` — alle tester passerer

---

## Task 3: Frontend — enklere analyse-velger
**Filer:** `web/templates/index.html`, `web/static/css/style.css`, `web/static/js/app.js`

### 3a. HTML — omstrukturere analyse-seksjon
- Metrikk + Gruppering alltid synlige med nye labels ("Hva vil du måle?" / "Hvordan dele opp?")
- "Vis analyse"-knappen rett under hoveddelen
- `<details>` "Flere valg" — inneholder Inndeling + Filter (inline layout)
- `<details>` "Maler" — inneholder mal-velger + Lagre/Slett-knapper
- Filter-dimensjon + filter-verdi på én linje med label "Filtrer på:"

### 3b. CSS — styling for progressiv avsløring
- `<details>` / `<summary>` styling — pilikon, padding, border
- Kompakt filter-layout (inline dropdowns)
- Visuelt hierarki: primære felter fremtredende, sekundære dempet

### 3c. JS — "Alle"-håndtering i frontend
- Når `group_by === "alle"`: vis KPI-kort i stedet for graf
- Skjul graftype-pills når "Alle" er valgt
- Skjul split_by-dropdown når "Alle" er valgt (gir ikke mening uten gruppering)
- Automatisk åpne "Flere valg" `<details>` hvis en mal med inndeling/filter lastes inn

### Verifikasjon
- Visuell sjekk: analyse-velgeren viser progressiv avsløring
- "Alle" viser KPI-kort, graftype-pills og split_by skjules
- Eksisterende analyse-funksjonalitet fungerer som før

---

## Task 4: Frontend — festede analyser (pin to dashboard)
**Filer:** `web/templates/index.html`, `web/static/js/app.js`, `web/static/css/style.css`

### 4a. HTML — pin-knapp i analyse-resultat
- Legg til "Fest til oversikt" (📌) knapp i `#analyse-result` chart-header
- Legg til `<div id="pinned-charts-container">` i oversikt-seksjonen

### 4b. JS — pin/unpin-logikk
- `pinChart()`: Les dropdown-verdier + chart-type, generer unik ID, lagre til `dashboard_pinned_charts` i localStorage
- `unpinChart(id)`: Fjern fra localStorage, fjern DOM-element, destroy Chart.js-instans
- Bekreftelsesanimasjon ved pin (grønn checkmark, fadeout)

### 4c. JS — `loadOversikt()` utvidet
- Etter de faste KPI-kort + 2 grafer: les `dashboard_pinned_charts` fra localStorage
- For hver pinned chart: kall `/api/analyze?...` og rendre i `<div class="chart-container pinned-chart">`
- Hver pinned chart har unpin-knapp (✕)
- Gjenbrukbar rendrefunksjon (extract fra `renderAnalyseChart()`)

### 4d. CSS — pinned chart grid
- `.pinned-charts-grid` — 2-kolonne responsivt grid (gjenbruk `.grid-2`)
- `.pinned-chart` — chart-container med unpin-knapp
- `.btn-unpin` styling

### Verifikasjon
- Pin en analyse → vises på Oversikt ved neste besøk
- Unpin → fjernes fra Oversikt og localStorage
- Flere pinnede analyser vises i grid

---

## Task 5: Frontend — dashboard-maler
**Filer:** `web/static/js/app.js`, `web/templates/index.html`, `web/static/css/style.css`

### 5a. JS — DASHBOARD_PRESETS konstant
- Definer 3 maler: 'hr-oversikt', 'ledelse', 'lonn-analyse' (se design.md A.4)
- Hver mal har label, description, og pins-array

### 5b. HTML — preset-velger i Oversikt
- `<div class="dashboard-preset-bar">` med `<select id="dashboard-preset">`
- Opsjoner: "Mine grafer" (default) + 3 maler
- Plasseres under KPI-kort / faste grafer, over pinned charts

### 5c. JS — preset-logikk
- "Mine grafer" = vis brukerens egne pinned charts fra localStorage
- Velge en mal = vis malens grafer i pinned-charts-containeren
- Brukerens pinned charts slettes IKKE ved malvalg (lagres separat)
- Bytte tilbake til "Mine grafer" = vis brukerens egne igjen

### 5d. CSS — preset-bar styling
- `.dashboard-preset-bar` — horisontalt layout, subtil bakgrunn
- `.preset-label` styling

### Verifikasjon
- Velg "Ledelse" → vises 3 forhåndsdefinerte grafer
- Bytt til "Mine grafer" → vises brukerens egne pinnede grafer
- Maler endrer ikke localStorage

---

## Task 6: Slutt-testing og cleanup
**Filer:** Alle endrede filer

### 6a. Kjør full test-suite
- `pytest tests/` — alle tester passerer, inkludert nye tester fra Task 2

### 6b. Visuell gjennomgang
- Oversikt: KPI-kort + faste grafer + pinned charts + preset-velger
- Analyse: progressiv avsløring, "Alle" → KPI-kort, farger korrekt
- Ingen regresjoner i andre faner (Churn, Tenure, Lønn, Søk, Import)

### 6c. Cleanup
- Fjern eventuell debug-kode / console.log
- Sjekk at ingen ubrukte funksjoner/variabler ble etterlatt
