# Design: Robust Excel Validation

## Designprinsipp

**Last inn alt du kan, men fortell brukeren hva som skjedde.**

Importen skal aldri blokkeres. Hvis filen har noen gjenkjente kolonner, importeres de. Brukeren får alltid tilbakemelding om hva som ble lastet og hva som manglet -- fra "alt OK" til "nesten ingenting ble gjenkjent".

## Approach

Legge til validering i den eksisterende import-flyten uten å bryte API-kontrakten. Valideringen skjer i `importer.py` og resultatene propageres opp via en ny returtype. API-laget og frontenden oppdateres for å vise valideringsinfo.

## Arkitektur

Ingen nye filer -- endringer i eksisterende filer:

```
konsern-database/
├── hr_database/
│   └── importer.py           # ENDRES — valideringslogikk + ny returtype
├── web/
│   ├── routes/
│   │   └── import_routes.py  # ENDRES — håndter valideringsresultat
│   └── static/js/
│       └── app.js            # ENDRES — vis advarsler/feil i UI
└── tests/
    ├── test_importer.py      # ENDRES — nye valideringstester
    └── test_api.py           # ENDRES — nye API-tester for validering
```

## Key Decisions

### 1. Aldri blokkér import -- alltid informér

| Scenario | Match | Handling |
|----------|-------|----------|
| Alle kolonner matcher | 100% | Grønn suksess: "52/52 kolonner gjenkjent" |
| Noen kolonner mangler | 50-99% | Importér + gul advarsel: "38/52 kolonner gjenkjent. Mangler: Lønn, Alder, ..." |
| Nesten ingen match | 1-49% | Importér + tydelig oransje advarsel: "Kun 3/52 kolonner gjenkjent -- er dette riktig fil?" |
| Null match | 0% | Importér (rader med NULL) + rød advarsel: "Ingen kolonner gjenkjent. 200 rader ble lastet men all data er tom." |

**Begrunnelse:** Brukeren vet bedre enn koden om filen er riktig. Systemets jobb er å gjøre jobben sin og rapportere resultatet -- ikke å nekte.

### 2. Valideringsresultat som dataclass

```python
from dataclasses import dataclass, field

@dataclass
class ImportValidation:
    matched_columns: list[str]      # Excel-kolonner som ble gjenkjent
    missing_columns: list[str]      # Forventede kolonner som ikke finnes
    unknown_columns: list[str]      # Kolonner i Excel som ikke er i mappingen
    match_ratio: float              # Andel matchede kolonner (0.0 - 1.0)

@dataclass
class ImportResult:
    imported: int                   # Antall importerte rader
    errors: int                     # Antall rader med feil
    validation: ImportValidation    # Kolonnevalidering
    warnings: list[str] = field(default_factory=list)
```

**Begrunnelse:**
- Strukturert data som er lett å serialisere til JSON
- Tydelig separasjon mellom import-resultat og valideringsinfo
- Ingen exception-klasser nødvendig -- importen feiler aldri på grunn av kolonner

### 3. Valideringspunkt: Etter `pd.read_excel()`, før row-iterasjon

```python
df = pd.read_excel(filepath, header=1)

# NY: Valider kolonner og bygg feedback
validation = validate_columns(df.columns)
warnings = build_warnings(validation)

if verbose:
    if validation.match_ratio == 1.0:
        print(f"  Alle {len(validation.matched_columns)} kolonner gjenkjent")
    else:
        print(f"  {len(validation.matched_columns)}/{len(COLUMN_MAPPING)} kolonner gjenkjent")
        if validation.missing_columns:
            print(f"  Mangler: {', '.join(validation.missing_columns)}")

# ... fortsett import som før
```

**Begrunnelse:**
- Legger seg naturlig inn i eksisterende flyt uten refaktorering
- Ingen branching som stopper importen
- `verbose`-output gir synlighet i CLI

### 4. Advarselsnivåer basert på match-ratio

```python
def build_warnings(validation: ImportValidation) -> list[str]:
    warnings = []
    
    if validation.match_ratio == 0.0:
        warnings.append(
            f"Ingen av {len(COLUMN_MAPPING)} forventede kolonner ble gjenkjent. "
            f"Alle rader ble importert med tom data. Er dette en VerismoHR-eksport?"
        )
    elif validation.match_ratio < 0.5:
        warnings.append(
            f"Kun {len(validation.matched_columns)}/{len(COLUMN_MAPPING)} kolonner gjenkjent "
            f"({validation.match_ratio:.0%}). Mye data vil mangle."
        )
    elif validation.missing_columns:
        warnings.append(
            f"{len(validation.missing_columns)} kolonner mangler: "
            f"{', '.join(validation.missing_columns[:5])}"
            f"{'...' if len(validation.missing_columns) > 5 else ''}"
        )
    
    return warnings
```

