"""
Interaktivt søkeverktøy for konsernstruktur-database.
Kjør: python3 sok.py
"""
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "data" / "konsern.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def format_belop(belop):
    """Formater beløp i millioner."""
    if belop >= 1_000_000:
        return f"{belop/1_000_000:,.1f} MNOK"
    elif belop >= 1_000:
        return f"{belop/1_000:,.1f} KNOK"
    else:
        return f"{belop:,.0f} NOK"


def sok_selskap(query):
    """Søk etter selskap på navn eller kode. Prioriterer eksakt kode-match."""
    conn = get_db()
    resultater = conn.execute("""
        SELECT id, kode, navn 
        FROM selskaper 
        WHERE kode LIKE ? OR navn LIKE ?
        ORDER BY 
            CASE WHEN UPPER(kode) = UPPER(?) THEN 0 ELSE 1 END,
            navn
    """, (f"%{query}%", f"%{query}%", query)).fetchall()
    conn.close()
    return resultater


def vis_eiere(selskap_id):
    """Vis hvem som eier et selskap."""
    conn = get_db()
    
    selskap = conn.execute(
        "SELECT kode, navn FROM selskaper WHERE id = ?", 
        (selskap_id,)
    ).fetchone()
    
    eiere = conn.execute("""
        SELECT s.kode, s.navn, e.investering
        FROM eierskap e
        JOIN selskaper s ON s.id = e.eier_id
        WHERE e.eid_id = ?
        ORDER BY e.investering DESC
    """, (selskap_id,)).fetchall()
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"EIERE AV: {selskap['navn']} ({selskap['kode']})")
    print(f"{'='*60}")
    
    if not eiere:
        print("  Ingen eiere funnet (mulig toppselskap)")
    else:
        total = 0
        for e in eiere:
            print(f"  {e['kode']:8} {e['navn'][:35]:36} {format_belop(e['investering']):>15}")
            total += e['investering']
        print(f"  {'-'*55}")
        print(f"  {'SUM':8} {' ':36} {format_belop(total):>15}")
    
    return eiere


def vis_datterselskaper(selskap_id):
    """Vis selskaper eid av dette selskapet."""
    conn = get_db()
    
    selskap = conn.execute(
        "SELECT kode, navn FROM selskaper WHERE id = ?", 
        (selskap_id,)
    ).fetchone()
    
    datter = conn.execute("""
        SELECT s.id, s.kode, s.navn, e.investering
        FROM eierskap e
        JOIN selskaper s ON s.id = e.eid_id
        WHERE e.eier_id = ?
        ORDER BY e.investering DESC
    """, (selskap_id,)).fetchall()
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"SELSKAPER EID AV: {selskap['navn']} ({selskap['kode']})")
    print(f"{'='*60}")
    
    if not datter:
        print("  Ingen datterselskaper funnet")
    else:
        total = 0
        for d in datter:
            print(f"  {d['kode']:8} {d['navn'][:35]:36} {format_belop(d['investering']):>15}")
            total += d['investering']
        print(f"  {'-'*55}")
        print(f"  {'SUM':8} {' ':36} {format_belop(total):>15}")
    
    return datter


def vis_konsernstruktur(selskap_id, nivå=0, visited=None, direkte_sum=None):
    """Vis hele konsernstrukturen nedover."""
    if visited is None:
        visited = set()
    
    if selskap_id in visited:
        return
    visited.add(selskap_id)
    
    conn = get_db()
    
    selskap = conn.execute(
        "SELECT kode, navn FROM selskaper WHERE id = ?", 
        (selskap_id,)
    ).fetchone()
    
    datter = conn.execute("""
        SELECT s.id, s.kode, s.navn, e.investering
        FROM eierskap e
        JOIN selskaper s ON s.id = e.eid_id
        WHERE e.eier_id = ?
        ORDER BY e.investering DESC
    """, (selskap_id,)).fetchall()
    
    conn.close()
    
    if nivå == 0:
        print(f"\n{'='*70}")
        print(f"KONSERNSTRUKTUR FRA: {selskap['navn']} ({selskap['kode']})")
        print(f"{'='*70}")
        # Beregn kun direkte investeringer fra toppselskapet
        direkte_sum = sum(d['investering'] for d in datter)
    
    for d in datter:
        prefix = "  " * nivå + "├─ " if nivå > 0 else ""
        print(f"{prefix}{d['kode']:8} {d['navn'][:40]:41} {format_belop(d['investering']):>15}")
        # Rekursivt vis datterselskaper (uten å summere)
        vis_konsernstruktur(d['id'], nivå + 1, visited, direkte_sum)
    
    if nivå == 0 and datter:
        print(f"{'='*70}")
        print(f"DIREKTE INVESTERING: {format_belop(direkte_sum)}")


