# Design: Dashboard UX Improvements

## Arkitektur-oversikt

Endringene fordeler seg på 5 områder. Ingen backend-endringer er nødvendig for A, B, D, E — kun C ("Alle" som gruppering) krever backend-endring.

```
┌─ A. Oversikt: Festede analyser ────────────────────────────────┐
│  localStorage (pinnedCharts[])  →  loadOversikt()  →  canvas   │
│  "Fest til oversikt"-knapp i Analyse-tab                        │
│  Dashboard-maler: forhåndsdefinerte sett med pinnede analyser   │
└─────────────────────────────────────────────────────────────────┘

┌─ B. Enklere analyse-velger ────────────────────────────────────┐
│  HTML: progressiv avsløring med <details>/<summary>             │
│  JS: ingen endring i runAnalysis()-logikk                       │
└─────────────────────────────────────────────────────────────────┘

┌─ C. "Alle" som gruppering ────────────────────────────────────┐
│  Backend: spesialhåndtering i analyzer.py (ingen GROUP BY)      │
│  Frontend: vise KPI-kort i stedet for graf                      │
└─────────────────────────────────────────────────────────────────┘

┌─ D. Farge-fix bar/horizontalBar ──────────────────────────────┐
│  charts.js: bruk PALETTE per bar ved enkeltserie                │
└─────────────────────────────────────────────────────────────────┘

┌─ E. Småfikser ────────────────────────────────────────────────┐
│  HTML: fjern duplikat tab-knapp                                 │
└─────────────────────────────────────────────────────────────────┘
```

## A. Oversikt — Festede analyser

### A.1 Datamodell (localStorage)

```javascript
// Nøkkel: 'dashboard_pinned_charts'
// Verdi: Array av pinned chart-konfigurasjoner
[
    {
        id: "pin-1708300000000",       // Unik ID (timestamp-basert)
        metric: "count",
        group_by: "arbeidsland",
        split_by: null,
        filter_dim: null,
        filter_val: null,
        chart_type: "bar",             // null = auto
        title: "Antall ansatte per Land",  // Auto-generert tittel
        pinned_at: "2026-02-19T12:00:00Z",
    },
    ...
]
```

### A.2 "Fest til oversikt"-knapp

Legges til i analyse-resultat-containeren (`#analyse-result`), ved siden av chart-title:

```html
<div id="analyse-result" class="chart-container hidden">
    <div class="chart-header">
        <h3 id="analyse-chart-title">Resultat</h3>
        <div class="chart-actions">
            <button class="btn-chart-action" id="btn-pin-analyse" title="Fest til oversikt">
                📌 <!-- eller SVG pin-ikon -->
            </button>
            <!-- eksisterende kopier/last ned-knapper -->
        </div>
    </div>
    <canvas id="chart-analyse"></canvas>
</div>
```

Klikk på knappen:
1. Leser nåværende dropdown-verdier + analyseChartType
2. Genererer title fra `analyse-chart-title`-teksten
3. Pusher til `dashboard_pinned_charts` i localStorage
4. Viser kort bekreftelse (grønn checkmark, som kopier-knappen)

### A.3 Oversikt-rendering

`loadOversikt()` utvides til å:
1. Rendre de faste KPI-kortene (som nå)
2. Rendre de faste 2 grafene (ansettelsestyper + heltid/deltid) (som nå)
3. Lese `dashboard_pinned_charts` fra localStorage
4. For hver pinned chart: kalle `/api/analyze?...` og rendre grafen i en ny `<div class="chart-container">` med en fjern-knapp (×)

Dynamisk HTML for festede grafer:
```html
<div class="chart-container pinned-chart" data-pin-id="pin-1708300000000">
    <div class="chart-header">
        <h3>Antall ansatte per Land</h3>
        <div class="chart-actions">
            <!-- kopier/last ned legges til av ensureChartActions() -->
            <button class="btn-chart-action btn-unpin" title="Fjern fra oversikt">✕</button>
        </div>
    </div>
    <canvas id="pinned-pin-1708300000000"></canvas>
</div>
```

Grafer rendres med samme logikk som `renderAnalyseChart()` — extraheres til en gjenbrukbar funksjon.

### A.4 Dashboard-maler

3 forhåndsdefinerte maler med faste sett av pinnede analyser:

