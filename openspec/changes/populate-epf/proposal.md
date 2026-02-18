# Proposal: Populate EPF

## Problem

EPF-instansen for ecit-selskapsanalyse er initialisert med template-filer, men alle artefaktene inneholder kun placeholder-verdier. Uten utfylte artefakter gir EPF ingen verdi — det blir bare tomme YAML-filer.

Produktet har ingen dokumentert strategi, ingen definerte personas, ingen feature-definisjoner, og ingen value model. All produktkunnskap lever implisitt i koden og i hodet til utviklerne.

## Solution

Gradvis fylle ut EPF-artefaktene i riktig rekkefølge (READY → FIRE → AIM), basert på analyse av eksisterende kodebase og produktkontekst. Hver artefakt fylles ut som en selvstendig oppgave som kan gjøres i én økt.

Rekkefølgen følger EPFs naturlige flyt:
1. **North Star** — visjon, misjon, formål (fundamentet alt bygger på)
2. **Insight Analyses** — trender, marked, brukerbehov
3. **Strategy Foundations** — strategiske pilarer
4. **Strategy Formula** — posisjonering og forretningsmodell
5. **Product Value Model** — verdistruktur for produktet
6. **Roadmap Recipe** — OKRs og milepæler
7. **Feature Definitions** — konkrete feature-spesifikasjoner
8. **Canonical Track Value Models** — Strategy, OrgOps, Commercial

## Scope

### In scope
- Fylle ut alle READY-fase artefakter (North Star, Insight Analyses, Strategy Foundations, Insight Opportunity, Strategy Formula, Roadmap Recipe)
- Bygge Product Value Model fra scratch basert på kodebasen
- Definere feature definitions for Konsern-modul og HR-modul
- Aktivere relevante sub-components i de kanoniske track value models
- Kjøre health check og fikse valideringsfeil

### Out of scope
- AIM-fase artefakter (assessment reports, calibration memos) — krever en aktiv syklus
- Output-generering (investor memos, context sheets etc.)
- Mappings-artefakten (krever features + value model ferdig først)
- LRA (Living Reality Assessment) bootstrap

## Success Criteria
- `epf health` returnerer ingen kritiske feil
- Alle READY-artefakter validerer mot schema
- Product Value Model dekker begge modulene (Konsern + HR)
- Minst 2 feature definitions er opprettet
- Roadmap har minst én syklus med OKRs