def vis_eierkjede(selskap_id, nivå=0, visited=None):
    """Vis eierkjeden oppover."""
    if visited is None:
        visited = set()
    
    if selskap_id in visited:
        return
    visited.add(selskap_id)
    
    conn = get_db()
    
    selskap = conn.execute(
        "SELECT kode, navn FROM selskaper WHERE id = ?", 
        (selskap_id,)
    ).fetchone()
    
    eiere = conn.execute("""
        SELECT s.id, s.kode, s.navn, e.investering
        FROM eierskap e
        JOIN selskaper s ON s.id = e.eier_id
        WHERE e.eid_id = ?
        ORDER BY e.investering DESC
    """, (selskap_id,)).fetchall()
    
    conn.close()
    
    if nivå == 0:
        print(f"\n{'='*60}")
        print(f"EIERKJEDE FOR: {selskap['navn']} ({selskap['kode']})")
        print(f"{'='*60}")
        print(f"  → {selskap['kode']:8} {selskap['navn']}")
    
    for e in eiere:
        prefix = "  " * (nivå + 1) + "↑ "
        print(f"{prefix}{e['kode']:8} {e['navn'][:40]} ({format_belop(e['investering'])})")
        vis_eierkjede(e['id'], nivå + 1, visited)


def vis_statistikk():
    """Vis overordnet statistikk."""
    conn = get_db()
    
    antall_selskaper = conn.execute("SELECT COUNT(*) FROM selskaper").fetchone()[0]
    antall_eierskap = conn.execute("SELECT COUNT(*) FROM eierskap").fetchone()[0]
    
    # Finn toppselskaper (de som ikke eies av noen)
    toppselskaper = conn.execute("""
        SELECT s.id, s.kode, s.navn
        FROM selskaper s
        WHERE s.id NOT IN (SELECT eid_id FROM eierskap)
        AND s.id IN (SELECT eier_id FROM eierskap)
    """).fetchall()
    
    # Finn bunnselskaper (de som ikke eier noen andre)
    bunnselskaper = conn.execute("""
        SELECT COUNT(*) FROM selskaper s
        WHERE s.id NOT IN (SELECT eier_id FROM eierskap)
        AND s.id IN (SELECT eid_id FROM eierskap)
    """).fetchone()[0]
    
    print(f"\n{'='*60}")
    print("STATISTIKK")
    print(f"{'='*60}")
    print(f"  Antall selskaper:        {antall_selskaper}")
    print(f"  Antall eierskapsforhold: {antall_eierskap}")
    print(f"  Toppselskaper:           {len(toppselskaper)}")
    print(f"  Operative selskaper:     {bunnselskaper}")
    
    if toppselskaper:
        print(f"\n  TOPPSELSKAPER (eies ikke av andre):")
        print(f"  {'-'*55}")
        for t in toppselskaper:
            # Tell hvor mange selskaper som ligger under
            antall_under = conn.execute("""
                WITH RECURSIVE underselskaper AS (
                    SELECT eid_id as id FROM eierskap WHERE eier_id = ?
                    UNION
                    SELECT e.eid_id FROM eierskap e
                    JOIN underselskaper u ON e.eier_id = u.id
                )
                SELECT COUNT(*) FROM underselskaper
            """, (t['id'],)).fetchone()[0]
            print(f"  {t['kode']:8} {t['navn'][:40]:41} ({antall_under} underselskaper)")
    
    # Holdingselskaper som kun eier 1 selskap (gjennomgangs-holdinger)
    print(f"\n  GJENNOMGANGS-HOLDINGER (eier kun 1 selskap):")
    print(f"  {'-'*55}")
    
    gjennomgang = conn.execute("""
        SELECT eier.kode as eier_kode, eier.navn as eier_navn,
               eid.kode as eid_kode, eid.navn as eid_navn
        FROM eierskap e
        JOIN selskaper eier ON eier.id = e.eier_id
        JOIN selskaper eid ON eid.id = e.eid_id
        WHERE e.eier_id IN (
            SELECT eier_id FROM eierskap GROUP BY eier_id HAVING COUNT(*) = 1
        )
        ORDER BY eier.navn
    """).fetchall()
    
    for g in gjennomgang:
        print(f"  {g['eier_kode']:8} {g['eier_navn'][:30]:31} → {g['eid_kode']:8} {g['eid_navn'][:20]}")
    
    print(f"\n  HOLDINGSELSKAPER (eier flere enn 1 selskap):")
    print(f"  {'-'*55}")
    
    holdinger = conn.execute("""
        SELECT s.kode, s.navn, COUNT(e.id) as antall
        FROM selskaper s
        JOIN eierskap e ON e.eier_id = s.id
        GROUP BY s.id
        HAVING COUNT(e.id) > 1
        ORDER BY antall DESC
        LIMIT 10
    """).fetchall()
    
    for h in holdinger:
        print(f"  {h['kode']:8} {h['navn'][:40]:41} {h['antall']:3} selskaper")
    
    conn.close()


