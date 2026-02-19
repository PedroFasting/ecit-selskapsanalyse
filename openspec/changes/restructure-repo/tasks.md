# Tasks: Restructure Repository (Revidert)

> **Revidert 2026-02-19:** Oppdatert for å inkludere web-app, tester og Docker som ble lagt til etter original plan.
> **Strategi:** Flytt først, refaktorer konsern-modul senere. Minimale kodeendringer.

## Task 1: Opprett prosjektinfrastruktur
**Status:** pending

### 1.1 Opprett `.gitignore` i repo-rot
Komplett `.gitignore` med Python, data, IDE, OS og Docker-mønstre.

### 1.2 Opprett `data/` mappe
```bash
mkdir -p data
touch data/.gitkeep
```

### 1.3 Flytt `requirements.txt` til repo-rot
```bash
git mv konsern-database/requirements.txt requirements.txt
```

---

## Task 2: Flytt og reorganiser HR-modulen
**Status:** pending

### 2.1 Flytt hr_database/ til hr/
```bash
git mv konsern-database/hr_database/ hr/
```

### 2.2 Oppdater DB-sti i hr/database.py
`DEFAULT_DB_PATH` peker til `data/ansatte.db`.

### 2.3 Flytt hr_cli.py til hr/cli.py
```bash
git mv konsern-database/hr_cli.py hr/cli.py
```

### 2.4 Oppdater imports i hr/cli.py
Fjern `sys.path.insert(0, ...)` og oppdater til `from hr import ...`

### 2.5 Legg til `__main__.py` i hr/
Slik at modulen kan kjøres med `python -m hr`.

### 2.6 Oppdater rapporter-sti i hr/report_generator.py
Rapporter genereres til `data/rapporter/` i stedet for `rapporter/` relativt.

---

## Task 3: Flytt web-app
**Status:** pending

### 3.1 Flytt web/ til toppnivå
```bash
git mv konsern-database/web/ web/
```

### 3.2 Oppdater imports i web/app.py
Fra `from hr_database import ...` til `from hr import ...`

### 3.3 Oppdater imports i web/routes/*.py
Alle routes bruker `hr_database` — oppdater til `hr`.

### 3.4 Oppdater DB_PATH i web/app.py
Sørg for at DB-sti peker til `data/ansatte.db`.

---

## Task 4: Flytt tester
**Status:** pending

### 4.1 Flytt tests/ til toppnivå
```bash
git mv konsern-database/tests/ tests/
```

### 4.2 Oppdater imports i tests/conftest.py
Fra `from hr_database import ...` til `from hr import ...`

### 4.3 Oppdater imports i alle test_*.py filer
Endre alle `hr_database`-referanser til `hr`.

### 4.4 Oppdater imports for web/routes
Fra `from web.routes.import_routes import ...` — verifiser at stier er riktige.

---

## Task 5: Flytt konsern-filer til konsern/
**Status:** pending

> Filene flyttes som de er. Refaktorering til pakke-mønster gjøres i en egen change.

### 5.1 Opprett konsern/ mappe og flytt filer
```bash
mkdir -p konsern
git mv konsern-database/import_data.py konsern/
git mv konsern-database/sok.py konsern/
git mv konsern-database/utvid_database.py konsern/
```

### 5.2 Oppdater DB-stier i konsern-filene
Oppdater hardkodede stier til å peke mot `data/konsern.db`.

### 5.3 Opprett konsern/__init__.py
Minimal `__init__.py` som markerer mappen som pakke.

---

## Task 6: Flytt scripts
**Status:** pending

### 6.1 Flytt engangsverktøy
```bash
mkdir -p scripts
git mv konsern-database/anonymiser.py scripts/
git mv konsern-database/analyse_kjede.py scripts/
```

### 6.2 Oppdater stier i scripts
Oppdater database-stier til å peke mot `data/`.

---

## Task 7: Flytt datafiler, oppdater Docker, rydd opp
**Status:** pending

### 7.1 Flytt datafiler til data/
```bash
git mv konsern-database/konsern.db data/
git mv konsern-database/ansatte.db data/
git mv "konsern-database/Cost price subsidiaries 31012026 vPF-kopi_anon.xlsx" data/
git mv "konsern-database/FLASH Report December25- final_pl_anon.xlsx" data/
git mv "konsern-database/VerismoHR-Export-20260213152527_test Pedro.xlsx" data/
git mv "konsern-database/VerismoHR-Export-20260213152527_test Pedro Voppdatert.xlsx" data/
```

### 7.2 Fjern Excel lock-filer
```bash
git rm "konsern-database/~$FLASH Report December25- final_pl_anon.xlsx"
git rm "konsern-database/~$VerismoHR-Export-20260213152527_test Pedro.xlsx"
```

### 7.3 Flytt og oppdater Dockerfile
Flytt til toppnivå og oppdater COPY-stier for ny struktur.

### 7.4 Flytt og oppdater docker-compose.yml
Flytt til toppnivå og oppdater build-context.

### 7.5 Flytt rapporter/ til data/rapporter/
```bash
git mv konsern-database/rapporter/ data/rapporter/
```

### 7.6 Fjern konsern-database/ mappen
Etter at alt er flyttet:
```bash
git rm -r konsern-database/
```

---

## Task 8: Oppdater README.md
**Status:** pending

Skriv README med:
- Prosjektbeskrivelse (to analyseverktøy for ECIT)
- Moduler: HR (web-dashboard + CLI) og Konsern (CLI)
- Installasjon: `pip install -r requirements.txt`
- Bruk: `python -m hr.cli`, web-dashboard via Docker
- Docker: `docker compose up`

---

## Task 9: Verifiser at alt fungerer
**Status:** pending

### 9.1 Kjør tester
```bash
python -m pytest tests/ -v
```
Alle 216 tester skal passere.

### 9.2 Sjekk at git er rent
```bash
git status
```
Ingen utrackede filer som burde vært ignorert.
