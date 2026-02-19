# Proposal: Robust Excel Validation

## Problem

Excel-importen i `hr_database/importer.py` har ingen validering av kolonner eller datainnhold. Den er hardkodet mot VerismoHR-eksportformatet med en `COLUMN_MAPPING` med 52 oppføringer, men sjekker aldri om de forventede kolonnene faktisk finnes i den opplastede filen.

Konkrete svakheter:

1. **Ingen kolonnevalidering** -- Hvis en Excel-fil har helt andre kolonner enn forventet, importeres alle rader med `NULL` i hvert eneste felt. API-et returnerer HTTP 200 med "Importerte N rader" som om alt var vellykket.

2. **Ingen advarsel ved delvis match** -- Hvis VerismoHR endrer eksporten (fjerner, omdøper eller legger til kolonner), oppdages ikke dette. Manglende kolonner blir stille `NULL`.

3. **Kritiske felt uten beskyttelse** -- `medarbeidernummer` (UNIQUE constraint), `fornavn`, `etternavn` kan alle bli `NULL`. Med `NULL` medarbeidernummer insertes dupliserte rader istedenfor REPLACE.

4. **`clear_existing=True` uten sikkerhetssjekk** -- Brukeren kan slette all eksisterende data og erstatte med tomme rader uten at systemet advarer.

5. **Feil returneres ikke til bruker** -- Per-rad feil skrives til stdout (usynlig i web-kontekst). Importresultatet inneholder ikke info om datakvalitet.

6. **Hardkodet header-rad** -- `pd.read_excel(filepath, header=1)` antar at rad 2 er header. Andre Excel-filer vil gi meningsløse kolonnenavn.

## Solution

Innføre validering i tre lag:

### Lag 1: Kolonne-gjenkjenning (i `importer.py`)
Etter `pd.read_excel()`, sjekk hvor mange av `COLUMN_MAPPING`-nøklene som finnes i DataFrame-kolonnene. Returner strukturert info om match/mangler.

### Lag 2: Kritisk-kolonne-sjekk (i `importer.py`)
Definer et sett med kritiske kolonner (f.eks. `Fornavn`, `Etternavn`, `Medarbeidernummer`) som **må** finnes for at importen skal kjøres. Avbryt med tydelig feilmelding hvis disse mangler.

### Lag 3: Valideringsrespons (i API + frontend)
Returner valideringsinfo (matchede kolonner, manglende kolonner, advarsler) i API-responsen slik at brukeren ser hva som skjedde. Ved alvorlige problemer, blokkér importen og vis hva som er galt.

## Scope

### In scope
- Kolonnevalidering etter Excel-lesing i `import_excel()`
- Definisjon av kritiske vs. valgfrie kolonner
- Strukturert valideringsresultat fra `import_excel()` (matchede, manglende, ukjente kolonner)
- Oppdatert API-respons med valideringsinfo
- Frontend-visning av advarsler/feil ved import
- Tester for alle valideringsscenarier (feil format, delvis match, manglende kritiske kolonner)

### Out of scope
- Automatisk kolonne-gjetting/fuzzy matching (f.eks. "First name" -> "Fornavn")
- Støtte for flere Excel-formater
- Endre database-skjema
- Datatype-validering per celle (f.eks. at `alder` er et tall)
- Preview/mapping-UI der brukeren manuelt mapper kolonner

## Success Criteria
- Opplasting av feil Excel-format gir tydelig feilmelding (ikke stille suksess)
- Opplasting av riktig format med manglende kolonner gir advarsel med liste over hva som mangler
- Opplasting av riktig format med alle kolonner fungerer som i dag
- Eksisterende tester fortsetter å passere
- Nye tester dekker alle valideringsscenarier
