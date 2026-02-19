"""
Import Excel-matrise til SQLite database for konsernstruktur.
"""
import pandas as pd
import sqlite3
from pathlib import Path

# Paths
EXCEL_FILE = Path(__file__).parent.parent / "data" / "Cost price subsidiaries 31012026 vPF-kopi.xlsx"
DB_FILE = Path(__file__).parent.parent / "data" / "konsern.db"


def parse_ownership_matrix(excel_file: Path, sheet_name: str = "All Co") -> pd.DataFrame:
    """
    Parser eierskapsmatrisen fra Excel-filen.
    Returnerer en "long format" DataFrame med kolonner:
    - eier_kode: Kode for eierselskap
    - eier_navn: Navn på eierselskap
    - eid_kode: Kode for selskap som eies
    - eid_navn: Navn på selskap som eies
    - investering: Bokført investering (cost price)
    """
    # Les hele arket
    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
    
    # Strukturen er:
    # Rad 7: "Company", NaN, kode1, kode2, kode3, ...
    # Rad 8: "Company", NaN, navn1, navn2, navn3, ...
    # Rad 9+: eid_kode, eid_navn, verdi1, verdi2, verdi3, ...
    kode_rad = 7
    navn_rad = 8
    data_start = 9
    
    # Hent eierselskap-koder og navn (fra kolonner fra index 2 og utover)
    eier_koder = df.iloc[kode_rad, 2:].tolist()
    eier_navn = df.iloc[navn_rad, 2:].tolist()
    
    # Bygg eierselskap-mapping
    eierselskaper = {}
    for i, (kode, navn) in enumerate(zip(eier_koder, eier_navn)):
        if pd.notna(kode) and pd.notna(navn):
            eierselskaper[i + 2] = {"kode": str(kode).strip(), "navn": str(navn).strip()}
    
    print(f"Funnet {len(eierselskaper)} eierselskaper")
    
    # Parse data-radene
    eierskapsdata = []
    
    for row_idx in range(data_start, len(df)):
        eid_kode = df.iloc[row_idx, 0]
        eid_navn = df.iloc[row_idx, 1]
        
        if pd.isna(eid_kode) or pd.isna(eid_navn):
            continue
            
        eid_kode = str(eid_kode).strip()
        eid_navn = str(eid_navn).strip()
        
        # Sjekk hver eierkolonne
        for col_idx, eierinfo in eierselskaper.items():
            verdi = df.iloc[row_idx, col_idx]
            
            if pd.notna(verdi) and verdi != 0:
                try:
                    investering = float(verdi)
                    if investering != 0:
                        eierskapsdata.append({
                            "eier_kode": eierinfo["kode"],
                            "eier_navn": eierinfo["navn"],
                            "eid_kode": eid_kode,
                            "eid_navn": eid_navn,
                            "investering": investering
                        })
                except (ValueError, TypeError):
                    pass  # Ikke et tall, hopp over
    
    return pd.DataFrame(eierskapsdata)


def create_database(df: pd.DataFrame, db_file: Path):
    """Oppretter SQLite database fra DataFrame."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Opprett tabeller
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS selskaper (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT UNIQUE NOT NULL,
            navn TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eierskap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eier_id INTEGER NOT NULL,
            eid_id INTEGER NOT NULL,
            investering REAL,
            FOREIGN KEY (eier_id) REFERENCES selskaper(id),
            FOREIGN KEY (eid_id) REFERENCES selskaper(id),
            UNIQUE(eier_id, eid_id)
        )
    """)
    
    # Samle alle unike selskaper
    alle_selskaper = {}
    
    # Fra eiere
    for _, row in df.iterrows():
        kode = row["eier_kode"]
        if kode not in alle_selskaper:
            alle_selskaper[kode] = row["eier_navn"]
    
    # Fra eide selskaper
    for _, row in df.iterrows():
        kode = row["eid_kode"]
        if kode not in alle_selskaper:
            alle_selskaper[kode] = row["eid_navn"]
    
    # Sett inn selskaper
    selskap_id_map = {}
    for kode, navn in alle_selskaper.items():
        cursor.execute(
            "INSERT OR IGNORE INTO selskaper (kode, navn) VALUES (?, ?)",
            (kode, navn)
        )
        cursor.execute("SELECT id FROM selskaper WHERE kode = ?", (kode,))
        selskap_id_map[kode] = cursor.fetchone()[0]
    
    # Sett inn eierskapsforhold
    for _, row in df.iterrows():
        eier_id = selskap_id_map[row["eier_kode"]]
        eid_id = selskap_id_map[row["eid_kode"]]
        investering = row["investering"]
        
        cursor.execute("""
            INSERT OR REPLACE INTO eierskap (eier_id, eid_id, investering)
            VALUES (?, ?, ?)
        """, (eier_id, eid_id, investering))
    
    conn.commit()
    
    # Vis statistikk
    cursor.execute("SELECT COUNT(*) FROM selskaper")
    antall_selskaper = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM eierskap")
    antall_eierskap = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(investering) FROM eierskap")
    total_investering = cursor.fetchone()[0] or 0
    
    print(f"Database opprettet: {db_file}")
    print(f"  Antall selskaper: {antall_selskaper}")
    print(f"  Antall eierskapsforhold: {antall_eierskap}")
    print(f"  Total investering: {total_investering:,.2f}")
    
    conn.close()


def main():
    print(f"Leser Excel-fil: {EXCEL_FILE}")
    
    if not EXCEL_FILE.exists():
        print(f"FEIL: Finner ikke fil: {EXCEL_FILE}")
        return
    
    # Parse matrisen
    df = parse_ownership_matrix(EXCEL_FILE)
    print(f"Funnet {len(df)} eierskapsforhold")
    
    if len(df) > 0:
        print("\nEksempel på data:")
        print(df.head(10).to_string(index=False))
    
    # Opprett database
    create_database(df, DB_FILE)


if __name__ == "__main__":
    main()
