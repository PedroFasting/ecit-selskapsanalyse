# Tasks: Utvide analysatorens metrikker og dimensjoner

## Task 1: Backend — Nye metrikker og dimensjoner i analyzer.py
- [ ] Legg til 4 nye metrikker i METRICS dict
- [ ] Legg til 4 nye dimensjoner i DIMENSIONS dict  
- [ ] Legg til TENURE_CASE_EXPR for tenure_gruppe (beregnet dimensjon)
- [ ] Oppdater _resolve_dimension() for tenure_gruppe
- [ ] Oppdater build_analysis_query() med WHERE-krav for nye metrikker
- [ ] Oppdater _round_value() for prosentmetrikker
- [ ] Oppdater FILTERS (nye kolonner som er filtrerbare)

## Task 2: Backend — Oppdater API-ruter
- [ ] Oppdater /api/analyze description med nye valg
- [ ] Legg til nye filter_* query-params i analyze()
- [ ] Oppdater analyze_options() (nye dimensjoner i riktig rekkefølge)

## Task 3: Frontend — Oppdater dashboard-presets
- [ ] Legg til "Mangfold"-preset
- [ ] Oppdater eksisterende presets med nye metrikker der relevant
- [ ] Cache-bust versjon

## Task 4: Tester
- [ ] Nye tester for metrikker: avg_tenure, avg_work_hours, pct_female, pct_leaders
- [ ] Nye tester for dimensjoner: tenure_gruppe, ansettelsesniva, nasjonalitet, arbeidssted
- [ ] Oppdater conftest.py om testdata trenger utvidelse (sjekk at kolonner finnes)
- [ ] API-tester for nye metrikker/dimensjoner

## Task 5: Verifisering
- [ ] Kjør alle tester
- [ ] Docker build + manuell verifisering
