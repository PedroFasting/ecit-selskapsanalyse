# Proposal: Custom Analysis Builder

## Problem

Dashboardet viser i dag kun ferdiglagde grafer med faste dimensjoner (f.eks. "Lønn per avdeling", "Kjønn per land"). Brukeren kan ikke selv kombinere dimensjoner og metrikker for å bygge tilpassede analyser.

Konkrete svakheter:

1. **Ingen fleksibilitet** -- Hver graf har en hardkodet SQL-spørring bak seg. Vil brukeren se "Lønn per avdeling fordelt på kjønn", må det bygges en ny metode i `analytics.py`, et nytt API-endepunkt, og ny frontend-kode.

2. **Mange metoder som gjør nesten det samme** -- `salary_by_department()`, `salary_by_country()`, `salary_by_gender()`, `salary_by_age()`, `salary_by_job_family()` er alle varianter av "aggreger lønn gruppert på X". Tilsvarende for `employees_by_country()`, `employees_by_company()`, `employees_by_department()`. Dette er et mønster som skriker etter generalisering.

3. **Kombinasjonsanalyser er vanskelige** -- Vil du se "Gjennomsnittlig lønn per avdeling, kun for kvinner i Norge"? Det krever enten en ny metode eller at brukeren eksporterer til Excel og gjør det selv.

4. **Ingen mulighet for å lagre innsikter** -- Når en bruker finner en nyttig kombinasjon, finnes det ingen måte å lagre den som favoritt eller template for gjenbruk.

## Solution

Bygge en "Analyse-bygger" som en ny tab i dashboardet. Brukeren velger:

1. **Metrikk** (hva skal måles): Antall ansatte, gjennomsnittslønn, min/maks lønn, total lønnsmasse
2. **Gruppering** (dimensjon 1): Avdeling, selskap, land, kjønn, aldersgruppe, jobbfamilie, ansettelsetype
3. **Valgfri inndeling** (dimensjon 2): Samme valg som gruppering -- gir stacked/grouped charts
4. **Valgfritt filter**: Begrens til spesifikt land, selskap, avdeling, kjønn, etc.

### Eksempler på hva brukeren kan lage:
- Antall ansatte per avdeling, fordelt på kjønn (stacked bar)
- Gjennomsnittslønn per land, fordelt på aldersgruppe (grouped bar)
- Antall ansatte per jobbfamilie, filtrert på Norge (bar)
- Gjennomsnittslønn per kjønn, filtrert på en avdeling (bar)

### Teknisk tilnærming

**Backend: Ett generisk endepunkt**

I stedet for 20+ spesifikke metoder, ett endepunkt:
```
GET /api/analyze?metric=avg_salary&group_by=avdeling&split_by=kjonn&filter_land=Norge
```

Bygger dynamisk SQL med `GROUP BY`, `WHERE`, og aggregeringsfunksjoner. Kun forhåndsgodkjente kolonnenavn tillates (SQL injection-sikring via whitelist).

**Frontend: Velger-UI + dynamisk graf**

- Dropdowns for metrikk, gruppering, inndeling, filter
- **Smart graftype-valg**: Systemet velger automatisk beste graftype basert på kombinasjonen (f.eks. 1 dimensjon → bar, 2 dimensjoner → stacked bar, få kategorier → pie). Brukeren kan overstyre med en dropdown som kun viser graftyper som gir mening for den aktuelle dataen.
- "Oppdater"-knapp som henter data og tegner graf
- Mulighet for å lagre kombinasjoner som templates (localStorage i første omgang)

## Scope

### In scope
- Generisk analyse-endepunkt i backend med dynamisk SQL-bygging
- Whitelist av tillatte kolonner og aggregeringsfunksjoner (sikkerhet)
- Ny "Analyse"-tab med velger-UI
- Smart graftype-valg med automatisk default + manuell overstyring (filtrert til relevante typer)
- Valgfritt filter (én dimensjon)
- Lagring av templates i localStorage
- Lasting/sletting av lagrede templates

### Out of scope
- Server-side template-lagring (database)
- Deling av templates mellom brukere
- Eksport av analyseresultater til Excel/CSV
- Pivot-tabell-visning (kun grafer)
- Mer enn 2 grupperingsdimensjoner
- Fritekst SQL (vi bygger sikker SQL fra forhåndsgodkjente valg)
- Avanserte graftyper (scatter, heatmap, box plot)

## Success Criteria
- Brukeren kan bygge en analyse med 1 metrikk + 1 gruppering og se en graf
- Brukeren kan legge til en ekstra inndeling (dimensjon 2) og se stacked/grouped chart
- Brukeren kan filtrere på én dimensjon (f.eks. kun Norge)
- Brukeren kan bytte graftype fra en filtrert liste (kun typer som gir mening)
- Brukeren kan lagre en kombinasjon som template og laste den inn igjen
- Alle eksisterende tester fortsetter å passere
- Nye tester dekker det generiske analyse-endepunktet
- SQL injection er umulig (whitelist-basert)