```javascript
const DASHBOARD_PRESETS = {
    'hr-oversikt': {
        label: 'HR-oversikt',
        description: 'Oversikt over organisasjonen',
        pins: [
            { metric: 'count', group_by: 'arbeidsland', chart_type: 'bar', title: 'Ansatte per land' },
            { metric: 'count', group_by: 'kjonn', chart_type: 'pie', title: 'Kjønnsfordeling' },
            { metric: 'count', group_by: 'aldersgruppe', chart_type: 'bar', title: 'Aldersfordeling' },
        ]
    },
    'ledelse': {
        label: 'Ledelse',
        description: 'Nøkkeltall for ledelsen',
        pins: [
            { metric: 'count', group_by: 'arbeidsland', chart_type: 'bar', title: 'Ansatte per land' },
            { metric: 'sum_salary', group_by: 'arbeidsland', chart_type: 'bar', title: 'Lønnsmasse per land' },
            { metric: 'count', group_by: 'avdeling', split_by: 'kjonn', chart_type: 'stacked', title: 'Avdelinger fordelt på kjønn' },
        ]
    },
    'lonn-analyse': {
        label: 'Lønnsanalyse',
        description: 'Lønnsoversikt på tvers',
        pins: [
            { metric: 'avg_salary', group_by: 'avdeling', chart_type: 'bar', title: 'Snittlønn per avdeling' },
            { metric: 'avg_salary', group_by: 'arbeidsland', chart_type: 'bar', title: 'Snittlønn per land' },
            { metric: 'avg_salary', group_by: 'kjonn', chart_type: 'bar', title: 'Snittlønn per kjønn' },
        ]
    },
};
```

UI: En velger øverst i Oversikt-fanen (under KPI-kortene):

```html
<div class="dashboard-preset-bar">
    <span class="preset-label">Dashboard-mal:</span>
    <select id="dashboard-preset">
        <option value="">Mine grafer</option>
        <option value="hr-oversikt">HR-oversikt</option>
        <option value="ledelse">Ledelse</option>
        <option value="lonn-analyse">Lønnsanalyse</option>
    </select>
</div>
```

Logikk:
- "Mine grafer" = vis brukerens egne pinned charts fra localStorage
- Velge en mal = vis malens grafer (uten å slette brukerens egne)
- Brukerens pinned charts lagres alltid separat

### A.5 Grid-layout for festede grafer

Festede grafer vises i et responsivt grid (2 kolonner på desktop, 1 på mobil) — bruker eksisterende `.grid-2` klasse.

## B. Enklere analyse-velger

### B.1 Progressiv avsløring

Nåværende layout: 2 rader med 5 dropdowns + knapp, alle synlige.

Ny layout:
```
┌──────────────────────────────────────────────────────┐
│  HVA VIL DU MÅLE?              HVORDAN DELE OPP?     │
│  [Antall ansatte ▼]            [Land ▼]              │
│                                                       │
│  [Vis analyse]                                        │
│                                                       │
│  ▶ Flere valg (inndeling, filter)                     │
│  ┌──────────────────────────────────────────────────┐ │
│  │ EKSTRA INNDELING           FILTER                │ │
│  │ [Ingen ▼]                  [Ingen filter ▼] [▼]  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  ▶ Maler                                              │
│  ┌──────────────────────────────────────────────────┐ │
│  │ [Velg mal... ▼]  [Last inn] [Lagre] [Slett]      │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

Implementering med `<details>` / `<summary>`:
- Hoveddelen (Metrikk + Gruppering + Vis analyse) er alltid synlig
- "Flere valg" er en `<details>` som skjuler Inndeling + Filter
- "Maler" er en `<details>` som skjuler mal-seksjonen
- Labels endres til mer beskrivende tekst: "Hva vil du måle?" og "Hvordan dele opp?"
- `<details>` åpnes automatisk hvis en mal med inndeling/filter lastes inn

### B.2 Sammenslått filter

Filter-dimensjon og filter-verdi forblir to dropdowns, men plasseres tettere (inline på samme linje) med en visuell kobling. Label endres fra "Filter" + "Filterverdi" til bare "Filtrer på:" med de to dropdowns inline.

### B.3 Bedre labels

| Nåværende       | Ny                          |
|----------------|-----------------------------|
| Metrikk        | Hva vil du måle?            |
| Gruppering     | Hvordan dele opp?           |
| Inndeling (valgfri) | Ekstra inndeling       |
| Filter         | Filtrer på                  |
| Filterverdi    | (ingen label, inline etter dim) |

## C. "Alle" som grupperingsvalg

### C.1 Backend-endring (analyzer.py)

Legg til spesialdimensjon `alle` i håndteringen (IKKE i DIMENSIONS — håndteres som spesialtilfelle):

```python
def build_analysis_query(metric, group_by, ...):
    if group_by == "alle":
        # Ingen GROUP BY, bare aggregering
        agg_func = METRICS[metric][0]
        where_clause = ...  # Bygg WHERE som vanlig
        sql = f"SELECT {agg_func} AS verdi FROM ansatte {where_clause}"
        return sql, tuple(params)
    # ... eksisterende logikk
