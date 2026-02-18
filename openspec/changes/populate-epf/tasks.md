# Tasks: Populate EPF

## Task 1: Fyll ut North Star
**Status:** pending
**Avhengighet:** Ingen (første artefakt)

Fyll ut `READY/00_north_star.yaml` med produktets grunnlag.

### 1.1 Purpose
- Statement: ECIT Selskapsanalyse gir analytikere umiddelbar innsikt i konsernets eierskapsstruktur og arbeidsstyrke
- Problem we solve: Manuell navigering i komplekse Excel-ark og spredte HR-systemer for å forstå konsernstruktur
- Who we serve: ECIT Groups interne analytikere og ledelse
- Impact: Datadrevet beslutningsgrunnlag for M&A, HR og strategi

### 1.2 Vision
- Én samlet analyseplattform for ECIT-konsernets struktur- og personaldata
- Timeframe: 2-3 år (internt verktøy)
- Success looks like: Analytikere bruker verktøyet daglig i stedet for Excel

### 1.3 Mission
- Bygge CLI-baserte analyseverktøy for konsernstruktur og HR-data
- To moduler: Konsern (eierskap) og HR (arbeidsstyrke)
- Importerer fra Excel, lagrer i SQLite, tilbyr interaktiv analyse

### 1.4 Values og Core Beliefs
- Utled fra kodebasens karakteristikker (norsk språk, praktisk, direkte)
- Hold enkelt — 2-3 verdier

### 1.5 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/00_north_star.yaml
```

---

## Task 2: Fyll ut Insight Analyses
**Status:** pending
**Avhengighet:** Task 1

Fyll ut `READY/01_insight_analyses.yaml` med kontekstanalyse.

### 2.1 Trendanalyse
- Nordiske konglomerater og behov for intern dataanalyse
- HR-analytics som voksende felt
- Regulatory compliance for konsernrapportering

### 2.2 Markedsanalyse
- ECIT som nordisk regnskaps-/IT-konsern med 50+ datterselskaper
- Kompleks eierskapsstruktur (TOPCO → MIDCO → BIDCO → XX → divisjoner)
- Multi-land tilstedeværelse (Norge, Sverige, Danmark, etc.)

### 2.3 Brukeranalyse
- Corporate finance-team: Trenger eierskapsanalyse for M&A og rapportering
- HR-team: Trenger workforce analytics for strategisk personalplanlegging
- Ledelse: Trenger overordnet innsikt

### 2.4 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/01_insight_analyses.yaml
```

---

## Task 3: Fyll ut Strategy Foundations
**Status:** pending
**Avhengighet:** Task 1, Task 2

Fyll ut `READY/02_strategy_foundations.yaml` med strategiske pilarer.

### 3.1 Strategiske pilarer
- **Intern effektivitet:** Erstatte manuelt Excel-arbeid med strukturert analyse
- **Data-sentralisering:** Samle konsern- og HR-data i querybare databaser
- **Inkrementell utbygging:** Bygge modul for modul, starte med det som gir mest verdi

### 3.2 Strategiske prinsipper
- CLI-first: Rask, scriptbar, ingen overhead
- Excel-inn, innsikt-ut: Bruk eksisterende datakilder
- Norsk-first: Brukere er norskspråklige

### 3.3 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/02_strategy_foundations.yaml
```

---

## Task 4: Fyll ut Insight Opportunity
**Status:** pending
**Avhengighet:** Task 2

Fyll ut `READY/03_insight_opportunity.yaml` med mulighetsrom.

### 4.1 Opportunity
- Identifisert behov for sentralisert konsern- og HR-analyse
- Ingen eksisterende verktøy dekker begge behovene
- Data er allerede tilgjengelig i Excel-format

### 4.2 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/03_insight_opportunity.yaml
```

---

## Task 5: Fyll ut Strategy Formula
**Status:** pending
**Avhengighet:** Task 3, Task 4

Fyll ut `READY/04_strategy_formula.yaml` med posisjonering.

### 5.1 Posisjonering
- Internt analyseverktøy — ikke et kommersielt produkt
- Unique value: Direkte tilgang til ECIT-spesifikke datastrukturer
- Target: ECIT-analytikere som jobber med konsern- eller HR-data

### 5.2 Value Creation
- Import Excel → SQLite → interaktiv CLI-analyse
- Key capabilities: Eierskapsnavigering, HR-analytics, formatert output

### 5.3 Business Model
- Cost-center: Ingen direkte inntekt, men tidsbesparelse
- Verdi måles i tid spart og bedre beslutninger

