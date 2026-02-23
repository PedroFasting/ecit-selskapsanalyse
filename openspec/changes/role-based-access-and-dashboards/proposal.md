# Proposal: Rollebasert tilgangskontroll og dashboards

## Bakgrunn

Applikasjonen er i dag et åpent analyseverktøy uten autentisering, roller eller tilgangskontroll. Alle med nettverkstilgang ser all data (inkl. sensitiv informasjon som personnummer og lønn). Dashboard-konfigurasjon lagres i nettleserens localStorage — det finnes ingen deling mellom brukere eller sentral styring.

ECIT har en kompleks organisasjonsstruktur med selskaper i flere land, divisjoner som går på tvers, "lokomotiver" (store selskaper med egne funksjoner), og avdelinger. Ulike brukere skal se ulike utsnitt av data basert på sitt ansvarsområde.

### Referanse: "Den Store PoC"

Dette arbeidet er relatert til det formelle ECIT-prosjektet **HR Analytics PoC** (ECIT NEXT HR-19 / CORP-IT-B 4b / CORP-IT-C 6), som har som mål å bygge et HR-dashboard for å forstå employee churn, med MS Fabric som dataplattform og Power BI som presentasjonslag.

Vår app fungerer som en lettvekts-MVP som kan:
- Vise verdi raskt uten å vente på Fabric-infrastruktur
- Teste og validere KPI-definisjoner før de formaliseres i Fabric
- Fungere som prototype for hvilke analyser som gir innsikt
- Eventuelt kobles til Fabric som datakilde på sikt

**KPI-mapping mot Den Store PoC:**

| PoC-metrikk | Definisjon | Status i vår app |
|-------------|-----------|------------------|
| Staff turnover | Andel som slutter / snitt headcount | **Har** (churn-fane + analysator) |
| Early turnover | Andel som slutter innen 12 mnd | **Delvis** (har start/slutdato, mangler beregning) |
| Employee engagement index | Sammensatt score fra medarbeiderundersøkelse | **Mangler** — krever ny datakilde (fase 5) |
| Organizational experience | Gjennomsnittlig ansiennitet | **Har** (`avg_tenure`) |
| Salary growth | Årlig lønnsøkning i % | **Mangler** — krever lønnshistorikk over tid |
| Span per people manager | Snitt direkte rapporter per leder | **Delvis** (har `ledere`-felt, mangler beregning) |
| Internal mobility rate | Andel som bytter rolle internt siste 12 mnd | **Mangler** — krever posisjonshistorikk |
| Gender pay ratio | Snittlønn kvinner / snittlønn menn | **Har** (lønn + kjønn i analysator) |

**HR ERM fra PoC-planen** (entiteter vi bør ta høyde for):

```
POSITION ──▶ JOB                     Vi har: tittel, rolle, jobbfamilie,
    │                                        ansettelsesniva
EMPLOYEE ──▶ EMPLOYMENT ──▶ ORG     Vi har: ansatte-tabell (flat)
    │              │                         med selskap, avdeling, land
    ▼              ▼
SURVEY RESP   COMPENSATION ──▶ COST CENTER
(ny kilde)    Vi har: lønn (snapshot)  Vi har: kostsenter
```

**Datakilder nevnt i PoC-planen:** Verismo, Sympa, Simployer (HR), EES (survey), TeamTailor (ATS), LinkedIn, HSE-systemer. Alle kan potensielt importeres som Excel i vår app.

## Mål

Bygge et rollebasert system der:
- **HR-superbrukere** har full tilgang og kan konfigurere dashboards for andre roller
- **HR-brukere** har bred datatilgang og ser views tildelt av superbruker
- **Ledere/ansvarlige** ser kun data for sin scope (selskap, avdeling, divisjon, land)
- Dashboard-konfigurasjon lagres server-side og styres av superbruker

## Prinsipp: Dataminimering

Appen er et analyseverktøy, ikke et HR-opslagsystem. Vi skal **kun lagre og vise data som trengs for analyse**. Sensitiv persondata som personnummer, bankkontonummer, IBAN, BIC og clearingnummer har ingen funksjon i analyse og skal:

- Ikke importeres (fjernes fra COLUMN_MAPPING), eller i det minste aldri eksponeres via API/UI
- Fødselsdato beholdes kun for å beregne alder
- Søk-fanen begrenses til analysenyttig info: navn, e-post, telefon, avdeling, selskap, rolle, land, startdato
- Har brukere behov for sensitiv persondata, henter de det direkte i HR-systemet (Verismo)

Dette er uavhengig av roller og tilgangskontroll — det er et grunnprinsipp for appen.

## Brukerroller

