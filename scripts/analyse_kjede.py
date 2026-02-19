import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "data" / "konsern.db"
conn = sqlite3.connect(str(DB_FILE))
conn.row_factory = sqlite3.Row

print('EIERKJEDE TOPCO -> XX med bokført verdi:')
print()

kjede = [('TOPCO', 'MIDCO2'), ('MIDCO2', 'BIDCO'), ('BIDCO', 'XX')]

for eier_kode, eid_kode in kjede:
    result = conn.execute('''
        SELECT e.investering
        FROM eierskap e
        JOIN selskaper eier ON eier.id = e.eier_id
        JOIN selskaper eid ON eid.id = e.eid_id
        WHERE eier.kode = ? AND eid.kode = ?
    ''', (eier_kode, eid_kode)).fetchone()
    if result:
        print(f'{eier_kode:8} -> {eid_kode:8}: {result[0]/1_000_000:,.1f} MNOK')

print()
print('Hva ECIT AS (XX) eier:')
xx_eier = conn.execute('''
    SELECT eid.kode, eid.navn, e.investering
    FROM eierskap e
    JOIN selskaper eier ON eier.id = e.eier_id
    JOIN selskaper eid ON eid.id = e.eid_id
    WHERE eier.kode = 'XX'
    ORDER BY e.investering DESC
''').fetchall()

total = 0
for e in xx_eier:
    print(f'  {e[0]:8} {e[1][:35]:36} {e[2]/1_000_000:,.1f} MNOK')
    total += e[2]
print()
print(f'  TOTAL XX investering: {total/1_000_000:,.1f} MNOK')
conn.close()
