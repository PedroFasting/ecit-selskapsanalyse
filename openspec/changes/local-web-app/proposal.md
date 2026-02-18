# Proposal: Local Web App

## Problem

HR-analyseverktøyet er i dag et Python CLI-program som krever at brukeren navigerer en 13-punkts tekstmeny, skriver stier til Excel-filer manuelt, og leser resultater som ASCII-tabeller i terminalen. Dette fungerer for utvikleren, men er ubrukelig for HR-personer uten teknisk bakgrunn.

For å dele verktøyet med andre i organisasjonen trenger vi:
- Et visuelt grensesnitt som HR-folk kan bruke uten opplæring
- En enkel distribusjon som ikke krever Python-installasjon eller terminalbruk
- Data som lagres lokalt på brukerens maskin (ikke i skyen — ennå)

## Solution

Bygge et lokalt web-grensesnitt som kjører i en Docker-container. Brukeren kjører én kommando (`docker run`), åpner nettleseren, og har tilgang til alle analyser med grafer, filtrering og PDF-eksport.

Arkitekturen er et tynt FastAPI-lag over den eksisterende `hr_database/`-pakken, med et enkelt HTML/CSS/JS-frontend. Ingen React, ingen build-steg, ingen kompleksitet utover det som trengs.

```
┌─────────────────────────────────────────┐
│  Docker-container (hr-analyse:latest)   │
│                                         │
│  Nettleser ◄──► FastAPI (port 8080)     │
│                   │                     │
│            hr_database/                 │
│            ├ analytics.py (uendret)     │
│            ├ importer.py  (uendret)     │
│            ├ database.py  (uendret)     │
│            └ report_generator.py        │
│                   │                     │
│              ansatte.db (volume)        │
└─────────────────────────────────────────┘
```

## Scope

### In scope
- FastAPI backend med REST API over alle eksisterende analytics-metoder
- Excel-opplasting via drag-and-drop i nettleseren
- Dashboard med interaktive grafer (Chart.js) for alle analyser
- PDF-rapportgenerering og nedlasting fra web-UI
- Dockerfile som pakker alt til ett kjørbart image
- Datapersistens via Docker volume (SQLite-filen overlever container-restart)
- Norskspråklig grensesnitt

### Out of scope
- Brukerautentisering / innlogging (kommer i fremtidig fase)
- HTTPS / TLS (ikke nødvendig for localhost)
- Deploy til sky / ekstern server
- Flerbruker-støtte / samtidig tilgang
- PII-maskering eller tilgangskontroll på sensitive felt
- Kobling mot konsern-databasen
- Endringer i forretningslogikk (analytics.py, importer.py)

## Success Criteria
- En HR-person uten teknisk bakgrunn kan kjøre `docker run hr-analyse` og bruke verktøyet i nettleseren uten hjelp
- Alle analyser fra CLI-et (13 kategorier, 30+ metoder) er tilgjengelige via web-UI
- Excel-import fungerer med drag-and-drop
- PDF-rapport kan genereres og lastes ned
- Eksisterende 91 tester fortsetter å passere uendret
- Container-image er under 500 MB
