# Design: Restructure Repository

## Approach

Restruktureringen gjøres i lag - først infrastruktur, så filflytting, og til slutt opprydding. Hver endring skal holde prosjektet fungerende underveis.

## Target Structure

```
ecit-selskapsanalyse/
├── .gitignore
├── README.md
├── requirements.txt
│
├── konsern/                        # Konsernstruktur-modul
│   ├── __init__.py                 # Public API (lik hr_database/)
│   ├── database.py                 # Schema, connection, DB_FILE
│   ├── importer.py                 # Excel -> SQLite (fra import_data.py)
│   ├── analytics.py                # Søk/analyse-logikk (fra sok.py)
│   └── cli.py                      # CLI REPL (presentasjon fra sok.py)
│
├── hr/                             # HR-modul (flyttet fra hr_database/)
│   ├── __init__.py                 # Eksisterende public API
│   ├── database.py                 # Eksisterende - oppdatert DB_FILE
│   ├── importer.py                 # Eksisterende
│   ├── analytics.py                # Eksisterende
│   └── cli.py                      # Fra hr_cli.py - oppdaterte imports
│
├── scripts/                        # Engangsverktøy
│   ├── anonymiser.py               # Flyttet, oppdaterte stier
│   └── analyse_kjede.py            # Flyttet, oppdaterte stier
│
├── data/                           # Data-filer (gitignored unntatt .gitkeep)
│   └── .gitkeep
│
└── openspec/                       # OpenSpec artefakter
    └── changes/
        └── restructure-repo/
```

## Key Decisions

### 1. Konsern-modulen refaktoreres til pakke-mønsteret fra hr_database

`sok.py` inneholder ~640 linjer med blandet logikk (SQL-queries, formatering, brukerinteraksjon). Denne splittes:

| Nåværende | Ny plassering | Innhold |
|-----------|---------------|---------|
| `sok.py` funksjoner med SQL | `konsern/analytics.py` | Søk, eierkjeder, statistikk |
| `sok.py` formatering + REPL | `konsern/cli.py` | CLI-presentasjon |
| `import_data.py` | `konsern/importer.py` | Excel-import |
| `utvid_database.py` + schema | `konsern/database.py` | All schema-logikk |

### 2. DB-stier sentraliseres per modul

Hver modul eier sin egen database-sti, men bruker `data/`-mappen:

```python
# konsern/database.py
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "konsern.db"

# hr/database.py  
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "ansatte.db"
```

### 3. Minimal refaktorering av logikk

Vi flytter og reorganiserer filer, men endrer ikke forretningslogikk. Unntak:
- Hardkodede stier fikses
- Import-statements oppdateres
- DB-stier peker til `data/`

### 4. test_database.py fjernes

Scriptet er ubrukelig (hardkodede absolutte stier, ingen assertions). Det gir ingen verdi å flytte.

### 5. Excel-filer og databaser flyttes til data/

Alle `.xlsx`, `.db` og lock-filer flyttes til `data/` og gitignores. `.gitkeep` sikrer at mappen finnes.

### 6. Tomme mapper fjernes

`static/` og `templates/` har ingen innhold og ingen kode refererer til dem.

## Migration Strategy

Rekkefølge som minimerer risiko:

1. **Infrastruktur først** - .gitignore, requirements.txt, data/
2. **HR-modul** - Enklest, allerede godt strukturert, bare flytte
3. **Konsern-modul** - Krever splitting av sok.py, mer arbeid
4. **Scripts** - Flytt engangsverktøy
5. **Opprydding** - Fjern gammel konsern-database/, oppdater README

## Risks

| Risiko | Tiltak |
|--------|--------|
| Import-stier brekker | Verifiser at CLI-ene fungerer etter hver flytting |
| Git-historikk går tapt | Bruk `git mv` der mulig for å bevare historikk |
| Databaser i data/ finnes ikke | Modulene håndterer allerede "db finnes ikke"-scenarioet |
