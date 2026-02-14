# Tasks: Restructure Repository

## Task 1: Opprett prosjektinfrastruktur
**Status:** pending

Opprett grunnleggende prosjektfiler som mangler.

### 1.1 Opprett `.gitignore`
Opprett `.gitignore` i repoets rot med:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/

# Data
data/*.db
data/*.xlsx
data/~$*

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Excel lock files
~$*
```

### 1.2 Opprett `requirements.txt`
```
pandas>=2.0
openpyxl>=3.0
numpy>=1.24
```

### 1.3 Opprett `data/` mappe
```bash
mkdir -p data
touch data/.gitkeep
```

### 1.4 Oppdater `README.md`
Skriv en kort README som beskriver:
- Hva prosjektet er (to analyseverktøy for ECIT)
- Modulene: konsern (eierskapsanalyse) og hr (HR-analyse)
- Installasjon: `pip install -r requirements.txt`
- Bruk: `python -m konsern.cli` og `python -m hr.cli`
- Databehandling: Legg Excel-filer i `data/`

---

## Task 2: Flytt og reorganiser HR-modulen
**Status:** pending

HR-modulen er allerede godt strukturert. Flytt den til toppnivå.

### 2.1 Flytt hr_database/ til hr/
```bash
git mv konsern-database/hr_database/ hr/
```

### 2.2 Oppdater DB-sti i hr/database.py
Endre `DEFAULT_DB_PATH` fra:
```python
DEFAULT_DB_PATH = Path(__file__).parent.parent / "ansatte.db"
```
til:
```python
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "ansatte.db"
```

### 2.3 Flytt hr_cli.py til hr/cli.py
```bash
git mv konsern-database/hr_cli.py hr/cli.py
```

### 2.4 Oppdater imports i hr/cli.py
Fjern `sys.path.insert(0, ...)` og oppdater imports til å bruke relativ import:
```python
from hr import init_database, import_excel, list_imports, get_analytics, reset_database
```

### 2.5 Legg til `__main__.py` i hr/
Opprett `hr/__main__.py` slik at modulen kan kjøres med `python -m hr`:
```python
from hr.cli import main
if __name__ == "__main__":
    main()
```

### 2.6 Flytt ansatte.db til data/
```bash
git mv konsern-database/ansatte.db data/ansatte.db
```

---

## Task 3: Refaktorer og flytt konsern-modulen
**Status:** pending

Splitt de løse scriptene til en konsistent pakke-struktur.

### 3.1 Opprett konsern/ pakke
```bash
mkdir -p konsern
```

### 3.2 Opprett konsern/__init__.py
Eksporter public API, lik hr/:
```python
from .database import get_connection, init_database, DEFAULT_DB_PATH
from .importer import import_from_excel
from .analytics import KonsernAnalytics
```

### 3.3 Opprett konsern/database.py
Samle all schema-logikk fra `import_data.py` og `utvid_database.py`:
- `DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "konsern.db"`
- `get_connection(db_path=None)` - returner connection
- `init_database(db_path=None)` - opprett alle tabeller (selskaper, eierskap, oppkjop, finansiell, segment, selskap_segment)
- `create_tables(conn)` - intern funksjon med all CREATE TABLE logikk

### 3.4 Opprett konsern/importer.py
Flytt import-logikk fra `import_data.py`:
- `parse_ownership_matrix(excel_file, sheet_name="All Co")` 
- `import_from_excel(excel_file, db_path=None)`

### 3.5 Opprett konsern/analytics.py
Flytt analyse-logikk fra `sok.py` (alle funksjoner som gjør SQL-queries):
- `format_belop(belop)` 
- `sok_selskap(query, db_path=None)`
- `vis_eiere(selskap_id, db_path=None)`
- `vis_datterselskaper(selskap_id, db_path=None)`
- `vis_konsernstruktur(selskap_id, db_path=None)`
- `vis_eierkjede(selskap_id, db_path=None)`
- `vis_statistikk(db_path=None)`
- `vis_tre(selskap_id, vis_tall=True, db_path=None)`
- `vis_sammenligning(selskap_ider, db_path=None)`

### 3.6 Opprett konsern/cli.py
Flytt CLI REPL fra `sok.py`:
- `velg_selskap(resultater)` - brukerinteraksjon
- `main()` - REPL-loop
- Importer analyse-funksjoner fra `konsern.analytics`

### 3.7 Legg til `__main__.py` i konsern/
```python
from konsern.cli import main
if __name__ == "__main__":
    main()
```

### 3.8 Flytt konsern.db til data/
```bash
git mv konsern-database/konsern.db data/konsern.db
```

---

## Task 4: Flytt scripts
**Status:** pending

### 4.1 Opprett scripts/ mappe og flytt
```bash
mkdir -p scripts
git mv konsern-database/anonymiser.py scripts/
git mv konsern-database/analyse_kjede.py scripts/
```

### 4.2 Oppdater database-sti i analyse_kjede.py
Endre fra relativ `'konsern.db'` til:
```python
from pathlib import Path
DB_FILE = Path(__file__).parent.parent / "data" / "konsern.db"
```

---

## Task 5: Flytt Excel-filer og rydd opp
**Status:** pending

### 5.1 Flytt Excel-filer til data/
```bash
git mv "konsern-database/Cost price subsidiaries 31012026 vPF-kopi_anon.xlsx" data/
git mv "konsern-database/FLASH Report December25- final_pl_anon.xlsx" data/
git mv "konsern-database/VerismoHR-Export-20260213152527_test Pedro.xlsx" data/
```

### 5.2 Fjern Excel lock-filer
```bash
git rm "konsern-database/~\$FLASH Report December25- final_pl_anon.xlsx"
git rm "konsern-database/~\$VerismoHR-Export-20260213152527_test Pedro.xlsx"
```

### 5.3 Fjern test_database.py
```bash
git rm konsern-database/test_database.py
```

### 5.4 Fjern tomme mapper
```bash
rmdir konsern-database/static/ konsern-database/templates/
```

### 5.5 Fjern konsern-database/ mappen
Etter at alt er flyttet, fjern den gamle mappen:
```bash
git rm -r konsern-database/
```

---

## Task 6: Verifiser at alt fungerer
**Status:** pending

### 6.1 Test konsern CLI
```bash
python -m konsern.cli
```
Verifiser at søk og menyvalg fungerer.

### 6.2 Test HR CLI
```bash
python -m hr.cli
```
Verifiser at menyen vises og import fungerer.

### 6.3 Sjekk at git er rent
```bash
git status
```
Ingen utrackede filer som burde vært ignorert.