| Rolle | Datatilgang | Kan konfigurere | Kan importere |
|-------|-------------|-----------------|---------------|
| **HR Super** | Alt | Dashboards for alle roller, brukerstyring, overstyre roller/scope | Ja |
| **HR Bruker** | Bred (alt eller stort scope) | Egne pins | Mulig |
| **Leder** | Kun sin scope | Egne pins innenfor sin scope | Nei |

Roller hentes primært fra HR-systemets eksportfil (VerismoHR). Superbruker kan overstyre manuelt.

## Scope-modell

En brukers "scope" definerer hvilke ansatte de ser data for. Scope er IKKE et rigid hierarki — det er fleksible grupperinger som kan overlappe:

```
Scope-typer:
  land          → "Norge", "Danmark", "Sverige"
  selskap       → "ECIT AS", "ECIT DK ApS"
  avdeling      → "Regnskap Oslo"
  divisjon      → "Cloud Services" (kan gå på tvers av land)
  lokomotiv     → Gruppe av selskaper med felles funksjoner
  alle          → Full tilgang (HR Super)
```

En bruker kan ha én eller flere scope-tilknytninger:
- Kari: `[land:Norge]` → ser alle ansatte i norske selskaper
- Ole: `[selskap:"ECIT Regnskap AS"]` → ser kun det selskapet
- Hilde: `[alle]` → ser alt

Scope-data hentes fra:
1. **HR-eksportfilen** — selskap, avdeling, rolle, er_leder finnes allerede
2. **Konsern-matrisen** (konsern.db) — eierstruktur, kan brukes for selskapsgrupper
3. **Manuell overstyring** av superbruker ved behov

Gruppestrukturer (divisjon, lokomotiv) endres sjelden og kan defineres i HR-systemet og/eller i konsern-matrisen.

## Autentisering

Microsoft Entra ID (Azure AD) SSO. ECIT har flere tenants men felles Teams-miljø.

Nøkkelprinsipper:
- SSO verifiserer identitet ("hvem er du")
- Appen har egen invitasjonsliste — ikke alle i tenant får tilgang
- Superbruker inviterer brukere og kan styre tilgang
- Detaljer rundt app-registrering (multi-tenant vs. single-tenant) må avklares med IT

## Faser

### Fase 0: Nåværende tilstand (ingen endring)
Appen brukes som i dag av HR-teamet uten tilgangskontroll. Brukes parallelt mens vi bygger fase 1-4.

### Fase 1: Grunnmur — autentisering og brukermodell
- Bruker-tabell i database (id, e-post, navn, rolle, scope, invitert_av, aktiv)
- SSO-integrasjon mot Microsoft Entra ID
- Invitasjonssystem: superbruker legger til brukere via e-post
- Innloggingskrav på alle sider/API-kall
- Enkel rolle: innlogget = tilgang, ikke innlogget = ingen tilgang
- CORS strammes inn fra `*`

### Fase 2: Organisasjonsstruktur og scope
- Scope-tabell i database (bruker_id, scope_type, scope_verdi)
- Grupperingstabeller (divisjoner, lokomotiver, selskapsgrupper)
- Koble konsern-matrise (konsern.db) til scope-modellen
- Import av rolle/scope fra HR-eksportfil (utvidelse av COLUMN_MAPPING)
- Superbruker-grensesnitt for å overstyre roller og scope
- Avklare med HR hvilke gruppe-felter som kommer i eksporten

### Fase 3: Data-scope i API
- Middleware/dependency som løser brukerens scope til SQL-filter
- Alle API-endepunkter filtrerer data basert på brukerens scope
- Scope-arv: ansvar for divisjon → ser alle selskaper i divisjonen
- Analysatoren (analyzer.py) får implicit scope-filter i tillegg til eksplisitte filtre
- Sensitiv persondata importeres ikke / eksponeres ikke (se prinsipp om dataminimering)

### Fase 4: Rollebaserte dashboards
- Dashboard-konfigurasjon flyttes fra localStorage til database
- Superbruker kan lage "views" (sett med pinnede grafer) og tildele til roller
- Brukere ser views tildelt sin rolle på Oversikt-fanen
- Brukere kan i tillegg ha egne pins (lagret server-side)
- Preset-dropdown erstattes av rolle-tildelte views

### Fase 5: Utvidet analyse — flere datakilder og sammenhenger

Applikasjonen utvides fra ren HR-rapportering til en analytisk plattform som kan avdekke sammenhenger på tvers av datakilder. Målet er å svare på det strategiske spørsmålet fra Den Store PoC: **"What underlying factors drive employee churn?"**

**Nye KPIer som krever nye datakilder:**
- **Employee engagement index** — fra medarbeiderundersøkelser (EES e.l.), aggregert per avdeling/selskap
- **Salary growth** — krever lønnshistorikk (flere Verismo-snapshots over tid, eller lønnsendringsfil)
- **Internal mobility rate** — krever posisjonshistorikk (stillingsendringer over 12 mnd)
- **Early turnover** — beregning av andel som slutter innen 12 mnd (data finnes, mangler beregningslogikk)
- **Span per people manager** — beregning av direkte rapporter (delvis data finnes via `ledere`-felt)

