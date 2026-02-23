# Design: Server-side dashboard-pins

## Databaseskjema

Tre nye tabeller legges til i `hr/database.py` sin `init_database()`:

### 1. `brukere` (users)

```sql
CREATE TABLE IF NOT EXISTS brukere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL,
    epost TEXT UNIQUE NOT NULL,
    rolle TEXT NOT NULL DEFAULT 'bruker',  -- 'admin' eller 'bruker'
    aktiv BOOLEAN DEFAULT 1,
    opprettet DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_innlogget DATETIME
);
```

Seeddata ved init:
```sql
INSERT OR IGNORE INTO brukere (navn, epost, rolle) VALUES ('Admin', 'admin@ecit.no', 'admin');
```

### 2. `dashboard_profiler` (dashboard profiles)

```sql
CREATE TABLE IF NOT EXISTS dashboard_profiler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,        -- 'hr-oversikt', 'ledelse', etc.
    navn TEXT NOT NULL,               -- 'HR-oversikt'
    beskrivelse TEXT,                 -- 'Oversikt over organisasjonen'
    opprettet_av INTEGER REFERENCES brukere(id),
    synlig_for TEXT DEFAULT 'alle',   -- 'alle', 'admin', eller kommaseparert bruker-IDer
    sortering INTEGER DEFAULT 0,     -- For å styre rekkefølge i dropdown
    opprettet DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3. `dashboard_pins` (pinned charts)

```sql
CREATE TABLE IF NOT EXISTS dashboard_pins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bruker_id INTEGER REFERENCES brukere(id),      -- NULL for profil-pins
    profil_id INTEGER REFERENCES dashboard_profiler(id),  -- NULL for "Mine grafer"
    metric TEXT NOT NULL,
    group_by TEXT NOT NULL,
    split_by TEXT,
    filter_dim TEXT,
    filter_val TEXT,
    chart_type TEXT,                  -- Eksplisitt graftype, NULL = auto
    tittel TEXT NOT NULL,
    sortering INTEGER DEFAULT 0,     -- Rekkefølge innen profil/bruker
    opprettet DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Enten bruker_id ELLER profil_id må være satt
    CHECK (bruker_id IS NOT NULL OR profil_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_pins_bruker ON dashboard_pins(bruker_id);
CREATE INDEX IF NOT EXISTS idx_pins_profil ON dashboard_pins(profil_id);
```

**Regler:**
- `bruker_id IS NOT NULL, profil_id IS NULL` → "Mine grafer" for den brukeren
- `bruker_id IS NULL, profil_id IS NOT NULL` → Tilhører en navngitt profil (synlig for alle med tilgang)
- `bruker_id IS NOT NULL, profil_id IS NOT NULL` → Brukerens personlige pin innen en profil (fremtidig)

### Migrering av hardkodede presets

Ved `init_database()`, etter tabellene er opprettet, kjøres en engangsmigring som konverterer `DASHBOARD_PRESETS` til rader i `dashboard_profiler` og `dashboard_pins`:

```python
SEED_PROFILES = [
    {
        'slug': 'hr-oversikt',
        'navn': 'HR-oversikt',
        'beskrivelse': 'Oversikt over organisasjonen',
        'pins': [
            {'metric': 'count', 'group_by': 'arbeidsland', 'chart_type': 'bar', 'tittel': 'Ansatte per land'},
            {'metric': 'count', 'group_by': 'kjonn', 'chart_type': 'pie', 'tittel': 'Kjønnsfordeling'},
            {'metric': 'count', 'group_by': 'aldersgruppe', 'chart_type': 'bar', 'tittel': 'Aldersfordeling'},
            {'metric': 'avg_tenure', 'group_by': 'avdeling', 'chart_type': 'bar', 'tittel': 'Snitt ansiennitet per avdeling'},
        ]
    },
    # ... ledelse, lonn-analyse, mangfold (tilsvarer dagens DASHBOARD_PRESETS)
]
```

---

## API-endepunkter

Ny fil: `web/routes/dashboard.py`

### Brukeridentitet

#### `GET /api/users`
Returnerer liste over alle aktive brukere (for login-dropdown).
```json
[
    {"id": 1, "navn": "Admin", "epost": "admin@ecit.no", "rolle": "admin"},
    {"id": 2, "navn": "Kari HR", "epost": "kari@ecit.no", "rolle": "bruker"}
]
```

#### `POST /api/users`
Opprett ny bruker (kun admin).
```json
{"navn": "Kari HR", "epost": "kari@ecit.no", "rolle": "bruker"}
```

#### `POST /api/auth/login`
Enkel "innlogging" — velg bruker fra dropdown. Setter cookie `user_id`.
```json
{"user_id": 2}
```
Respons setter `Set-Cookie: user_id=2; Path=/; SameSite=Strict`.

#### `GET /api/auth/me`
Returnerer innlogget bruker basert på cookie.
```json
{"id": 2, "navn": "Kari HR", "epost": "kari@ecit.no", "rolle": "bruker"}
```

### Dashboard-profiler

#### `GET /api/dashboard/profiles`
Returnerer profiler synlige for innlogget bruker + "Mine grafer" pseudo-profil.
```json
[
    {"id": null, "slug": "", "navn": "Mine grafer", "beskrivelse": "Dine personlige grafer", "editable": true},
    {"id": 1, "slug": "hr-oversikt", "navn": "HR-oversikt", "beskrivelse": "Oversikt over organisasjonen", "editable": false},
    {"id": 2, "slug": "ledelse", "navn": "Ledelse", "beskrivelse": "Nøkkeltall for ledelsen", "editable": false}
]
```
`editable` er `true` for "Mine grafer" og for profiler der bruker er admin.

#### `POST /api/dashboard/profiles` (admin)
Opprett ny profil.
```json
{"navn": "Divisjon Nord", "beskrivelse": "Dashboard for divisjon Nord", "synlig_for": "alle"}
```

#### `PUT /api/dashboard/profiles/{profile_id}` (admin)
Oppdater profil (navn, beskrivelse, synlighet).

#### `DELETE /api/dashboard/profiles/{profile_id}` (admin)
Slett profil og alle tilhørende pins.

### Pins

#### `GET /api/dashboard/pins?profile_id={id}`
Hent pins for en profil. Hvis `profile_id` er tom/null, returnerer "Mine grafer" for innlogget bruker.
```json
[
    {
        "id": 1,
        "metric": "count",
        "group_by": "arbeidsland",
        "split_by": null,
        "filter_dim": null,
        "filter_val": null,
        "chart_type": "bar",
        "tittel": "Ansatte per land",
        "sortering": 0
    }
]
```

#### `POST /api/dashboard/pins`
Opprett ny pin. Body:
```json
{
    "profile_id": null,
    "metric": "count",
    "group_by": "avdeling",
    "split_by": "kjonn",
    "filter_dim": null,
    "filter_val": null,
    "chart_type": "stacked",
    "tittel": "Avdelinger fordelt på kjønn"
}
```
- `profile_id: null` → "Mine grafer"
- `profile_id: 1` → legg til i profil 1 (krever admin)

Regler:
- Vanlig bruker kan kun pinne til `profile_id: null` (Mine grafer)
- Admin kan pinne til enhver profil
- Duplikat-sjekk: avvis hvis identisk metric+group_by+split_by+filter allerede finnes i målprofilen

#### `DELETE /api/dashboard/pins/{pin_id}`
Fjern en pin.
- Bruker kan fjerne egne "Mine grafer"-pins
- Admin kan fjerne pins fra alle profiler

#### `PUT /api/dashboard/pins/reorder`
Endre rekkefølge på pins (drag-and-drop støtte for fremtiden).
```json
{"pin_ids": [3, 1, 2]}
```

#### `POST /api/dashboard/pins/migrate-local`
Migrering av localStorage-pins til database. Frontend sender eksisterende pins:
```json
{"pins": [{"metric": "count", "group_by": "avdeling", ...}]}
```
Lagres som "Mine grafer" for innlogget bruker. Kalles automatisk ved første innlogging.

---

## Frontend-endringer

### 1. Innlogging (ny)

Ved app-start: sjekk `GET /api/auth/me`.
- Hvis ok → vis app som vanlig
- Hvis ikke innlogget → vis enkel login-modal med dropdown av brukere (`GET /api/users`)

Login-modal:
```html
<div id="login-modal" class="modal">
    <h2>Velg bruker</h2>
    <select id="login-user-select">
        <option value="">Velg...</option>
        <!-- Populeres fra /api/users -->
    </select>
    <button onclick="login()">Logg inn</button>
</div>
```

Etter login: `POST /api/auth/login` → cookie settes → modal skjules → app laster.

### 2. Pin-modal (ny) — erstatter direkte pin

Når bruker klikker pin-knappen i Analyse-fanen, åpnes en liten modal/dropdown:

```
┌──────────────────────────────┐
│  Fest graf til:              │
│  ○ Mine grafer               │
│  ○ HR-oversikt               │
│  ○ Ledelse                   │
│  ○ Lønnsanalyse              │
│  ○ Mangfold                  │
│  [Fest]  [Avbryt]            │
└──────────────────────────────┘
```

- Viser alle profiler brukeren har tilgang til å pinne til
- For vanlig bruker: kun "Mine grafer"
- For admin: alle profiler
- Default-valg: "Mine grafer"
- Etter "Fest": `POST /api/dashboard/pins` → bekreftelse → modal lukkes

### 3. Oversikt-fanen — endringer

Dashboard-preset-dropdownen (`#dashboard-preset`) populeres fra `GET /api/dashboard/profiles` i stedet for hardkodede `<option>`-verdier.

```javascript
// Erstatter hardkodede options
async function loadDashboardProfiles() {
    const profiles = await fetchData('/api/dashboard/profiles');
    const sel = document.getElementById('dashboard-preset');
    sel.innerHTML = profiles.map(p =>
        `<option value="${p.id || ''}">${p.navn}</option>`
    ).join('');
}
```

`renderDashboardCharts()` endres til å hente pins fra API:
```javascript
async function renderDashboardCharts(profileId) {
    const pins = await fetchData(`/api/dashboard/pins?profile_id=${profileId}`);
    const canEdit = /* admin, eller profileId er tom (Mine grafer) */;
    await renderPinnedCharts(pins, canEdit);
}
```

### 4. Unpin — tydeligere

- Unpin-knappen (`X`) vises alltid (ikke bare hover) for redigerbare profiler
- Kaller `DELETE /api/dashboard/pins/{pin_id}` i stedet for localStorage-fjerning
- Etter sletting: fjern DOM-element (som i dag)

### 5. Fiks: chart_type null-bug

I `pinCurrentAnalysis()` (nå i pin-modalen), lagre faktisk brukt chart type:
```javascript
const chartType = analyseChartType || suggestChartType(data, hasSplitBy).default;
```
I stedet for dagens `analyseChartType` som kan være `null`.

### 6. localStorage-migrering

Ved første innlogging (etter login, før dashboard lastes):
```javascript
const localPins = JSON.parse(localStorage.getItem('dashboard_pinned_charts') || '[]');
if (localPins.length > 0) {
    await fetch('/api/dashboard/pins/migrate-local', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pins: localPins})
    });
    localStorage.removeItem('dashboard_pinned_charts');
}
```

### 7. Admin-panel (enkel)

Kun synlig for admin-brukere. Kan være en enkel seksjon i Oversikt eller egen fane:

- Liste over profiler med redigering (navn, beskrivelse)
- Opprett ny profil
- Slett profil
- Brukerstyring (legg til/fjern brukere, endre rolle)

For MVP kan dette være en enkel tabellvisning med knappper, ikke en full CRUD-app.

---

## Endringer i eksisterende filer

### `hr/database.py`
- Legg til 3 nye tabeller i `init_database()`
- Legg til seed-funksjon for standard-profiler
- Legg til indekser

### `web/app.py`
- Registrer ny `dashboard_router`
- Legg til enkel auth-middleware (les cookie, sett `request.state.user`)

### `web/routes/dashboard.py` (NY FIL)
- Alle nye endepunkter (users, auth, profiles, pins)

### `web/static/js/app.js`
- Fjern `PINNED_KEY`, `DASHBOARD_PRESETS`, `getPinnedCharts()`, `savePinnedCharts()`
- Fjern `pinCurrentAnalysis()` direkte localStorage-logikk
- Erstatt med API-kall
- Legg til pin-modal
- Legg til login-flyt
- Oppdater `renderDashboardCharts()` til å bruke API
- Oppdater `unpinChart()` til å bruke API

### `web/templates/index.html`
- Legg til login-modal HTML
- Legg til pin-modal HTML
- Fjern hardkodede preset-options fra `#dashboard-preset`

### `web/static/css/style.css`
- Stiler for login-modal
- Stiler for pin-modal
- Synlig unpin-knapp (ikke bare hover)

### `tests/test_api.py`
- Nye tester for alle dashboard-endepunkter
- Test rollebasert tilgang (admin vs bruker)
- Test pin CRUD
- Test localStorage-migrering

---

## Sekvensdiagram: Pin-flyt

```
Bruker                  Frontend              API                  Database
  │                       │                     │                     │
  ├─ Klikk pin-knapp ──▶ │                     │                     │
  │                       ├─ GET /profiles ───▶ │                     │
  │                       │◀── profiler ───────┤                     │
  │                       ├─ Vis pin-modal ──▶  │                     │
  │◀── Velg profil ──────┤                     │                     │
  ├─ Klikk "Fest" ──────▶│                     │                     │
  │                       ├─ POST /pins ──────▶ │                     │
  │                       │                     ├─ Sjekk auth ──────▶│
  │                       │                     ├─ Sjekk duplikat ──▶│
  │                       │                     ├─ INSERT pin ──────▶│
  │                       │◀── 201 Created ────┤                     │
  │                       ├─ Vis bekreftelse ─▶ │                     │
  │◀── Modal lukkes ─────┤                     │                     │
```

## Sekvensdiagram: Dashboard-lasting

```
Bruker                  Frontend              API                  Database
  │                       │                     │                     │
  ├─ Åpne Oversikt ─────▶│                     │                     │
  │                       ├─ GET /profiles ───▶ │                     │
  │                       │◀── profiler ───────┤                     │
  │                       ├─ Populer dropdown   │                     │
  │                       ├─ GET /pins?pid=X ─▶ │                     │
  │                       │◀── pins ───────────┤                     │
  │                       │                     │                     │
  │                       │ For hver pin:       │                     │
  │                       ├─ GET /analyze?... ─▶│                     │
  │                       │◀── data ───────────┤                     │
  │                       ├─ Render graf        │                     │
  │◀── Dashboard vist ──┤                     │                     │
```