```

`run_analysis()` endres til å returnere:
```json
{
    "meta": { "metric": "count", "group_by": "alle", ... },
    "data": { "Alle": 342 }
}
```

`/api/analyze/options` endres til å inkludere "Alle" i dimensions-listen:
```python
dimensions = [{"id": "alle", "label": "Alle (total)"}] + [...]
```

### C.2 Frontend-endring

Når `group_by === 'alle'` og data har kun 1 nøkkel:
- Vis et KPI-kort i stedet for graf
- Skjul graftype-pills
- Skjul split_by (gir ikke mening uten gruppering)

```javascript
if (groupBy === 'alle') {
    // Vis som KPI-kort
    const value = Object.values(data)[0];
    const resultEl = document.getElementById('analyse-result');
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `
        <div class="cards">
            ${card(result.meta.metric_label, formatNumber(value))}
        </div>
    `;
    // Skjul graftype-pills
    document.getElementById('analyse-chart-types').classList.add('hidden');
    return;
}
```

## D. Farge-fix for bar/horizontalBar

### D.1 Rotårsak

I `charts.js` linje 244 og 277:
```javascript
backgroundColor: options.colors || COLORS.primary,
```

`options.colors` mottar enten en enkelt farge-streng (f.eks. `COLORS.secondary`) eller en array av farger. Når en enkelt streng sendes, bruker Chart.js den på alle barer.

### D.2 Løsning

Endre `renderBarChart` og `renderHorizontalBarChart` til å bruke PALETTE-farger per bar som default ved enkeltserie:

```javascript
function renderBarChart(canvasId, labels, data, options = {}) {
    // ...
    const colors = options.colors
        ? (Array.isArray(options.colors) ? options.colors : options.colors)
        : labels.map((_, i) => PALETTE[i % PALETTE.length]);
    // ...
    datasets: [{ data, backgroundColor: colors, borderRadius: 4 }],
}
```

Merk: Behold muligheten for callere å sende inn en enkelt farge (f.eks. `COLORS.negative` for churn-grafer) — da brukes den fargen på alle barer. Default (ingen `options.colors`) gir PALETTE-farger.

### D.3 Påvirkning

- Analyse-fanen: `renderBarChart(canvasId, labels, values)` kalles uten `options.colors` → får nå PALETTE-farger per bar ✓
- Analyse-fanen: `renderHorizontalBarChart(canvasId, labels, values, { colors: COLORS.secondary })` → får fortsatt enhetsfarge (som ønsket for enkel blå)
  - MEN: dette er nettopp buggen! Når vi filtrerer på Kjønn og har 1 bar, bør den ha sin egen farge.
  - Løsning: Endre `renderAnalyseChart()` til å IKKE sende `colors`-option for 1-dim data, slik at default PALETTE brukes.
- Churn-grafer: sender eksplisitt `{ colors: COLORS.negative }` → beholder enhetsfarge ✓
- Oversikt/Tenure: bruker eksplisitt farger → uendret ✓

## E. Småfikser

### E.1 Duplikat Analyse-tab

`index.html` linje 26 og 30 har begge `<button class="tab" data-tab="analyse">Analyse</button>`.

Fix: Fjern linje 30. Tab-rekkefølgen blir: Oversikt, Analyse, Churn, Tenure, Lønn, Søk, Import.

## Filendringer

```
web/templates/index.html     ENDRET  — fjern duplikat tab, omstrukturere analyse-seksjon
                                        med <details>, dashboard-preset-velger i oversikt,
                                        pin-knapp i analyse-resultat
web/static/js/app.js         ENDRET  — pinned charts logikk, dashboard presets,
                                        "Alle"-håndtering, loadOversikt() utvidet
web/static/js/charts.js      ENDRET  — PALETTE som default for bar/horizontalBar
web/static/css/style.css     ENDRET  — styling for <details>, preset-bar, pin-knapp,
                                        unpin-knapp, pinned chart grid
hr/analyzer.py               ENDRET  — "alle" som spesialdimensjon i build_analysis_query
                                        og run_analysis
web/routes/analyze.py        ENDRET  — inkluder "Alle (total)" i options-respons
tests/test_api.py            ENDRET  — test for /api/analyze?metric=count&group_by=alle
tests/test_analyzer.py       ENDRET  — test for build_analysis_query med group_by="alle"
```
