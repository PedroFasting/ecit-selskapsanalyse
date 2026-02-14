# Proposal: Restructure Repository

## Problem

Repoet `ecit-selskapsanalyse` inneholder to uavhengige prosjekter (konsernstruktur-analyse og HR-analyse) i en flat mappestruktur under `konsern-database/`. Dette skaper flere problemer:

- **Ingen separasjon mellom data og kode** - SQLite-databaser, Excel-filer og Excel lock-filer ligger blandet med Python-kildekode
- **Ingen `.gitignore`** - Binærfiler (.db), midlertidige filer (~$*.xlsx), og __pycache__ trackes i git
- **Ingen deklarerte avhengigheter** - Prosjektet bruker pandas, openpyxl og numpy uten requirements.txt
- **Inkonsistent arkitektur** - HR-modulen (`hr_database/`) er ryddig med database/importer/analytics-separasjon, mens konsern-koden er løse scripts
- **Hardkodede stier** - test_database.py har absolutte stier som bare fungerer på én maskin
- **Tom README** - Ingen dokumentasjon av hva prosjektet er eller hvordan det brukes
- **Tomme mapper** - `static/` og `templates/` tjener ingen funksjon

## Solution

Restrukturere repoet med klar separasjon mellom de to prosjektene, flytte data ut av kildekoden, og legge til grunnleggende prosjektinfrastruktur (.gitignore, requirements.txt, README).

Konsern-modulen refaktoreres til samme mønster som HR-modulen (database/importer/analytics), slik at begge prosjektene har konsistent arkitektur.

## Scope

### In scope
- Opprett .gitignore med fornuftige mønstre
- Opprett requirements.txt med deklarerte avhengigheter
- Oppdater README.md med prosjektbeskrivelse
- Flytt HR-kode til `hr/` (toppnivå)
- Refaktorer konsern-kode til `konsern/` med modulstruktur
- Flytt CLI-verktøy til riktige moduler
- Separer data-filer til `data/`
- Flytt engangsscripts til `scripts/`
- Fjern tomme/unødvendige mapper

### Out of scope
- Webapp-implementasjon for HR
- Kobling mellom konsern- og HR-databaser
- CI/CD-oppsett
- Test-rammeverk (pytest) - kan komme senere
- Splitting til separate repoer

## Success Criteria
- Repoet har en klar, forståelig struktur
- Begge modulene har konsistent arkitektur
- Data er separert fra kode
- Nye utviklere kan forstå og komme i gang via README
- Ingen binærfiler eller midlertidige filer i git
