"""
Anonymiserer Excel-fil med eierstruktur.
Beholder strukturen, erstatter navn med koder og tall med tilfeldige verdier.

Bruk: python3 anonymiser.py input.xlsx output.xlsx
"""
import pandas as pd
import random
import string
import sys
from pathlib import Path


def generer_kode(lengde=4):
    """Generer tilfeldig kode."""
    return ''.join(random.choices(string.ascii_uppercase, k=lengde))


def anonymiser_excel(input_fil, output_fil):
    """Les Excel, anonymiser og lagre ny fil. Håndterer alle ark."""
    
    # Les alle ark fra Excel
    alle_ark = pd.read_excel(input_fil, header=None, sheet_name=None)
    
    print(f"  Fant {len(alle_ark)} ark: {', '.join(alle_ark.keys())}")
    
    # Lag mapping for konsistente erstatninger (delt på tvers av ark)
    tekst_mapping = {}
    kode_teller = 1
    
    def anonymiser_celle(verdi):
        nonlocal kode_teller
        
        if pd.isna(verdi):
            return verdi
        
        # Hvis tall - erstatt med tilfeldig verdi (behold størrelsesorden)
        if isinstance(verdi, (int, float)):
            if verdi == 0:
                return 0
            # Behold ca samme størrelsesorden, men randomiser
            faktor = random.uniform(0.5, 2.0)
            return round(verdi * faktor, 2)
        
        # Hvis tekst - erstatt med anonymisert versjon
        if isinstance(verdi, str):
            verdi_stripped = verdi.strip()
            
            # Behold tomme strenger
            if not verdi_stripped:
                return verdi
            
            # Behold korte koder (3-6 tegn, bare bokstaver) - disse er allerede koder
            if len(verdi_stripped) <= 6 and verdi_stripped.isalpha():
                if verdi_stripped not in tekst_mapping:
                    tekst_mapping[verdi_stripped] = f"K{kode_teller:03d}"
                    kode_teller += 1
                return tekst_mapping[verdi_stripped]
            
            # Erstatt lengre tekst (selskapsnavn)
            if verdi_stripped not in tekst_mapping:
                tekst_mapping[verdi_stripped] = f"Selskap {kode_teller:03d} AS"
                kode_teller += 1
            return tekst_mapping[verdi_stripped]
        
        return verdi
    
    # Anonymiser alle ark
    anonymiserte_ark = {}
    for ark_navn, df in alle_ark.items():
        anonymiserte_ark[ark_navn] = df.map(anonymiser_celle)
        print(f"  - {ark_navn}: {df.shape[0]} rader × {df.shape[1]} kolonner")
    
    # Lagre alle ark til ny fil
    with pd.ExcelWriter(output_fil, engine='openpyxl') as writer:
        for ark_navn, df in anonymiserte_ark.items():
            df.to_excel(writer, sheet_name=ark_navn, index=False, header=False)
    
    print(f"\n✓ Anonymisert fil lagret: {output_fil}")
    print(f"  - {len(tekst_mapping)} unike tekster erstattet")
    print(f"  - Alle tall randomisert (±50%)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Bruk: python3 anonymiser.py <input.xlsx> [output.xlsx eller mappe]")
        print("Eksempel: python3 anonymiser.py 'sensitiv_fil.xlsx' 'testdata.xlsx'")
        print("Eksempel: python3 anonymiser.py 'sensitiv_fil.xlsx' ~/Desktop/")
        sys.exit(1)
    
    input_fil = Path(sys.argv[1])
    
    if not input_fil.exists():
        print(f"Feil: Finner ikke {input_fil}")
        sys.exit(1)
    
    # Hvis output er oppgitt
    if len(sys.argv) >= 3:
        output_sti = Path(sys.argv[2])
        
        # Hvis output er en mappe, generer filnavn
        if output_sti.is_dir():
            output_fil = output_sti / f"{input_fil.stem}_anon.xlsx"
        else:
            output_fil = output_sti
    else:
        # Ingen output oppgitt - lag fil i samme mappe som input
        output_fil = input_fil.parent / f"{input_fil.stem}_anon.xlsx"
    
    anonymiser_excel(input_fil, output_fil)

