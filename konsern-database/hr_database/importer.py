"""
Excel-import modul for HR-data.
Leser VerismoHR-eksporter og lagrer i database.
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
import numpy as np

from .database import get_connection, init_database, DEFAULT_DB_PATH


# Mapping fra Excel-kolonner til database-kolonner
COLUMN_MAPPING = {
    'Fornavn': 'fornavn',
    'Etternavn': 'etternavn',
    'E-post arbeid': 'epost_arbeid',
    'Jobbtelefon': 'jobbtelefon',
    'Kjønn': 'kjonn',
    'Fødelsedato': 'fodselsdato',
    'Alder': 'alder',
    'Fødested': 'fodested',
    'Nasjonalitet': 'nasjonalitet',
    'Fødsel og personnummer': 'personnummer',
    'BIC': 'bic',
    'IBAN': 'iban',
    'Clearingnummer': 'clearingnummer',
    'Bankkontonummer': 'bankkontonummer',
    'Nødtelefon': 'nodtelefon',
    'Sykekasse': 'sykekasse',
    'Type of health insurance': 'helseforsikring_type',
    'personnummer': 'personnummer',
    'c/o': 'co',
    'Adresse': 'adresse',
    'Postkode': 'postkode',
    'Sted': 'sted',
    'Land': 'land',
    'Kostsenter': 'kostsenter',
    'Juridisk selskap': 'juridisk_selskap',
    'Land ': 'arbeidsland',  # NB: har mellomrom etter
    'Medarbeidernummer': 'medarbeidernummer',
    'Lovlig ansettelsesdato': 'lovlig_ansettelsesdato',
    'Ansettelsens startdato': 'ansettelsens_startdato',
    'Slutdato for lovlig ansettelse': 'slutdato_lovlig_ansettelse',
    'Slutdato for ansettelse': 'slutdato_ansettelse',
    'Ansettelsetype': 'ansettelsetype',
    'Arbeidstid per uke': 'arbeidstid_per_uke',
    'Heltid per uke': 'heltid_per_uke',
    'Type av arbeidstid': 'type_arbeidstid',
    'Ekstern': 'ekstern',
    'Inkludere i antallet ansatte': 'inkludere_antall_ansatte',
    'Ansettelsegruppe': 'ansettelsegruppe',
    'Årsak til oppsigelse av arbeidsforhold': 'oppsigelsesarsak',
    'Lønnutbetaling': 'lonnutbetaling',
    'Tittel': 'tittel',
    'Ledere': 'ledere',
    'Avdeling': 'avdeling',
    'Rolle': 'rolle',
    'Jobbfamilie': 'jobbfamilie',
    'Ansettelsenivå': 'ansettelsesniva',
    'Er leder': 'er_leder',
    'Lønn': 'lonn',
    'Startdato for posisjon': 'startdato_posisjon',
    'Sted ': 'arbeidssted',  # NB: har mellomrom etter
}


def parse_date(value) -> Optional[str]:
    """
    Konverter diverse datoformater til ISO-format (YYYY-MM-DD).
    """
    if pd.isna(value) or value is None:
        return None
    
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        
        # Prøv forskjellige formater
        formats = [
            '%d.%m.%Y',  # 06.02.2017
            '%Y-%m-%d',  # 2017-02-06
            '%d/%m/%Y',  # 06/02/2017
            '%Y/%m/%d',  # 2017/02/06
            '%d-%m-%Y',  # 06-02-2017
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        print(f"  Advarsel: Kunne ikke parse dato: '{value}'")
        return None
    
    return None


def clean_value(value):
    """Rens en verdi for databaselagring."""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def import_excel(
    filepath: str,
    db_path: Optional[Path] = None,
    clear_existing: bool = False,
    verbose: bool = True
) -> int:
    """
    Importer ansattdata fra Excel-fil til database.
    
    Args:
        filepath: Sti til Excel-filen
        db_path: Valgfri database-sti
        clear_existing: Slett eksisterende data før import
        verbose: Vis detaljert output
        
    Returns:
        Antall importerte rader
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Finner ikke fil: {filepath}")
    
    if verbose:
        print(f"Importerer fra: {filepath.name}")
    
    # Les Excel med header på rad 1 (0-indeksert)
    df = pd.read_excel(filepath, header=1)
    
    if verbose:
        print(f"  Leste {len(df)} rader fra Excel")
    
    # Initialiser database om nødvendig
    init_database(db_path)
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if clear_existing:
        cursor.execute("DELETE FROM ansatte")
        if verbose:
            print("  Slettet eksisterende data")
    
    # Forbered kolonner for innsetting
    db_columns = list(COLUMN_MAPPING.values())
    # Fjern duplikater (personnummer finnes to ganger i mapping)
    db_columns = list(dict.fromkeys(db_columns))
    db_columns.append('kilde_fil')
    db_columns.append('er_aktiv')
    
    date_columns = [
        'fodselsdato', 'lovlig_ansettelsesdato', 'ansettelsens_startdato',
        'slutdato_lovlig_ansettelse', 'slutdato_ansettelse', 'startdato_posisjon'
    ]
    
    placeholders = ', '.join(['?' for _ in db_columns])
    column_names = ', '.join(db_columns)
    
    insert_sql = f"INSERT OR REPLACE INTO ansatte ({column_names}) VALUES ({placeholders})"
    
    imported = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            values = []
            slutdato = None
            
            for db_col in db_columns[:-2]:  # Alle unntatt kilde_fil og er_aktiv
                # Finn Excel-kolonnenavn
                excel_col = None
                for exc, dbc in COLUMN_MAPPING.items():
                    if dbc == db_col:
                        excel_col = exc
                        break
                
                if excel_col and excel_col in row.index:
                    value = row[excel_col]
                    value = clean_value(value)
                    
                    # Parse datoer
                    if db_col in date_columns and value is not None:
                        value = parse_date(value)
                    
                    # Lagre slutdato for er_aktiv beregning
                    if db_col == 'slutdato_ansettelse':
                        slutdato = value
                    
                    values.append(value)
                else:
                    values.append(None)
            
            # Legg til kilde_fil
            values.append(filepath.name)
            
            # Beregn er_aktiv
            if slutdato is None:
                er_aktiv = True
            else:
                try:
                    slutdato_dt = datetime.strptime(slutdato, '%Y-%m-%d').date()
                    er_aktiv = slutdato_dt > datetime.now().date()
                except (ValueError, TypeError):
                    er_aktiv = True
            values.append(er_aktiv)
            
            cursor.execute(insert_sql, values)
            imported += 1
            
        except Exception as e:
            errors += 1
            if verbose:
                print(f"  Feil på rad {idx + 2}: {e}")
    
    # Logg importen
    cursor.execute(
        "INSERT INTO import_logg (filnavn, antall_rader, status) VALUES (?, ?, ?)",
        (filepath.name, imported, 'OK' if errors == 0 else f'{errors} feil')
    )
    
    conn.commit()
    conn.close()
    
    if verbose:
        print(f"  Importert: {imported} rader")
        if errors > 0:
            print(f"  Feil: {errors}")
    
    return imported


def list_imports(db_path: Optional[Path] = None) -> list:
    """List alle tidligere importer."""
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filnavn, importert_dato, antall_rader, status 
            FROM import_logg 
            ORDER BY importert_dato DESC
        """)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]
    except sqlite3.OperationalError:
        return []


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        import_excel(sys.argv[1])
    else:
        print("Bruk: python -m hr_database.importer <excel-fil>")
