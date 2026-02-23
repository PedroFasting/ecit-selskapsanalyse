# Proposal: Server-side dashboard-pins med brukeridentitet og profilvalg

## Bakgrunn

Pin-funksjonaliteten i Analyse-fanen lar brukere feste grafer til Oversikt-dashboardet. I dag har den flere problemer:

1. **Lagring i localStorage** — pins er bundet til én nettleser, synkroniserer ikke mellom enheter, og forsvinner ved tømming av nettleserdata
2. **Kun første pin fungerer pålitelig** — `chart_type` lagres som `null` når brukeren ikke eksplisitt har valgt graftype (bruker auto-suggest), og det finnes ingen duplikat-deteksjon
3. **Ingen brukeridentitet** — "Mine grafer" betyr "denne nettleseren", ikke "denne brukeren"
4. **Ingen profilvalg ved pin** — grafer legges alltid i "Mine grafer", men det er behov for at admin kan legge grafer på fellesrapporter (HR-oversikt, Ledelse, osv.)
5. **Presets er hardkodet** — dashboard-maler er definert i JavaScript, ikke konfigurerbare
6. **Unpin er skjult** — X-knapp vises kun ved hover, og det er uklart at man kan fjerne grafer

### Relasjon til rolle-proposalen

`openspec/changes/role-based-access-and-dashboards/proposal.md` beskriver en full 5-fase plan med Entra ID SSO, scope-modell og rollebaserte dashboards. Denne endringen er en **pragmatisk mellomløsning** som implementerer fase 4 (dashboard-pins i database) med en forenklet brukermodell som senere kan oppgraderes til full SSO.

## Mål

1. Flytte pin-lagring fra localStorage til SQLite-database
2. Innføre enkel brukeridentitet (brukernavn + rolle, uten passord/SSO i første omgang)
3. La brukere velge hvilken profil/rapport en graf skal pinnes til ved pin-tidspunkt
4. La admin opprette og redigere profiler (erstatter hardkodede presets)
5. Fikse bugs: null chart_type, duplikat-pins, "kun første fungerer"
6. Tydelig unpin-funksjonalitet

## Arkitekturbeslutninger

### Brukeridentitet: Enkel dropdown-basert innlogging

Siden appen brukes internt av et lite team og full SSO krever IT-avklaringer, starter vi med:
- Brukertabell i database med navn, e-post, rolle (admin/bruker)
- Innlogging via dropdown/enkel identifisering (ikke passord)
- Lagrer valgt bruker i session/cookie
- Kan byttes til Entra ID SSO senere uten å endre resten av arkitekturen

Roller:
- **admin** — full tilgang, kan opprette/redigere profiler, kan pinne grafer til alle profiler
- **bruker** — kan pinne til "Mine grafer", ser profiler tildelt av admin

### Dashboard-profiler: Erstatter hardkodede presets

Dagens `DASHBOARD_PRESETS` (hr-oversikt, ledelse, lonn-analyse, mangfold) flyttes til database som konfigurerbare profiler. Admin kan opprette nye profiler og legge til/fjerne grafer.

### Pin-lagring: Database med profil-tilhørighet

Hver pin kobles til en bruker OG en profil:
- "Mine grafer" = pins tilhørende innlogget bruker, profil = null
- Navngitt profil = pins tilhørende profilen (synlig for alle med tilgang)

### Migrering

Eksisterende localStorage-pins migreres til "Mine grafer" i database ved første innlogging.

## Prinsipp: Oppgraderbar arkitektur

Alt som bygges her skal fungere uendret når Entra ID SSO legges til i fremtiden:
- Bruker-tabellen utvides med SSO-felter (entra_id, token, osv.)
- Login-mekanismen byttes, men API-endepunkter og pin-modell forblir
- Scope-filtrering (fase 2-3) kan legges oppå uten endringer i pin-systemet

## Utenfor scope

- SSO / Entra ID (bygges i fase 1 av rolle-proposalen)
- Scope-basert datafiltrering (fase 2-3)
- Passordhåndtering
- Revisjonsspor