def vis_tre(selskap_id=None, vis_tall=False):
    """Vis hele eierstrukturen som et tre."""
    conn = get_db()
    
    # Hvis ikke spesifisert, finn toppselskapet med flest underselskaper
    if selskap_id is None:
        topp = conn.execute("""
            SELECT s.id, s.kode, s.navn
            FROM selskaper s
            WHERE s.id NOT IN (SELECT eid_id FROM eierskap)
            AND s.id IN (SELECT eier_id FROM eierskap)
        """).fetchall()
        
        # Finn den med flest underselskaper (ECIT TopCo)
        beste = None
        beste_antall = 0
        for t in topp:
            antall = conn.execute("""
                WITH RECURSIVE underselskaper AS (
                    SELECT eid_id as id FROM eierskap WHERE eier_id = ?
                    UNION
                    SELECT e.eid_id FROM eierskap e
                    JOIN underselskaper u ON e.eier_id = u.id
                )
                SELECT COUNT(*) FROM underselskaper
            """, (t['id'],)).fetchone()[0]
            if antall > beste_antall:
                beste = t
                beste_antall = antall
        
        if beste:
            selskap_id = beste['id']
        else:
            print("Ingen toppselskap funnet")
            conn.close()
            return
    
    # Hent selskapsinfo
    selskap = conn.execute(
        "SELECT kode, navn FROM selskaper WHERE id = ?", 
        (selskap_id,)
    ).fetchone()
    
    print(f"\n{'='*95}")
    print(f"EIERSTRUKTUR FRA: {selskap['navn']} ({selskap['kode']})")
    print(f"{'='*95}")
    print(f"{selskap['kode']} {selskap['navn']}")
    
    direkte_investering = [0]  # Investeringer direkte fra toppselskapet
    
    # Bygg mapping av største eier for hvert selskap
    største_eier = {}
    alle_eiere = conn.execute("""
        SELECT e.eid_id, e.eier_id, e.investering
        FROM eierskap e
    """).fetchall()
    
    for row in alle_eiere:
        eid_id = row['eid_id']
        if eid_id not in største_eier or row['investering'] > største_eier[eid_id]['investering']:
            største_eier[eid_id] = {'eier_id': row['eier_id'], 'investering': row['investering']}
    
    def hent_eierinfo(datter_id, denne_eier_id):
        """Hent info om alle eiere av et selskap og beregn andeler."""
        eiere = conn.execute("""
            SELECT eier.kode, e.investering
            FROM eierskap e
            JOIN selskaper eier ON eier.id = e.eier_id
            WHERE e.eid_id = ?
            ORDER BY e.investering DESC
        """, (datter_id,)).fetchall()
        
        if len(eiere) <= 1:
            return None, True  # Kun én eier, vis alltid
        
        total = sum(e['investering'] for e in eiere)
        if total == 0:
            return None, True
        
        # Finn denne eiers andel
        denne_andel = 0
        for e in eiere:
            if e['kode'] == conn.execute("SELECT kode FROM selskaper WHERE id=?", (denne_eier_id,)).fetchone()['kode']:
                denne_andel = e['investering'] / total * 100
                break
        
        # Er dette største eier?
        er_største = (største_eier.get(datter_id, {}).get('eier_id') == denne_eier_id)
        
        if not er_største:
            return None, False  # Vis ikke under mindre eiere
        
        # Bygg tekst om andre eiere
        andre = [f"{e['kode']} {e['investering']/total*100:.0f}%" for e in eiere[1:]]
        eierinfo = f"({denne_andel:.0f}% - også: {', '.join(andre)})"
        return eierinfo, True
    
    def skriv_tre(sid, prefix="", er_siste=True, visited=None, nivå=0):
        if visited is None:
            visited = set()
        
        if sid in visited:
            return
        visited.add(sid)
        
        if vis_tall:
            datter = conn.execute("""
                SELECT s.id, s.kode, s.navn, e.investering
                FROM eierskap e
                JOIN selskaper s ON s.id = e.eid_id
                WHERE e.eier_id = ?
                ORDER BY e.investering DESC
            """, (sid,)).fetchall()
        else:
            datter = conn.execute("""
                SELECT s.id, s.kode, s.navn, 0 as investering
                FROM eierskap e
                JOIN selskaper s ON s.id = e.eid_id
                WHERE e.eier_id = ?
                ORDER BY s.navn
            """, (sid,)).fetchall()
        
        # Filtrer ut selskaper som skal vises under annen eier
        datter_filtrert = []
        for d in datter:
            eierinfo, vis = hent_eierinfo(d['id'], sid)
            if vis:
                datter_filtrert.append((d, eierinfo))
        
        for i, (d, eierinfo) in enumerate(datter_filtrert):
            er_siste_barn = (i == len(datter_filtrert) - 1)
            
            # Velg riktig tegn
            if er_siste_barn:
                gren = "└── "
                ny_prefix = prefix + "    "
            else:
                gren = "├── "
                ny_prefix = prefix + "│   "
            
            if vis_tall and d['investering']:
                if nivå == 0:
                    direkte_investering[0] += d['investering']
                if eierinfo:
                    print(f"{prefix}{gren}{d['kode']} {d['navn'][:30]:31} {format_belop(d['investering']):>12} {eierinfo}")
                else:
                    print(f"{prefix}{gren}{d['kode']} {d['navn'][:40]:41} {format_belop(d['investering']):>12}")
            else:
                if eierinfo:
                    print(f"{prefix}{gren}{d['kode']} {d['navn'][:45]} {eierinfo}")
                else:
                    print(f"{prefix}{gren}{d['kode']} {d['navn']}")
            skriv_tre(d['id'], ny_prefix, er_siste_barn, visited.copy(), nivå + 1)
    
    skriv_tre(selskap_id)
    print(f"{'='*95}")
    if vis_tall:
        print(f"DIREKTE INVESTERING: {format_belop(direkte_investering[0])}")
    conn.close()


