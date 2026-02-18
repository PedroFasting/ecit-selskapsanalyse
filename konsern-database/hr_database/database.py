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
DEFAULT_DB_PATH = Path(_env_db_path) if _env_db_path else Path(__file__).parent.parent / "ansatte.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Opprett tilkobling til databasen."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Gir dict-lignende rader
    return conn


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
