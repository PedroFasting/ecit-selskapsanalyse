"""
Database-skjema og tilkoblingslogikk for HR-databasen.
Håndterer SQLite-database for ansattdata.
"""

import sqlite3
from pathlib import Path
from datetime import date, datetime
from typing import Optional
import os

# Standard database-plassering — kan overstyres med DB_PATH miljøvariabel
_env_db_path = os.environ.get("DB_PATH")
DEFAULT_DB_PATH = Path(_env_db_path) if _env_db_path else Path(__file__).parent.parent / "data" / "ansatte.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Opprett tilkobling til databasen."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Gir dict-lignende rader
    return conn


# Standard dashboard-profiler (erstatter hardkodede DASHBOARD_PRESETS i JS)
_SEED_PROFILES = [
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
    {
        'slug': 'ledelse',
        'navn': 'Ledelse',
        'beskrivelse': 'Nøkkeltall for ledelsen',
        'pins': [
            {'metric': 'count', 'group_by': 'arbeidsland', 'chart_type': 'bar', 'tittel': 'Ansatte per land'},
            {'metric': 'sum_salary', 'group_by': 'arbeidsland', 'chart_type': 'bar', 'tittel': 'Lønnsmasse per land'},
            {'metric': 'pct_leaders', 'group_by': 'avdeling', 'chart_type': 'bar', 'tittel': 'Lederandel per avdeling'},
            {'metric': 'count', 'group_by': 'avdeling', 'split_by': 'kjonn', 'chart_type': 'stacked', 'tittel': 'Avdelinger fordelt på kjønn'},
        ]
    },
    {
        'slug': 'lonn-analyse',
        'navn': 'Lønnsanalyse',
        'beskrivelse': 'Lønnsoversikt på tvers',
        'pins': [
            {'metric': 'avg_salary', 'group_by': 'avdeling', 'chart_type': 'bar', 'tittel': 'Snittlønn per avdeling'},
            {'metric': 'avg_salary', 'group_by': 'arbeidsland', 'chart_type': 'bar', 'tittel': 'Snittlønn per land'},
            {'metric': 'avg_salary', 'group_by': 'kjonn', 'chart_type': 'bar', 'tittel': 'Snittlønn per kjønn'},
        ]
    },
    {
        'slug': 'mangfold',
        'navn': 'Mangfold',
        'beskrivelse': 'Kjønnsbalanse, nasjonalitet og aldersfordeling',
        'pins': [
            {'metric': 'pct_female', 'group_by': 'avdeling', 'chart_type': 'bar', 'tittel': 'Andel kvinner per avdeling'},
            {'metric': 'count', 'group_by': 'nasjonalitet', 'chart_type': 'pie', 'tittel': 'Nasjonalitetsfordeling'},
            {'metric': 'count', 'group_by': 'aldersgruppe', 'split_by': 'kjonn', 'chart_type': 'stacked', 'tittel': 'Alder fordelt på kjønn'},
        ]
    },
]