### 5. API-respons med valideringsinfo

Responsen utvides men brekker ikke eksisterende kontrakt -- nye felter legges til.

**Full match:**
```json
{
  "status": "ok",
  "melding": "Importerte 200 rader fra VerismoHR-Export.xlsx",
  "antall_rader": 200,
  "filnavn": "VerismoHR-Export.xlsx",
  "validering": {
    "matchede_kolonner": 52,
    "totalt_forventede": 52,
    "match_prosent": 100,
    "manglende": []
  }
}
```

**Delvis match:**
```json
{
  "status": "ok",
  "melding": "Importerte 200 rader fra VerismoHR-Export.xlsx",
  "antall_rader": 200,
  "filnavn": "VerismoHR-Export.xlsx",
  "advarsler": [
    "7 kolonner mangler: Lønn, Alder, BIC, IBAN, Clearingnummer, ..."
  ],
  "validering": {
    "matchede_kolonner": 45,
    "totalt_forventede": 52,
    "match_prosent": 87,
    "manglende": ["Lønn", "Alder", "BIC", "IBAN", "Clearingnummer", "Bankkontonummer", "Sykekasse"]
  }
}
```

**Null match (importerer likevel):**
```json
{
  "status": "ok",
  "melding": "Importerte 200 rader fra random-file.xlsx",
  "antall_rader": 200,
  "filnavn": "random-file.xlsx",
  "advarsler": [
    "Ingen av 52 forventede kolonner ble gjenkjent. Alle rader ble importert med tom data. Er dette en VerismoHR-eksport?"
  ],
  "validering": {
    "matchede_kolonner": 0,
    "totalt_forventede": 52,
    "match_prosent": 0,
    "manglende": ["Fornavn", "Etternavn", "..."]
  }
}
```

### 6. Frontend-visning

Bruker eksisterende `#import-status`-elementet med en ny CSS-klasse:

- **100% match**: Grønn melding som i dag + "52/52 kolonner gjenkjent"
- **50-99% match**: Gul melding med liste over manglende kolonner
- **1-49% match**: Oransje/gul melding med tydelig "er dette riktig fil?"
- **0% match**: Rød advarsel (men importen skjedde) med "all data er tom"

Ny CSS-klasse `.warning` for gul variant. Advarsler vises under suksessmeldingen.

## Endringer i eksisterende kode

| Fil | Endring | Risiko |
|-----|---------|--------|
| `importer.py` | Ny `validate_columns()`, `ImportResult`/`ImportValidation` dataclasses. `import_excel()` returnerer `ImportResult` istedenfor `int`. | Medium -- endrer returtype. CLI bruker også `import_excel()`. |
| `import_routes.py` | Pakk ut valideringsinfo og advarsler i JSON-respons. | Lav |
| `app.js` | Vis advarsler med gul/oransje styling, vis match-prosent. | Lav |
| `hr_cli.py` | Oppdater til å håndtere `ImportResult` istedenfor `int`. | Lav |
| `test_importer.py` | Nye tester for `validate_columns()`, ulike match-scenarier. | Ingen -- kun nye tester |
| `test_api.py` | Nye tester for valideringsinfo i API-respons. | Ingen -- kun nye tester |

### Bakoverkompatibilitet med CLI

`hr_cli.py` linje 197 oppdateres:
```python
result = import_excel(filepath, clear_existing=clear, verbose=True)
print(f"\n Importert {result.imported} ansatte")
for warning in result.warnings:
    print(f"  Advarsel: {warning}")
```

## Risks

| Risiko | Konsekvens | Tiltak |
|--------|-----------|--------|
| Endret returtype brekker eksisterende kode | CLI og evt. andre callsites feiler | Oppdater alle callsites i samme endring. Kjør alle tester. |
| Bruker ignorerer advarsler og laster feil data | Database fylles med NULL-rader | Akseptabelt -- brukeren tar beslutningen. Advarslene er tydelige nok. |
| VerismoHR endrer kolonnenavn | Match-ratio synker, advarsler vises | Bra -- brukeren ser at noe er annerledes og kan oppdatere COLUMN_MAPPING. |