def velg_selskap(resultater):
    """La bruker velge fra søkeresultater."""
    if len(resultater) == 0:
        print("  Ingen treff")
        return None
    
    if len(resultater) == 1:
        return resultater[0]['id']
    
    print(f"\n  Flere treff ({len(resultater)}):")
    for i, r in enumerate(resultater[:15], 1):
        print(f"  {i:2}. {r['kode']:8} {r['navn']}")
    
    if len(resultater) > 15:
        print(f"  ... og {len(resultater) - 15} flere")
    
    try:
        valg = input("\n  Velg nummer (Enter for første): ").strip()
        if valg == "":
            return resultater[0]['id']
        idx = int(valg) - 1
        if 0 <= idx < len(resultater):
            return resultater[idx]['id']
    except (ValueError, IndexError):
        pass
    
    return None


def vis_sammenligning(selskap_ider, vis_tall=False):
    """Vis flere selskaper side om side."""
    conn = get_db()
    
    print(f"\n{'='*95}")
    print("  SAMMENLIGNING AV SELSKAPER")
    print(f"{'='*95}")
    
    for selskap_id in selskap_ider:
        selskap = conn.execute(
            "SELECT kode, navn FROM selskaper WHERE id = ?", 
            (selskap_id,)
        ).fetchone()
        
        if not selskap:
            continue
            
        # Finn datterselskaper
        datterselskaper = conn.execute("""
            SELECT s.kode, s.navn, e.investering
            FROM eierskap e
            JOIN selskaper s ON s.id = e.eid_id
            WHERE e.eier_id = ?
            ORDER BY e.investering DESC
        """, (selskap_id,)).fetchall()
        
        total_investering = sum(d['investering'] for d in datterselskaper)
        
        print(f"\n  ┌─ {selskap['kode']} {selskap['navn']}")
        if vis_tall:
            print(f"  │  Total investering: {format_belop(total_investering)}")
        print(f"  │  Datterselskaper: {len(datterselskaper)}")
        print(f"  │")
        
        for i, d in enumerate(datterselskaper[:10]):
            gren = "└──" if i == len(datterselskaper[:10]) - 1 else "├──"
            if vis_tall:
                print(f"  │  {gren} {d['kode']:8} {d['navn'][:30]:31} {format_belop(d['investering']):>12}")
            else:
                print(f"  │  {gren} {d['kode']:8} {d['navn'][:45]}")
        
        if len(datterselskaper) > 10:
            print(f"  │      ... og {len(datterselskaper) - 10} flere")
    
    print(f"\n{'='*95}")
    conn.close()