**Nye datakilder (aggregerte/anonymiserte):**
- Medarbeiderundersøkelser (EES-verktøy → Excel-eksport, aggregert per avdeling/selskap)
- Sykefravær (aggregert per enhet)
- Exit-intervjuer / sluttårsaker (aggregert)
- Onboarding-feedback
- Kompetansekartlegging
- Rekrutteringsdata (TeamTailor e.l.)
- Andre relevante Excel-eksporter fra HR-systemer (Sympa, Simployer)

**Datamodell:**
I dag har vi én flat tabell (ansatte). Fase 5 introduserer tilleggstabeller som kobles på avdelings-/selskapsnivå (ikke individnivå, pga. anonymitet):

```
ansatte (per person, som i dag)
  │
  ├── kobles via avdeling/selskap ──▶ undersokelse_resultater (aggregert)
  ├── kobles via avdeling/selskap ──▶ fravar_statistikk (aggregert)
  ├── kobles via avdeling/selskap ──▶ exit_data (aggregert)
  └── ...flere kilder over tid
```

**Analysemuligheter:**
- "Har avdelinger med lav trivselsscore høyere turnover?"
- "Er det sammenheng mellom ledertetthet og medarbeidertilfredshet?"
- "Hvilke avdelinger har risikosignaler — høy churn + lavt engasjement?"
- Trendanalyse over tid (flere undersøkelsesrunder)

**Importflyt:**
Bruker samme Excel-importmønster som i dag — nye filtyper med egne COLUMN_MAPPING-definisjoner. Superbruker laster opp, systemet gjenkjenner filtype og importerer til riktig tabell.

**Arkitekturimplikasjon:**
Analysatoren (analyzer.py) må utvides til å kunne joine/korrelere data fra flere tabeller. Scope-filtrering (fase 3) må fungere på tvers av alle datakilder.

**NB:** Denne fasen bygges gradvis. MVP kan være så enkelt som import av én undersøkelsesfil + ett korrelasjonsdashboard. Detaljert design lages når datakilder er avklart.

**Quick wins (kan bygges uten nye datakilder):**
- Early turnover-beregning (data finnes allerede: startdato + slutdato)
- Span per manager (kan estimeres fra `ledere`-feltet)
- Gender pay ratio som eksplisitt KPI (data finnes, mangler dedikert visning)
- Churn-korrelasjon mot eksisterende dimensjoner (avdeling, ansiennitet, alder, land)

## Avhengigheter og avklaringer

Følgende må avklares før/under implementering:

### Med IT-avdelingen
- [ ] Entra ID app-registrering: multi-tenant eller single-tenant?
- [ ] Hvilke tenants/domener skal støttes? (.com, .no, andre?)
- [ ] Finnes det en felles Entra ID-tenant, eller må vi støtte flere?

### Med HR-avdelingen
- [ ] Hvilke rolle-/gruppefelter kommer i VerismoHR-eksporten?
- [ ] Divisjon/lokomotiv — finnes disse som kolonner, eller er det en separat eksport?
- [ ] Rapporteringsstruktur (hvem rapporterer til hvem) — kommer dette i eksporten?
- [ ] Hvilke roller/grupper brukes i HR-systemet som er relevante for tilgangsstyring?
- [ ] Medarbeiderundersøkelser — hvilket system brukes, og kan resultater eksporteres som Excel?
- [ ] Hvilke aggregeringsnivåer finnes i undersøkelsesdata (avdeling, selskap, land)?
- [ ] Finnes det andre relevante datakilder (sykefravær, exit-intervjuer) som kan eksporteres?

### Tekniske
- [ ] Velge SSO-bibliotek (msal-python vs. authlib)
- [ ] Session-håndtering (JWT tokens vs. server-side sessions)
- [ ] Migrering av localStorage-pins for eksisterende brukere

## Utenfor scope

- Selvregistrering (kun invitasjon av superbruker)
- Vanlige ansatte som brukergruppe (kun HR + ledere)
- Revisjonsspor / audit log (kan legges til senere)
- To-faktor utover det Entra ID allerede krever
- Mobilapp / responsivt design
- Maskinlæringsmodeller / prediktiv analyse (kan vurderes etter fase 5)
- Sanntidsintegrasjoner / API-kobling mot andre systemer (kun filimport i første omgang)

## Status
**UTKAST** — til diskusjon med HR og IT. Brukes som grunnlag for avklaringsmøter.

## Referansedokumenter
- `Diverse/HRDSC_2026-02-18[1]-kopi.pdf` — HR Analytics PoC presentasjon ("Den Store PoC")
