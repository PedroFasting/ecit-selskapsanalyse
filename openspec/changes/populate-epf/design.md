# Design: Populate EPF

## Approach

Artefaktene fylles ut i EPFs naturlige rekkefølge der hvert lag bygger på det forrige. Innholdet utledes fra den eksisterende kodebasen — vi dokumenterer hva produktet *er*, ikke hva det *burde være*.

Hvert steg er designet for å kunne gjøres i én økt (15-30 min) med AI-assistanse. Agenten analyserer kodebasen og foreslår innhold, brukeren reviewer og justerer.

## EPF Instance

```
docs/EPF/_instances/ecit-selskapsanalyse/
├── _epf.yaml                    # Anchor
├── _meta.yaml                   # Produkt-metadata
├── READY/
│   ├── 00_north_star.yaml       # Steg 1
│   ├── 01_insight_analyses.yaml # Steg 2
│   ├── 02_strategy_foundations.yaml # Steg 3
│   ├── 03_insight_opportunity.yaml  # Steg 4
│   ├── 04_strategy_formula.yaml     # Steg 5
│   └── 05_roadmap_recipe.yaml       # Steg 6
├── FIRE/
│   ├── value_models/
│   │   ├── product.value_model.yaml   # Steg 7
│   │   ├── strategy.value_model.yaml  # Steg 9 (aktivere sub-components)
│   │   ├── org_ops.value_model.yaml   # Steg 9
│   │   └── commercial.value_model.yaml # Steg 9
│   └── feature_definitions/
│       ├── fd-001_konsern-analyse.yaml  # Steg 8
│       └── fd-002_hr-analyse.yaml       # Steg 8
└── AIM/                         # Out of scope (tom)
```

## Utfyllingsstrategi per artefakt

### Steg 1: North Star
**Kilde:** Produktets formål utledet fra kodebasen og ECIT-kontekst.
**Nøkkelbeslutninger:**
- Purpose: Gi ECIT-analytikere rask innsikt i konsernstruktur og arbeidsstyrke
- Vision: Internt, men scope for å bli self-service
- Mission: To analyse-moduler (konsern + HR) som CLI-verktøy
- Values: Utledes fra kode-kvalitet og beslutninger i kodebasen

### Steg 2-4: Insight & Opportunity
**Kilde:** ECIT som nordisk regnskaps-/IT-konsern, behov for internanalyse.
**Nøkkelbeslutninger:**
- Trendfokus: Konserndataanalyse, HR-analytics, compliance
- Markedsposisjon: Internt verktøy (ikke kommersielt)
- Opportunity: Sentralisert analyse-plattform for ECIT

### Steg 5: Strategy Formula
**Kilde:** Posisjonering som internt verktøy, forretningsmodell som cost-center.
**Nøkkelbeslutninger:**
- Intern tool = ingen revenue model, men cost-savings
- Competitive moat: Intern domenekunnskap + data-tilgang

### Steg 6: Roadmap Recipe
**Kilde:** Eksisterende openspec/restructure-repo + feature-gaps.
**Nøkkelbeslutninger:**
- Syklus 1: Repo-restrukturering + grunnleggende forbedringer
- OKRs: Kode-kvalitet, brukeropplevelse, utvidet analyse

### Steg 7: Product Value Model
**Kilde:** Direkte mapping fra kodebasens moduler og funksjoner.
**Nøkkelbeslutninger:**
- Layer 1: Konsern-analyse (eierskap, struktur, investering)
- Layer 2: HR-analyse (demografi, turnover, lønn, jobbfamilier)
- Layer 3: Felles infrastruktur (database, import, CLI)

### Steg 8: Feature Definitions
**Kilde:** Mapping av eksisterende funksjonalitet i koden.
**Nøkkelbeslutninger:**
- fd-001: Konsern-modulen (søk, eierkjeder, statistikk)
- fd-002: HR-modulen (demografi, turnover, lønn, jobbfamilier)

### Steg 9: Kanoniske tracks
**Kilde:** Hvilke Strategy/OrgOps/Commercial sub-components er relevante.
**Nøkkelbeslutninger:**
- Minimal aktivering — bare det som er relevant for et internt verktøy
- OrgOps: Development processes er mest relevant
- Strategy/Commercial: Begrenset for intern tool

## Risiko

| Risiko | Tiltak |
|--------|--------|
| Feil antakelser om produktets retning | Brukeren reviewer hvert steg før vi går videre |
| Schema-validering feiler | Kjør `epf validate` etter hvert steg |
| For mye innhold vs. for lite | Start med "good enough" — kan itereres |
| Artefakter divergerer fra kodebase | Utled alt fra eksisterende kode der mulig |