### 5.4 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/04_strategy_formula.yaml
```

---

## Task 6: Fyll ut Roadmap Recipe
**Status:** pending
**Avhengighet:** Task 5

Fyll ut `READY/05_roadmap_recipe.yaml` med OKRs.

### 6.1 Syklus 1: Fundament (Q1 2026)
- **OKR 1:** Kodebase er strukturert og vedlikeholdbar
  - KR: Repo restrukturert (jf. openspec/restructure-repo)
  - KR: .gitignore, requirements.txt, README på plass
- **OKR 2:** Konsern-analyse er pålitelig og komplett
  - KR: Konsern-modul refaktorert til pakke-struktur
  - KR: Alle søk/analyse-funksjoner fungerer etter restrukturering
- **OKR 3:** HR-analyse dekker kjernebehov
  - KR: HR-modul fungerer som selvstendig pakke
  - KR: Alle analytics-funksjoner validert

### 6.2 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/READY/05_roadmap_recipe.yaml
```

---

## Task 7: Bygg Product Value Model
**Status:** pending
**Avhengighet:** Task 1, Task 5

Fyll ut `FIRE/value_models/product.value_model.yaml` fra scratch.

### 7.1 Layer 1: Konsernstruktur-analyse
Utled fra `sok.py` (641 linjer) og `import_data.py`:
- **Component: Eierskapsnavigering** — søk, eierkjeder, datterselskaper, konserntre
- **Component: Investeringsanalyse** — beløp, statistikk, sammenligning
- **Component: Dataimport** — Excel-matrise til SQLite

### 7.2 Layer 2: HR-analyse
Utled fra `hr_database/analytics.py` (926 linjer) og `hr_cli.py`:
- **Component: Arbeidsstyrke-oversikt** — headcount, demografi, geografi
- **Component: Turnover-analyse** — churn, tenure, oppsigelsesårsaker
- **Component: Lønnsanalyse** — per avdeling, land, kjønn, jobbfamilie
- **Component: Dataimport** — VerismoHR Excel til SQLite

### 7.3 Layer 3: Felles infrastruktur
- **Component: Database-håndtering** — SQLite, schema, connection
- **Component: CLI-grensesnitt** — interaktiv REPL, menynavigering

### 7.4 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/FIRE/value_models/product.value_model.yaml
```

---

## Task 8: Opprett Feature Definitions
**Status:** pending
**Avhengighet:** Task 7

Opprett feature-filer i `FIRE/feature_definitions/`.

### 8.1 fd-001: Konsern Eierskapsanalyse
- Personas: Corporate Finance Analyst
- Capabilities: Søk, eierkjeder, konserntre, investering, sammenligning
- contributes_to: Product.KonsernAnalyse.*

### 8.2 fd-002: HR Workforce Analytics
- Personas: HR Analyst
- Capabilities: Demografi, turnover, lønn, jobbfamilier, geografi
- contributes_to: Product.HRAnalyse.*

### 8.3 Validering
```bash
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/FIRE/feature_definitions/fd-001_konsern-analyse.yaml
epf-cli validate docs/EPF/_instances/ecit-selskapsanalyse/FIRE/feature_definitions/fd-002_hr-analyse.yaml
```

---

## Task 9: Aktiver kanoniske track value models
**Status:** pending
**Avhengighet:** Task 7

Aktiver relevante sub-components i Strategy, OrgOps og Commercial tracks.

### 9.1 OrgOps (mest relevant)
- Aktiver: Development processes, code quality, tooling
- La resten stå som `active: false`

### 9.2 Strategy
- Aktiver: Intern posisjonering, brukerforståelse
- Minimal — internt verktøy trenger lite strategisk overhead

### 9.3 Commercial
- Minimal aktivering — ingen kommersiell distribusjon
- Eventuelt: Intern stakeholder management

### 9.4 Validering
```bash
epf-cli health docs/EPF/_instances/ecit-selskapsanalyse/
```

---

## Task 10: Kjør full health check og fiks feil
**Status:** pending
**Avhengighet:** Alle foregående tasks

### 10.1 Health check
```bash
epf-cli health docs/EPF/_instances/ecit-selskapsanalyse/
```

### 10.2 Fiks valideringsfeil
Iterer til health check er grønn.

### 10.3 Valider relasjoner
```bash
# Sjekk at feature contributes_to paths matcher value model
# Sjekk at roadmap KR targets er gyldige
```
