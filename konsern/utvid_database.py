"""
Utvider konsern-databasen med tabeller for:
- Oppkjøpsdata (kjøpsdato)
- Finansielle data (EBITDA, Revenue)
- Verdsettelsesoppsett (multipler per segment)
"""
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "data" / "konsern.db"


def utvid_database():
    """Legg til nye tabeller i databasen."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabell for oppkjøpsdata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oppkjop (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            selskap_id INTEGER NOT NULL,
            kjopsdato DATE,
            kommentar TEXT,
            FOREIGN KEY (selskap_id) REFERENCES selskaper(id),
            UNIQUE(selskap_id)
        )
    """)
    
    # Tabell for finansielle data (per år)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS finansiell (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            selskap_id INTEGER NOT NULL,
            aar INTEGER NOT NULL,
            ebitda REAL,
            revenue REAL,
            vekst_pct REAL,
            ebitda_margin_pct REAL,
            kommentar TEXT,
            FOREIGN KEY (selskap_id) REFERENCES selskaper(id),
            UNIQUE(selskap_id, aar)
        )
    """)
    
    # Tabell for segment-klassifisering
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS segment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            navn TEXT UNIQUE NOT NULL,
            beskrivelse TEXT,
            default_multippel REAL,
            multippel_type TEXT DEFAULT 'EBITDA'  -- 'EBITDA' eller 'REVENUE'
        )
    """)
    
    # Legg til segment på selskaper
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS selskap_segment (
            selskap_id INTEGER PRIMARY KEY,
            segment_id INTEGER,
            custom_multippel REAL,  -- overstyrer segment-default
            multippel_type TEXT,    -- overstyrer segment-default
            FOREIGN KEY (selskap_id) REFERENCES selskaper(id),
            FOREIGN KEY (segment_id) REFERENCES segment(id)
        )
    """)
    
    # Legg inn standard-segmenter
    segmenter = [
        ("F&A", "Finance & Accounting", 8.0, "EBITDA"),
        ("IT Consulting", "IT Consulting", 7.0, "EBITDA"),
        ("IT Managed Services", "IT Managed Services", 9.0, "EBITDA"),
        ("Tech", "Software/Technology", 3.0, "REVENUE"),
        ("Annet", "Øvrige selskaper", 6.0, "EBITDA"),
    ]
    
    for navn, beskr, multippel, mtype in segmenter:
        cursor.execute("""
            INSERT OR IGNORE INTO segment (navn, beskrivelse, default_multippel, multippel_type)
            VALUES (?, ?, ?, ?)
        """, (navn, beskr, multippel, mtype))
    
    conn.commit()
    
    # Vis status
    cursor.execute("SELECT navn, default_multippel, multippel_type FROM segment")
    print("Segmenter i databasen:")
    for row in cursor.fetchall():
        print(f"  {row[0]:20} {row[1]}x {row[2]}")
    
    conn.close()
    print("\nDatabase utvidet med nye tabeller.")


if __name__ == "__main__":
    utvid_database()
