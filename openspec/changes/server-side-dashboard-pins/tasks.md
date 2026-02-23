# Tasks: Server-side dashboard-pins

## Fase A: Backend-grunnmur (database + API)

### A1. Databaseskjema
- [ ] Legg til `brukere`-tabell i `hr/database.py:init_database()`
- [ ] Legg til `dashboard_profiler`-tabell
- [ ] Legg til `dashboard_pins`-tabell med indekser
- [ ] Seed-funksjon: opprett standard admin-bruker
- [ ] Seed-funksjon: migrer `DASHBOARD_PRESETS` fra JS til database (hr-oversikt, ledelse, lonn-analyse, mangfold)
- [ ] Oppdater `tests/conftest.py` med fixtures for nye tabeller

### A2. Auth-endepunkter
- [ ] Opprett `web/routes/dashboard.py`
- [ ] `GET /api/users` — liste alle aktive brukere
- [ ] `POST /api/users` — opprett bruker (admin-only)
- [ ] `POST /api/auth/login` — sett bruker-cookie
- [ ] `GET /api/auth/me` — hent innlogget bruker fra cookie
- [ ] `POST /api/auth/logout` — fjern cookie
- [ ] Auth-middleware: les cookie, sett `request.state.user` (eller None)
- [ ] Registrer router i `web/app.py`

### A3. Dashboard-profil-endepunkter
- [ ] `GET /api/dashboard/profiles` — hent profiler synlig for bruker
- [ ] `POST /api/dashboard/profiles` — opprett profil (admin)
- [ ] `PUT /api/dashboard/profiles/{id}` — oppdater profil (admin)
- [ ] `DELETE /api/dashboard/profiles/{id}` — slett profil + tilhørende pins (admin)

### A4. Pin-endepunkter
- [ ] `GET /api/dashboard/pins?profile_id=X` — hent pins for profil/bruker
- [ ] `POST /api/dashboard/pins` — opprett pin med duplikat-sjekk
- [ ] `DELETE /api/dashboard/pins/{id}` — slett pin (med tilgangssjekk)
- [ ] `PUT /api/dashboard/pins/reorder` — endre pin-rekkefølge
- [ ] `POST /api/dashboard/pins/migrate-local` — migrer localStorage-pins

### A5. Backend-tester
- [ ] Test brukere CRUD
- [ ] Test auth-flyt (login/me/logout)
- [ ] Test profil CRUD med rollesjekk
- [ ] Test pin CRUD med rollesjekk
- [ ] Test duplikat-deteksjon ved pin
- [ ] Test localStorage-migrering
- [ ] Test at vanlig bruker ikke kan pinne til profiler
- [ ] Test at admin kan pinne til alle profiler

---

## Fase B: Frontend-endringer

### B1. Login-flyt
- [ ] Login-modal HTML i `index.html`
- [ ] CSS for login-modal i `style.css`
- [ ] JS: Sjekk `GET /api/auth/me` ved app-start
- [ ] JS: Populer bruker-dropdown fra `GET /api/users`
- [ ] JS: Login via `POST /api/auth/login` → skjul modal → last app
- [ ] JS: Vis innlogget brukernavn i header/footer
- [ ] JS: Logout-knapp

### B2. Pin-modal
- [ ] Pin-modal HTML i `index.html`
- [ ] CSS for pin-modal i `style.css`
- [ ] JS: Åpne modal ved klikk på pin-knapp
- [ ] JS: Populer profilvalg fra `GET /api/dashboard/profiles` (filtrert på rolle)
- [ ] JS: "Fest"-knapp kaller `POST /api/dashboard/pins`
- [ ] JS: Vis bekreftelse etter pin
- [ ] JS: Fiks chart_type — bruk faktisk brukt type, ikke `analyseChartType` (som kan være null)

### B3. Dashboard-oversikt refaktor
- [ ] Fjern `DASHBOARD_PRESETS` objekt fra `app.js`
- [ ] Fjern `getPinnedCharts()`, `savePinnedCharts()` (localStorage-funksjoner)
- [ ] Populer `#dashboard-preset` dropdown fra `GET /api/dashboard/profiles`
- [ ] Endre `renderDashboardCharts()` til å hente pins fra API
- [ ] Endre `unpinChart()` til å kalle `DELETE /api/dashboard/pins/{id}`
- [ ] Vis unpin-knapp synlig (ikke bare hover) for redigerbare profiler
- [ ] Vis "Ingen festede grafer" melding når profil er tom

### B4. localStorage-migrering
- [ ] Ved første login: sjekk localStorage for eksisterende pins
- [ ] Hvis pins finnes: kall `POST /api/dashboard/pins/migrate-local`
- [ ] Slett localStorage-nøkkel etter vellykket migrering
- [ ] Vis migreringsstatus til bruker (valgfritt)

### B5. Admin-panel (MVP)
- [ ] Admin-seksjon i UI (ny fane eller seksjon i Oversikt)
- [ ] Vis brukerliste med roller
- [ ] Legg til ny bruker (navn, e-post, rolle)
- [ ] Vis profilliste
- [ ] Opprett ny profil (navn, beskrivelse)
- [ ] Slett profil

---

## Fase C: Opprydding og kvalitet

### C1. Fjern gammel kode
- [ ] Fjern `PINNED_KEY` konstant og localStorage-logikk fra `app.js`
- [ ] Fjern `DASHBOARD_PRESETS` fra `app.js`
- [ ] Fjern hardkodede `<option>`-verdier fra `#dashboard-preset` i `index.html`
- [ ] Fjern analysis templates localStorage (valgfritt — kan være separat oppgave)

### C2. Feilhåndtering
- [ ] Vis feilmelding hvis API-kall feiler (pin, unpin, profiler)
- [ ] Håndter utlogget tilstand gracefullt (redirect til login)
- [ ] Håndter nettverksfeil ved pin/unpin

### C3. Dokumentasjon
- [ ] Oppdater README med informasjon om brukerroller
- [ ] Oppdater rolle-proposalen med referanse til denne endringen

---

## Implementeringsrekkefølge

```
A1 → A2 → A3 → A4 → A5 → B1 → B2 → B3 → B4 → B5 → C1 → C2 → C3
```

A1-A4 kan delvis parallelliseres. B1 er prereq for B2-B5.
Estimert arbeid: 2-3 dager for en utvikler.

---

## Risikoer og avhengigheter

| Risiko | Tiltak |
|--------|--------|
| SQLite har ingen migreringssystem — nye tabeller legges til i `init_database()` som kjører `CREATE TABLE IF NOT EXISTS` | Fungerer for nye tabeller, men krever manuell håndtering ved skjemaendringer. Vurder Alembic på sikt. |
| Ingen ekte auth — cookie-basert "login" er usikker | Akseptabelt for intern PoC. Flagg tydelig at dette er midlertidig. Ikke eksponér sensitiv data. |
| localStorage-migrering kan feile hvis pins har ugyldig format | Wrap i try/catch, logg feil, fortsett uten migrering |
| Eksisterende tester forventer ingen auth | Legg til test-fixtures som hopper over auth, eller sett test-bruker i conftest |
