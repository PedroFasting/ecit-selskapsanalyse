# Tasks: Robust Excel Validation

## Fase 1: Kjernevalidering i importer.py

### 1.1 Definer dataklasser
- [x] Opprett `ImportValidation` dataclass: `matched_columns`, `missing_columns`, `unknown_columns`, `match_ratio`
- [x] Opprett `ImportResult` dataclass: `imported`, `errors`, `validation`, `warnings`

### 1.2 Implementer `validate_columns()`
- [x] Ny funksjon `validate_columns(actual_columns: pd.Index) -> ImportValidation`
- [x] Beregn matched/missing/unknown kolonner mot `COLUMN_MAPPING`
- [x] Beregn `match_ratio`

### 1.3 Implementer `build_warnings()`
- [x] Ny funksjon som bygger advarselsliste basert på `ImportValidation`
- [x] Nivåer: 0% match (rød tekst), <50% (tydelig advarsel), <100% (info om manglende kolonner), 100% (ingen advarsler)

### 1.4 Integrer i `import_excel()`
- [x] Kall `validate_columns()` rett etter `pd.read_excel()`
- [x] Kall `build_warnings()` for å bygge advarselsliste
- [x] Vis match-info i verbose-output
- [x] Endre returtype fra `int` til `ImportResult`
- [x] Importen kjøres alltid -- aldri blokkér basert på kolonner

---

## Fase 2: Oppdater API-lag

### 2.1 Oppdater `import_routes.py`
- [x] Importer `ImportResult` fra `hr_database.importer`
- [x] Pakk ut `result.validation` til `validering`-objekt i JSON-respons
- [x] Inkluder `result.warnings` som `advarsler` i JSON-respons
- [x] Behold eksisterende feilhåndtering for uventede feil (500)

---

## Fase 3: Oppdater frontend

### 3.1 Oppdater `app.js` uploadFile()
- [x] Vis advarsler (gul boks) under suksessmelding hvis `data.advarsler` finnes
- [x] Vis match-prosent i import-status

### 3.2 Oppdater `style.css`
- [x] Legg til `.warning`-klasse for gul advarselsboks

---

## Fase 4: Oppdater CLI

### 4.1 Oppdater `hr_cli.py`
- [x] Endre `count = import_excel(...)` til `result = import_excel(...)`
- [x] Vis `result.imported` som antall
- [x] Vis advarsler fra `result.warnings`

---

## Fase 5: Oppdater eksporter

### 5.1 Oppdater `__init__.py`
- [x] Eksporter `ImportResult`, `ImportValidation` fra pakken

---

## Fase 6: Tester

### 6.1 Nye tester i `test_importer.py`
- [x] Test `validate_columns()` med 100% match
- [x] Test `validate_columns()` med 0% match
- [x] Test `validate_columns()` med delvis match
- [x] Test `validate_columns()` med ukjente ekstra-kolonner
- [x] Test `build_warnings()` for hvert advarselsnivå
- [x] Test at `import_excel()` returnerer `ImportResult`

### 6.2 Nye tester i `test_api.py`
- [x] Test at respons inneholder `validering`-objekt ved suksess
- [x] Test at respons inneholder `advarsler` ved delvis match

### 6.3 Verifiser eksisterende tester
- [x] Kjør alle eksisterende tester -- verifiser at de passerer (179 passed, 2 xfailed)

---

## Avhengigheter

```
Fase 1 (kjernevalidering) ──► Fase 2 (API) ──► Fase 3 (frontend)
         │                                 
         ├──► Fase 4 (CLI)
         │
         ├──► Fase 5 (eksporter)
         │
         └──► Fase 6 (tester)
```