def main():
    print("\n" + "="*60)
    print("  KONSERNSTRUKTUR SØKEVERKTØY")
    print("="*60)
    print("""
  KOMMANDOER:
    s <navn/kode>  - Søk etter selskap
    e <navn/kode>  - Vis eiere av selskap
    d <navn/kode>  - Vis datterselskaper (direkte eid)
    k <navn/kode>  - Vis full konsernstruktur nedover
    o <navn/kode>  - Vis eierkjede oppover
    tre            - Vis hele eierstrukturen (fra TopCo)
    tre <navn>     - Vis eierstruktur fra valgt selskap
    sml <s1,s2,..> - Sammenlign flere selskaper (komma-separert)
    stat           - Vis statistikk
    q              - Avslutt
    
  Legg til 't' for å vise tall: tre t, sml t NORH,INTH,MASEH
    
  Eksempel: sml NORH,INTH,MASEH,TECH (vis de 4 divisjonsholdingene)
""")
    
    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAvslutter...")
            break
        
        if not cmd:
            continue
        
        if cmd.lower() == 'q':
            print("Avslutter...")
            break
        
        if cmd.lower() == 'stat':
            vis_statistikk()
            continue
        
        if cmd.lower() == 'tre':
            vis_tre()
            continue
        
        if cmd.lower() == 'tre t':
            vis_tre(vis_tall=True)
            continue
        
        parts = cmd.split()
        if len(parts) < 2:
            print("  Bruk: <kommando> <søkeord>  (legg til 't' for tall)")
            continue
        
        kommando = parts[0].lower()
        vis_tall = 't' in [p.lower() for p in parts[1:]]
        søkeord_parts = [p for p in parts[1:] if p.lower() != 't']
        søkeord = ' '.join(søkeord_parts) if søkeord_parts else ''
        
        if kommando == 'tre':
            if søkeord:
                resultater = sok_selskap(søkeord)
                selskap_id = velg_selskap(resultater)
                if selskap_id:
                    vis_tre(selskap_id, vis_tall=vis_tall)
            else:
                vis_tre(vis_tall=vis_tall)
        
        elif kommando == 's':
            resultater = sok_selskap(søkeord)
            if resultater:
                print(f"\n  Treff ({len(resultater)}):")
                for r in resultater[:20]:
                    print(f"  {r['kode']:8} {r['navn']}")
            else:
                print("  Ingen treff")
        
        elif kommando == 'e':
            resultater = sok_selskap(søkeord)
            selskap_id = velg_selskap(resultater)
            if selskap_id:
                vis_eiere(selskap_id)
        
        elif kommando == 'd':
            resultater = sok_selskap(søkeord)
            selskap_id = velg_selskap(resultater)
            if selskap_id:
                vis_datterselskaper(selskap_id)
        
        elif kommando == 'k':
            resultater = sok_selskap(søkeord)
            selskap_id = velg_selskap(resultater)
            if selskap_id:
                vis_konsernstruktur(selskap_id)
        
        elif kommando == 'o':
            resultater = sok_selskap(søkeord)
            selskap_id = velg_selskap(resultater)
            if selskap_id:
                vis_eierkjede(selskap_id)
        
        elif kommando == 'sml':
            # Sammenlign flere selskaper (komma-separert)
            selskap_koder = [s.strip() for s in søkeord.split(',') if s.strip()]
            selskap_ider = []
            for kode in selskap_koder:
                resultater = sok_selskap(kode)
                if len(resultater) == 1:
                    selskap_ider.append(resultater[0]['id'])
                elif len(resultater) > 1:
                    print(f"  Flertydig søk '{kode}', velger første treff: {resultater[0]['kode']}")
                    selskap_ider.append(resultater[0]['id'])
                else:
                    print(f"  Fant ikke: {kode}")
            if selskap_ider:
                vis_sammenligning(selskap_ider, vis_tall=vis_tall)
        
        else:
            print(f"  Ukjent kommando: {kommando}")
            print("  Bruk: s/e/d/k/o/sml <søkeord> eller 'stat' eller 'q'")


if __name__ == "__main__":
    main()
