# ECIT Selskapsanalyse

Interne analyseverktøy for ECIT Group. Inneholder to moduler:

- **HR-analyse** — importerer ansattdata fra VerismoHR (Excel), beregner nøkkeltall (turnover, sykefravær, kjønnsfordeling m.m.), og genererer PDF-rapporter. Tilgjengelig som web-dashboard og CLI.
- **Konsern-analyse** — importerer og søker i selskapsstruktur (konserntrær) fra Brønnøysundregistrene.

## Prosjektstruktur

```
hr/               HR-modul (database, import, analytikk, rapporter, CLI)
web/              FastAPI web-dashboard for HR-analyse
tests/            Pytest-tester for HR-modulen
konsern/          Konsern-modul (import, søk, utvidelse av selskapsdata)
scripts/          Engangsverktøy (anonymisering, kjedeanalyse)
data/             Databaser og datafiler (ikke sporet i git)
```

## Installasjon

```bash
pip install -r requirements.txt
```

Krever Python 3.11+.

## Bruk

### Web-dashboard (Docker)

```bash
docker compose up
```

Åpne http://localhost:8080 i nettleseren.

### Web-dashboard (lokal)

```bash
uvicorn web.app:app --host 0.0.0.0 --port 8080
```

### HR CLI

```bash
python -m hr
```

Interaktivt menybasert program for import, analyse og rapportgenerering.

### Konsern-verktøy

```bash
python konsern/import_data.py    # Importer selskapsdata
python konsern/sok.py            # Søk i konsernstruktur
python konsern/utvid_database.py # Utvid med tilleggsdata
```

## Testing

```bash
python -m pytest tests/ -v
```

## Datafiler

Databaser (`ansatte.db`, `konsern.db`) og Excel-filer lagres i `data/` og spores ikke i git. Legg dine datafiler der manuelt, eller bruk importfunksjonene.
