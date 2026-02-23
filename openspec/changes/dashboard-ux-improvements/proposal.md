# Proposal: Dashboard UX Improvements

## Problem

Dashboardet fungerer teknisk, men har flere UX-svakheter som gjør det vanskeligere å bruke enn nødvendig:

### 1. Oversikt-fanen er statisk og begrenset
Etter at vi fjernet redundante faner (Alder, Geografi, Kjønn, Jobbfamilier) har Oversikt kun 6 KPI-kort og 2 faste grafer (ansettelsestyper + heltid/deltid). Brukeren kan ikke:
- Velge hvilke grafer som vises
- Legge til nye grafer fra analysemotoren
- Tilpasse dashboardet til sin rolle (HR-sjef vs. landsjef vs. ledelse)

### 2. Analyse-velgeren er kompleks
5 synlige dropdowns + 3 mal-knapper + graftype-pills skaper kognitiv overbelastning. For en førstegangsbruker er det uklart hva som er obligatorisk og hva som er valgfritt. Filter-dimensjon og filter-verdi er to separate dropdowns som kunne vært forenklet.

### 3. "Alle" mangler som grupperingsvalg
Velger man f.eks. metrikk "Antall ansatte" og gruppering "Kjønn", får man bare oppdeling per kjønn. Det finnes ingen måte å si "vis totalen uten gruppering" — altså bare ett tall. Dette er nyttig som baseline-sammenligning.

### 4. Farge-bug ved filter + horisontal bar
Når man filtrerer på Kjønn (f.eks. kun "Mann") og velger horisontal bar, vises alle barer i samme farge. Årsak: `renderHorizontalBarChart()` bruker `options.color || COLORS.primary` som en enkelt farge — den har ikke per-bar fargelogikk slik pie/doughnut har.

### 5. Mindre UX-problemer oppdaget i koden
- **Duplisert Analyse-tab i HTML** — `index.html` har to `<button>` for Analyse-tab (linje 26 og 30)
- **Ingen dataetiketter på grafer** — vanskelig å lese nøyaktige verdier uten å hovere
- **Template-systemet er usynlig for nye brukere** — gjemt i en liten seksjon uten forklaring

## Solution

### A. Oversikt-fanen: Konfigurerbart dashboard

Gjør Oversikt til et konfigurerbart dashboard der brukeren kan:

1. **Pinne analyser til dashboardet** — Fra Analyse-fanen kan brukeren klikke "Fest til Oversikt" på en analyse. Denne legges til som en graf på Oversikt-fanen.
2. **Standard-oppsett** — Oversikt beholder eksisterende KPI-kort + 2 grafer som default, men brukeren kan fjerne og legge til.
3. **Dashboard-konfigurasjon lagret i localStorage** — Hvilke grafer som vises, rekkefølge, og graftype.

**Merk:** Per-brukerrolle-dashboard (ulike oppsett for HR-sjef, landsjef, etc.) legges til som forhåndsdefinerte mal-oppsett som brukeren kan velge mellom. Ikke dynamisk rollestyring — dette er et enkeltbrukerverktøy uten autentisering.

### B. Enklere analyse-velger

Forenkle UI-en uten å fjerne funksjonalitet:

1. **Progressiv avsløring** — Vis kun Metrikk og Gruppering som obligatoriske. "Inndeling" og "Filter" vises som valgfri accordion/expanderbart felt.
2. **Sammenslått filter** — Slå sammen filter-dimensjon + filter-verdi til en kompakt inline-velger: `[Land ▼] [Norge ▼]` på én rad i stedet for to fulle dropdowns.
3. **Klarere visuelt hierarki** — Obligatoriske felter (Metrikk, Gruppering) er fremtredende. Valgfrie felter (Inndeling, Filter, Maler) er sekundære.
4. **Bedre onboarding** — Placeholder-tekst og subtitler som forklarer hvert felt ("Hva vil du måle?", "Hvordan vil du dele opp?").

### C. "Alle" som grupperingsvalg

Legg til en spesialverdi `alle` i DIMENSIONS (eller håndter i frontend/API). Effekt:
- Ingen GROUP BY → returnerer én enkelt verdi
- Nyttig for "Vis total lønnsmasse" eller "Antall aktive ansatte" uten oppdeling
- Graftype for "Alle": stort KPI-kort i stedet for graf

### D. Fiks farge-bug

Endre `renderBarChart()` og `renderHorizontalBarChart()` til å bruke PALETTE-farger per bar (som pie/doughnut gjør) når det er én dataserie. Behold enhetsfarge kun ved multi-serie (stacked/grouped).

### E. Småfikser
- Fjern duplikat Analyse-tab-knapp i HTML
- Vurder dataetiketter (Chart.js datalabels-plugin) — kan være opt-in for å unngå rot

## Scope

### In scope
- Oversikt-fanen: "Fest til oversikt"-funksjonalitet fra Analyse
- Oversikt-fanen: Fjern/reorder festede grafer
- Oversikt-fanen: Forhåndsdefinerte dashboard-maler (2–3 stk)
- Analyse-velger: Progressiv avsløring av valgfrie felter
- Analyse-velger: Sammenslått filter-velger
- Analyse-velger: Bedre labels/placeholder-tekst
- "Alle" som grupperingsvalg i backend + frontend
- Farge-fix for bar/horizontalBar med én serie
- Fjern duplikat tab-knapp i HTML

### Out of scope
- Server-side lagring av dashboard-konfigurasjon
- Brukerautentisering / rollestyring
- Drag-and-drop reordering av grafer
- Chart.js datalabels-plugin (vurderes separat)
- Eksport av analyseresultater til Excel/CSV
- Flere graftyper (scatter, heatmap, etc.)

## Success Criteria
- Brukeren kan feste en analyse fra Analyse-tab til Oversikt
- Brukeren kan fjerne festede grafer fra Oversikt
- Brukeren kan velge mellom 2–3 forhåndsdefinerte dashboard-oppsett
- Analyse-velgeren viser kun obligatoriske felter by default, med valgfrie felter expander-bare
- "Alle" fungerer som gruppering og viser et KPI-kort
- Bar/horisontal bar viser ulike farger per bar ved enkeltserie
- Duplikat Analyse-tab er fjernet
- Alle eksisterende tester passerer + nye tester for "Alle"-gruppering