def _seed_defaults(cursor: sqlite3.Cursor) -> None:
    """Opprett standard admin-bruker og dashboard-profiler hvis de ikke finnes."""
    # Admin-bruker
    cursor.execute("SELECT COUNT(*) FROM brukere")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO brukere (navn, epost, rolle) VALUES (?, ?, ?)",
            ("Admin", "admin@ecit.no", "admin"),
        )

    # Dashboard-profiler
    cursor.execute("SELECT COUNT(*) FROM dashboard_profiler")
    if cursor.fetchone()[0] == 0:
        for idx, profile in enumerate(_SEED_PROFILES):
            cursor.execute(
                "INSERT INTO dashboard_profiler (slug, navn, beskrivelse, sortering) VALUES (?, ?, ?, ?)",
                (profile['slug'], profile['navn'], profile['beskrivelse'], idx),
            )
            profil_id = cursor.lastrowid
            for pin_idx, pin in enumerate(profile['pins']):
                cursor.execute(
                    """INSERT INTO dashboard_pins
                       (profil_id, metric, group_by, split_by, chart_type, tittel, sortering)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (profil_id, pin['metric'], pin['group_by'],
                     pin.get('split_by'), pin['chart_type'],
                     pin['tittel'], pin_idx),
                )


def init_database(db_path: Optional[Path] = None) -> None:
    """
    Opprett databaseskjema hvis det ikke eksisterer.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Hovedtabell for ansatte
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ansatte (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Grunnleggende informasjon
        fornavn TEXT,
        etternavn TEXT,
        epost_arbeid TEXT,
        jobbtelefon TEXT,
        kjonn TEXT,
        fodselsdato DATE,
        alder INTEGER,
        fodested TEXT,
        nasjonalitet TEXT,
        personnummer TEXT,  -- SENSITIV
        
        -- Bank (SENSITIV)
        bic TEXT,
        iban TEXT,
        clearingnummer TEXT,
        bankkontonummer TEXT,
        
        -- Kontakt
        nodtelefon TEXT,
        sykekasse TEXT,
        helseforsikring_type TEXT,
        
        -- Adresse
        co TEXT,
        adresse TEXT,
        postkode TEXT,
        sted TEXT,
        land TEXT,
        
        -- Ansettelse
        kostsenter TEXT,
        juridisk_selskap TEXT,
        arbeidsland TEXT,
        medarbeidernummer TEXT UNIQUE,
        lovlig_ansettelsesdato DATE,
        ansettelsens_startdato DATE,
        slutdato_lovlig_ansettelse DATE,
        slutdato_ansettelse DATE,
        ansettelsetype TEXT,
        arbeidstid_per_uke REAL,
        heltid_per_uke REAL,
        type_arbeidstid TEXT,
        ekstern TEXT,
        inkludere_antall_ansatte TEXT,
        ansettelsegruppe TEXT,
        oppsigelsesarsak TEXT,
        lonnutbetaling TEXT,
        
        -- Stilling
        tittel TEXT,
        ledere TEXT,
        avdeling TEXT,
        rolle TEXT,
        jobbfamilie TEXT,
        ansettelsesniva TEXT,
        er_leder TEXT,
        startdato_posisjon DATE,
        arbeidssted TEXT,
        
        -- Lønn
        lonn REAL,
        
        -- Metadata
        importert_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
        kilde_fil TEXT,
        
        -- Aktiv-status (oppdateres ved import)
        er_aktiv BOOLEAN DEFAULT 1
    )
    """)
    
    # Indekser for raske oppslag
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_land ON ansatte(land)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_arbeidsland ON ansatte(arbeidsland)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_juridisk_selskap ON ansatte(juridisk_selskap)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_avdeling ON ansatte(avdeling)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_slutdato ON ansatte(slutdato_ansettelse)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_startdato ON ansatte(ansettelsens_startdato)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ansatte_alder ON ansatte(alder)")
    
    # Tabell for importhistorikk
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS import_logg (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filnavn TEXT,
        importert_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
        antall_rader INTEGER,
        status TEXT
    )
    """)

    # --- Dashboard-system: brukere, profiler, pins ---

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS brukere (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        navn TEXT NOT NULL,
        epost TEXT UNIQUE NOT NULL,
        rolle TEXT NOT NULL DEFAULT 'bruker',
        aktiv BOOLEAN DEFAULT 1,
        opprettet DATETIME DEFAULT CURRENT_TIMESTAMP,
        sist_innlogget DATETIME
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_profiler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        navn TEXT NOT NULL,
        beskrivelse TEXT,
        opprettet_av INTEGER REFERENCES brukere(id),
        synlig_for TEXT DEFAULT 'alle',
        sortering INTEGER DEFAULT 0,
        opprettet DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_pins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bruker_id INTEGER REFERENCES brukere(id),
        profil_id INTEGER REFERENCES dashboard_profiler(id),
        metric TEXT NOT NULL,
        group_by TEXT NOT NULL,
        split_by TEXT,
        filter_dim TEXT,
        filter_val TEXT,
        chart_type TEXT,
        tittel TEXT NOT NULL,
        sortering INTEGER DEFAULT 0,
        opprettet DATETIME DEFAULT CURRENT_TIMESTAMP,
        CHECK (bruker_id IS NOT NULL OR profil_id IS NOT NULL)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pins_bruker ON dashboard_pins(bruker_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pins_profil ON dashboard_pins(profil_id)")

    # Seed standard-profiler og admin-bruker (kun hvis tabellene er tomme)
    _seed_defaults(cursor)

    conn.commit()
    conn.close()
    print(f"Database initialisert: {db_path or DEFAULT_DB_PATH}")


def reset_database(db_path: Optional[Path] = None) -> None:
    """Slett og opprett databasen på nytt. ADVARSEL: Sletter alle data!"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    if db_path.exists():
        os.remove(db_path)
        print(f"Slettet eksisterende database: {db_path}")
    
    init_database(db_path)


if __name__ == "__main__":
    init_database()
