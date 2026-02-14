"""
Analyse-modul for HR-data.
Beregner statistikk om ansatte, aldersfordeling, churn, mm.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from collections import defaultdict

from .database import get_connection, DEFAULT_DB_PATH


# Alderskategorier
AGE_CATEGORIES = [
    (0, 24, 'Under 25'),
    (25, 34, '25-34'),
    (35, 44, '35-44'),
    (45, 54, '45-54'),
    (55, 64, '55-64'),
    (65, 100, '65+'),
]


def get_age_category(age: int) -> str:
    """Returner alderskategori for gitt alder."""
    for min_age, max_age, label in AGE_CATEGORIES:
        if min_age <= age <= max_age:
            return label
    return 'Ukjent'


class HRAnalytics:
    """Analyseklasse for HR-data."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
    
    def _query(self, sql: str, params: tuple = ()) -> list:
        """Kjør SQL-spørring og returner resultater."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def _query_scalar(self, sql: str, params: tuple = ()):
        """Kjør SQL-spørring og returner enkeltverdi."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    # === GRUNNLEGGENDE STATISTIKK ===
    
    def total_employees(self, active_only: bool = True) -> int:
        """Tell totalt antall ansatte."""
        if active_only:
            return self._query_scalar(
                "SELECT COUNT(*) FROM ansatte WHERE er_aktiv = 1"
            ) or 0
        return self._query_scalar("SELECT COUNT(*) FROM ansatte") or 0
    
    def employees_summary(self) -> Dict:
        """Generell oversikt over ansatte."""
        return {
            'totalt': self.total_employees(active_only=False),
            'aktive': self.total_employees(active_only=True),
            'sluttede': self._query_scalar(
                "SELECT COUNT(*) FROM ansatte WHERE er_aktiv = 0"
            ) or 0,
            'gjennomsnitt_alder': round(self._query_scalar(
                "SELECT AVG(alder) FROM ansatte WHERE er_aktiv = 1 AND alder IS NOT NULL"
            ) or 0, 1),
        }
    
    # === ALDERSANALYSE ===
    
    def age_distribution(self, active_only: bool = True) -> Dict[str, int]:
        """
        Fordeling av ansatte per alderskategori.
        Returnerer dict med kategori -> antall.
        """
        where = "WHERE er_aktiv = 1 AND alder IS NOT NULL" if active_only else "WHERE alder IS NOT NULL"
        rows = self._query(f"SELECT alder FROM ansatte {where}")
        
        distribution = {cat[2]: 0 for cat in AGE_CATEGORIES}
        distribution['Ukjent'] = 0
        
        for row in rows:
            category = get_age_category(row['alder'])
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution
    
    def age_distribution_pct(self, active_only: bool = True) -> Dict[str, float]:
        """Aldersfordeling i prosent."""
        dist = self.age_distribution(active_only)
        total = sum(dist.values())
        if total == 0:
            return {k: 0.0 for k in dist}
        return {k: round(v / total * 100, 1) for k, v in dist.items()}
    
    def age_distribution_by_country(self, active_only: bool = True) -> Dict[str, Dict[str, int]]:
        """Aldersfordeling per land."""
        where = "WHERE er_aktiv = 1 AND alder IS NOT NULL" if active_only else "WHERE alder IS NOT NULL"
        rows = self._query(f"SELECT alder, arbeidsland FROM ansatte {where}")
        
        result = defaultdict(lambda: {cat[2]: 0 for cat in AGE_CATEGORIES})
        
        for row in rows:
            country = row['arbeidsland'] or 'Ukjent land'
            category = get_age_category(row['alder'])
            result[country][category] += 1
        
        return dict(result)
    
    # === GEOGRAFISK ANALYSE ===
    
    def employees_by_country(self, active_only: bool = True) -> Dict[str, int]:
        """Antall ansatte per land."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT COALESCE(arbeidsland, 'Ukjent') as land, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY land
            ORDER BY antall DESC
        """)
        return {row['land']: row['antall'] for row in rows}
    
    def employees_by_company(self, active_only: bool = True) -> Dict[str, int]:
        """Antall ansatte per juridisk selskap."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT COALESCE(juridisk_selskap, 'Ukjent') as selskap, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY selskap
            ORDER BY antall DESC
        """)
        return {row['selskap']: row['antall'] for row in rows}
    
    def employees_by_department(self, active_only: bool = True) -> Dict[str, int]:
        """Antall ansatte per avdeling."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT COALESCE(avdeling, 'Ukjent') as avdeling, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY avdeling
            ORDER BY antall DESC
        """)
        return {row['avdeling']: row['antall'] for row in rows}
    
    # === KJØNNSANALYSE ===
    
    def gender_distribution(self, active_only: bool = True) -> Dict[str, int]:
        """Kjønnsfordeling."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT COALESCE(kjonn, 'Ukjent') as kjonn, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY kjonn
        """)
        return {row['kjonn']: row['antall'] for row in rows}
    
    def gender_by_country(self, active_only: bool = True) -> Dict[str, Dict[str, int]]:
        """Kjønnsfordeling per land."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT 
                COALESCE(arbeidsland, 'Ukjent') as land,
                COALESCE(kjonn, 'Ukjent') as kjonn,
                COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY land, kjonn
        """)
        
        result = defaultdict(lambda: {'Mann': 0, 'Kvinne': 0, 'Ukjent': 0})
        for row in rows:
            result[row['land']][row['kjonn']] = row['antall']
        
        return dict(result)
    
    # === CHURN / TURNOVER ANALYSE ===
    
    def calculate_churn(
        self,
        start_date: str,
        end_date: str,
        by: str = 'total'
    ) -> Dict:
        """
        Beregn churn/turnover for en periode.
        
        Args:
            start_date: Startdato (YYYY-MM-DD)
            end_date: Sluttdato (YYYY-MM-DD)
            by: 'total', 'country', 'company', 'department'
        
        Returns:
            Dict med churn-statistikk
        """
        # Ansatte som sluttet i perioden
        terminated = self._query("""
            SELECT 
                arbeidsland, juridisk_selskap, avdeling, 
                slutdato_ansettelse, oppsigelsesarsak
            FROM ansatte
            WHERE slutdato_ansettelse BETWEEN ? AND ?
        """, (start_date, end_date))
        
        # Nyansatte i perioden
        hired = self._query("""
            SELECT arbeidsland, juridisk_selskap, avdeling
            FROM ansatte
            WHERE ansettelsens_startdato BETWEEN ? AND ?
        """, (start_date, end_date))
        
        # Gjennomsnittlig antall ansatte (forenklet: ved periodeslutt)
        avg_headcount = self._query_scalar("""
            SELECT COUNT(*) FROM ansatte
            WHERE ansettelsens_startdato <= ?
            AND (slutdato_ansettelse IS NULL OR slutdato_ansettelse > ?)
        """, (end_date, start_date)) or 1
        
        result = {
            'periode': f"{start_date} til {end_date}",
            'antall_sluttet': len(terminated),
            'antall_nyansatte': len(hired),
            'gjennomsnittlig_ansatte': avg_headcount,
            'churn_rate_pct': round(len(terminated) / avg_headcount * 100, 2) if avg_headcount > 0 else 0,
            'netto_endring': len(hired) - len(terminated),
        }
        
        if by == 'country':
            result['per_land'] = self._aggregate_churn(terminated, hired, 'arbeidsland')
        elif by == 'company':
            result['per_selskap'] = self._aggregate_churn(terminated, hired, 'juridisk_selskap')
        elif by == 'department':
            result['per_avdeling'] = self._aggregate_churn(terminated, hired, 'avdeling')
        
        return result
    
    def _aggregate_churn(self, terminated: list, hired: list, key: str) -> Dict:
        """Aggreger churn per grupperingsnøkkel."""
        term_count = defaultdict(int)
        hire_count = defaultdict(int)
        
        for t in terminated:
            term_count[t[key] or 'Ukjent'] += 1
        for h in hired:
            hire_count[h[key] or 'Ukjent'] += 1
        
        all_keys = set(term_count.keys()) | set(hire_count.keys())
        
        return {
            k: {
                'sluttet': term_count[k],
                'nyansatte': hire_count[k],
                'netto': hire_count[k] - term_count[k]
            }
            for k in sorted(all_keys)
        }
    
    def monthly_churn(self, year: int) -> List[Dict]:
        """Churn per måned for et gitt år."""
        results = []
        
        for month in range(1, 13):
            if month == 12:
                start = f"{year}-{month:02d}-01"
                end = f"{year + 1}-01-01"
            else:
                start = f"{year}-{month:02d}-01"
                end = f"{year}-{month + 1:02d}-01"
            
            # Sjekk om vi har data for denne perioden
            terminated = self._query_scalar("""
                SELECT COUNT(*) FROM ansatte
                WHERE slutdato_ansettelse >= ? AND slutdato_ansettelse < ?
            """, (start, end)) or 0
            
            hired = self._query_scalar("""
                SELECT COUNT(*) FROM ansatte
                WHERE ansettelsens_startdato >= ? AND ansettelsens_startdato < ?
            """, (start, end)) or 0
            
            results.append({
                'måned': f"{year}-{month:02d}",
                'sluttet': terminated,
                'nyansatte': hired,
                'netto': hired - terminated
            })
        
        return results
    
    # === ANSETTELSETID / TENURE ===
    
    def average_tenure(self, active_only: bool = True) -> float:
        """Gjennomsnittlig ansettelsestid i år."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        result = self._query_scalar(f"""
            SELECT AVG(
                JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - 
                JULIANDAY(ansettelsens_startdato)
            ) / 365.25
            FROM ansatte
            {where}
            AND ansettelsens_startdato IS NOT NULL
        """)
        return round(result or 0, 1)
    
    def tenure_distribution(self, active_only: bool = True) -> Dict[str, int]:
        """Fordeling av ansettelsestid i kategorier."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT 
                (JULIANDAY(COALESCE(slutdato_ansettelse, date('now'))) - 
                 JULIANDAY(ansettelsens_startdato)) / 365.25 as tenure
            FROM ansatte
            {where}
            AND ansettelsens_startdato IS NOT NULL
        """)
        
        categories = {
            'Under 1 år': 0,
            '1-2 år': 0,
            '2-5 år': 0,
            '5-10 år': 0,
            'Over 10 år': 0,
        }
        
        for row in rows:
            tenure = row['tenure']
            if tenure < 1:
                categories['Under 1 år'] += 1
            elif tenure < 2:
                categories['1-2 år'] += 1
            elif tenure < 5:
                categories['2-5 år'] += 1
            elif tenure < 10:
                categories['5-10 år'] += 1
            else:
                categories['Over 10 år'] += 1
        
        return categories
    
    # === ANSETTELSESTYPE ANALYSE ===
    
    def employment_type_distribution(self, active_only: bool = True) -> Dict[str, int]:
        """Fordeling av ansettelsestyper."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT COALESCE(ansettelsetype, 'Ukjent') as type, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY type
            ORDER BY antall DESC
        """)
        return {row['type']: row['antall'] for row in rows}
    
    def fulltime_vs_parttime(self, active_only: bool = True) -> Dict[str, int]:
        """Heltid vs deltid basert på arbeidstid."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT 
                CASE 
                    WHEN arbeidstid_per_uke >= heltid_per_uke THEN 'Heltid'
                    WHEN arbeidstid_per_uke IS NOT NULL THEN 'Deltid'
                    ELSE 'Ukjent'
                END as arbeidstid_type,
                COUNT(*) as antall
            FROM ansatte {where}
            GROUP BY arbeidstid_type
        """)
        return {row['arbeidstid_type']: row['antall'] for row in rows}
    
    # === LEDELSEANALYSE ===
    
    def manager_ratio(self, active_only: bool = True) -> Dict:
        """Andel ledere vs ikke-ledere."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT er_leder, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY er_leder
        """)
        
        result = {'ledere': 0, 'ikke_ledere': 0}
        for row in rows:
            if row['er_leder'] and row['er_leder'].lower() in ('ja', 'yes', '1', 'true'):
                result['ledere'] = row['antall']
            else:
                result['ikke_ledere'] += row['antall']
        
        total = result['ledere'] + result['ikke_ledere']
        result['leder_andel_pct'] = round(result['ledere'] / total * 100, 1) if total > 0 else 0
        result['ansatte_per_leder'] = round(result['ikke_ledere'] / result['ledere'], 1) if result['ledere'] > 0 else 0
        
        return result
    
    # === DETALJERTE SØKERESULTATER ===
    
    def search_employees(
        self,
        name: str = None,
        department: str = None,
        country: str = None,
        company: str = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Dict]:
        """Søk etter ansatte."""
        conditions = []
        params = []
        
        if active_only:
            conditions.append("er_aktiv = 1")
        
        if name:
            conditions.append("(fornavn LIKE ? OR etternavn LIKE ?)")
            params.extend([f'%{name}%', f'%{name}%'])
        
        if department:
            conditions.append("avdeling LIKE ?")
            params.append(f'%{department}%')
        
        if country:
            conditions.append("arbeidsland LIKE ?")
            params.append(f'%{country}%')
        
        if company:
            conditions.append("juridisk_selskap LIKE ?")
            params.append(f'%{company}%')
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        return self._query(f"""
            SELECT 
                id, fornavn, etternavn, tittel, avdeling, 
                arbeidsland, juridisk_selskap, alder, er_aktiv
            FROM ansatte
            {where}
            ORDER BY etternavn, fornavn
            LIMIT ?
        """, tuple(params) + (limit,))
    
    def get_termination_reasons(self, start_date: str = None, end_date: str = None) -> Dict[str, int]:
        """Oversikt over oppsigelsesårsaker."""
        conditions = ["slutdato_ansettelse IS NOT NULL"]
        params = []
        
        if start_date:
            conditions.append("slutdato_ansettelse >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("slutdato_ansettelse <= ?")
            params.append(end_date)
        
        where = "WHERE " + " AND ".join(conditions)
        
        rows = self._query(f"""
            SELECT COALESCE(oppsigelsesarsak, 'Ikke oppgitt') as arsak, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY arsak
            ORDER BY antall DESC
        """, tuple(params))
        
        return {row['arsak']: row['antall'] for row in rows}
    
    # === KOMBINERTE ANALYSER ===
    
    def churn_by_age(self, start_date: str, end_date: str) -> Dict[str, Dict]:
        """
        Churn fordelt på alderskategorier.
        Viser hvilke aldersgrupper som har høyest turnover.
        """
        # Ansatte som sluttet i perioden, med alder
        terminated = self._query("""
            SELECT alder FROM ansatte
            WHERE slutdato_ansettelse BETWEEN ? AND ?
            AND alder IS NOT NULL
        """, (start_date, end_date))
        
        # Totalt antall per alderskategori ved periodeslutt
        active_by_age = self._query("""
            SELECT alder FROM ansatte
            WHERE ansettelsens_startdato <= ?
            AND (slutdato_ansettelse IS NULL OR slutdato_ansettelse > ?)
            AND alder IS NOT NULL
        """, (end_date, start_date))
        
        # Aggreger per alderskategori
        term_by_cat = defaultdict(int)
        active_by_cat = defaultdict(int)
        
        for row in terminated:
            cat = get_age_category(row['alder'])
            term_by_cat[cat] += 1
        
        for row in active_by_age:
            cat = get_age_category(row['alder'])
            active_by_cat[cat] += 1
        
        result = {}
        for cat in [c[2] for c in AGE_CATEGORIES]:
            total = active_by_cat[cat]
            sluttet = term_by_cat[cat]
            result[cat] = {
                'totalt': total,
                'sluttet': sluttet,
                'churn_rate_pct': round(sluttet / total * 100, 1) if total > 0 else 0
            }
        
        return result
    
    def churn_by_country(self, start_date: str, end_date: str) -> Dict[str, Dict]:
        """Churn fordelt på land."""
        terminated = self._query("""
            SELECT COALESCE(arbeidsland, 'Ukjent') as land FROM ansatte
            WHERE slutdato_ansettelse BETWEEN ? AND ?
        """, (start_date, end_date))
        
        active = self._query("""
            SELECT COALESCE(arbeidsland, 'Ukjent') as land FROM ansatte
            WHERE ansettelsens_startdato <= ?
            AND (slutdato_ansettelse IS NULL OR slutdato_ansettelse > ?)
        """, (end_date, start_date))
        
        term_by_country = defaultdict(int)
        active_by_country = defaultdict(int)
        
        for row in terminated:
            term_by_country[row['land']] += 1
        for row in active:
            active_by_country[row['land']] += 1
        
        all_countries = set(term_by_country.keys()) | set(active_by_country.keys())
        
        result = {}
        for country in sorted(all_countries):
            total = active_by_country[country]
            sluttet = term_by_country[country]
            result[country] = {
                'totalt': total,
                'sluttet': sluttet,
                'churn_rate_pct': round(sluttet / total * 100, 1) if total > 0 else 0
            }
        
        return result
    
    def churn_by_gender(self, start_date: str, end_date: str) -> Dict[str, Dict]:
        """Churn fordelt på kjønn."""
        terminated = self._query("""
            SELECT COALESCE(kjonn, 'Ukjent') as kjonn FROM ansatte
            WHERE slutdato_ansettelse BETWEEN ? AND ?
        """, (start_date, end_date))
        
        active = self._query("""
            SELECT COALESCE(kjonn, 'Ukjent') as kjonn FROM ansatte
            WHERE ansettelsens_startdato <= ?
            AND (slutdato_ansettelse IS NULL OR slutdato_ansettelse > ?)
        """, (end_date, start_date))
        
        term_by_gender = defaultdict(int)
        active_by_gender = defaultdict(int)
        
        for row in terminated:
            term_by_gender[row['kjonn']] += 1
        for row in active:
            active_by_gender[row['kjonn']] += 1
        
        all_genders = set(term_by_gender.keys()) | set(active_by_gender.keys())
        
        result = {}
        for gender in sorted(all_genders):
            total = active_by_gender[gender]
            sluttet = term_by_gender[gender]
            result[gender] = {
                'totalt': total,
                'sluttet': sluttet,
                'churn_rate_pct': round(sluttet / total * 100, 1) if total > 0 else 0
            }
        
        return result
    
    def age_and_gender_by_country(self, active_only: bool = True) -> Dict[str, Dict]:
        """
        Kombinert oversikt: alder og kjønn per land.
        """
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT 
                COALESCE(arbeidsland, 'Ukjent') as land,
                COALESCE(kjonn, 'Ukjent') as kjonn,
                alder
            FROM ansatte {where}
        """)
        
        result = defaultdict(lambda: {
            'total': 0,
            'kjønn': {'Mann': 0, 'Kvinne': 0, 'Ukjent': 0},
            'alder': {cat[2]: 0 for cat in AGE_CATEGORIES},
            'snitt_alder': []
        })
        
        for row in rows:
            land = row['land']
            result[land]['total'] += 1
            result[land]['kjønn'][row['kjonn']] = result[land]['kjønn'].get(row['kjonn'], 0) + 1
            
            if row['alder']:
                cat = get_age_category(row['alder'])
                result[land]['alder'][cat] += 1
                result[land]['snitt_alder'].append(row['alder'])
        
        # Beregn snitt alder
        for land in result:
            ages = result[land]['snitt_alder']
            result[land]['snitt_alder'] = round(sum(ages) / len(ages), 1) if ages else 0
        
        return dict(result)
    
    def planned_departures(self, months_ahead: int = 12) -> List[Dict]:
        """
        Ansatte med planlagt slutdato i fremtiden.
        
        Args:
            months_ahead: Hvor mange måneder fremover å se
        """
        today = date.today()
        future_date = date(
            today.year + (today.month + months_ahead - 1) // 12,
            (today.month + months_ahead - 1) % 12 + 1,
            min(today.day, 28)
        )
        
        rows = self._query("""
            SELECT 
                id, fornavn, etternavn, tittel, avdeling, 
                arbeidsland, juridisk_selskap, slutdato_ansettelse
            FROM ansatte
            WHERE slutdato_ansettelse > date('now')
            AND slutdato_ansettelse <= ?
            ORDER BY slutdato_ansettelse
        """, (str(future_date),))
        
        return rows
    
    def combined_summary(self, country: str = None, active_only: bool = True) -> Dict:
        """
        Kombinert sammendrag med alle nøkkeltall.
        Kan filtreres på land.
        """
        where_parts = []
        params = []
        
        if active_only:
            where_parts.append("er_aktiv = 1")
        if country:
            where_parts.append("arbeidsland = ?")
            params.append(country)
        
        where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
        
        # Hent alle relevante data
        rows = self._query(f"""
            SELECT alder, kjonn, avdeling, ansettelsens_startdato, slutdato_ansettelse
            FROM ansatte {where}
        """, tuple(params))
        
        if not rows:
            return {'feil': 'Ingen data funnet'}
        
        total = len(rows)
        ages = [r['alder'] for r in rows if r['alder']]
        genders = defaultdict(int)
        age_cats = defaultdict(int)
        depts = defaultdict(int)
        
        for row in rows:
            if row['kjonn']:
                genders[row['kjonn']] += 1
            if row['alder']:
                age_cats[get_age_category(row['alder'])] += 1
            if row['avdeling']:
                depts[row['avdeling']] += 1
        
        return {
            'antall': total,
            'snitt_alder': round(sum(ages) / len(ages), 1) if ages else 0,
            'kjønnsfordeling': dict(genders),
            'kjønn_pct': {k: round(v/total*100, 1) for k, v in genders.items()},
            'aldersfordeling': dict(age_cats),
            'alder_pct': {k: round(v/total*100, 1) for k, v in age_cats.items()},
            'avdelinger': dict(depts)
        }
    
    # === LØNNSANALYSE ===
    
    def salary_summary(self, active_only: bool = True) -> Dict:
        """Oppsummering av lønnsdata."""
        where = "WHERE er_aktiv = 1 AND lonn IS NOT NULL" if active_only else "WHERE lonn IS NOT NULL"
        
        result = self._query(f"""
            SELECT 
                COUNT(*) as antall,
                AVG(lonn) as snitt,
                MIN(lonn) as min,
                MAX(lonn) as maks,
                SUM(lonn) as total
            FROM ansatte {where}
        """)
        
        if not result or result[0]['antall'] == 0:
            return {'antall': 0, 'melding': 'Ingen lønnsdata tilgjengelig'}
        
        r = result[0]
        return {
            'antall_med_lonn': r['antall'],
            'gjennomsnitt': round(r['snitt'], 0) if r['snitt'] else 0,
            'min': r['min'],
            'maks': r['maks'],
            'total_lonnsmasse': round(r['total'], 0) if r['total'] else 0
        }
    
    def salary_by_department(self, active_only: bool = True) -> Dict[str, Dict]:
        """Gjennomsnittlig lønn per avdeling."""
        where = "WHERE er_aktiv = 1 AND lonn IS NOT NULL" if active_only else "WHERE lonn IS NOT NULL"
        
        rows = self._query(f"""
            SELECT 
                COALESCE(avdeling, 'Ukjent') as avdeling,
                COUNT(*) as antall,
                AVG(lonn) as snitt,
                MIN(lonn) as min,
                MAX(lonn) as maks
            FROM ansatte {where}
            GROUP BY avdeling
            ORDER BY snitt DESC
        """)
        
        return {
            row['avdeling']: {
                'antall': row['antall'],
                'gjennomsnitt': round(row['snitt'], 0),
                'min': row['min'],
                'maks': row['maks']
            }
            for row in rows
        }
    
    def salary_by_country(self, active_only: bool = True) -> Dict[str, Dict]:
        """Gjennomsnittlig lønn per land."""
        where = "WHERE er_aktiv = 1 AND lonn IS NOT NULL" if active_only else "WHERE lonn IS NOT NULL"
        
        rows = self._query(f"""
            SELECT 
                COALESCE(arbeidsland, 'Ukjent') as land,
                COUNT(*) as antall,
                AVG(lonn) as snitt,
                MIN(lonn) as min,
                MAX(lonn) as maks,
                SUM(lonn) as total
            FROM ansatte {where}
            GROUP BY land
            ORDER BY snitt DESC
        """)
        
        return {
            row['land']: {
                'antall': row['antall'],
                'gjennomsnitt': round(row['snitt'], 0),
                'min': row['min'],
                'maks': row['maks'],
                'total_lonnsmasse': round(row['total'], 0)
            }
            for row in rows
        }
    
    def salary_by_gender(self, active_only: bool = True) -> Dict[str, Dict]:
        """Gjennomsnittlig lønn per kjønn (lønnslikestilling)."""
        where = "WHERE er_aktiv = 1 AND lonn IS NOT NULL" if active_only else "WHERE lonn IS NOT NULL"
        
        rows = self._query(f"""
            SELECT 
                COALESCE(kjonn, 'Ukjent') as kjonn,
                COUNT(*) as antall,
                AVG(lonn) as snitt,
                MIN(lonn) as min,
                MAX(lonn) as maks
            FROM ansatte {where}
            GROUP BY kjonn
        """)
        
        result = {
            row['kjonn']: {
                'antall': row['antall'],
                'gjennomsnitt': round(row['snitt'], 0),
                'min': row['min'],
                'maks': row['maks']
            }
            for row in rows
        }
        
        # Beregn lønnsgap hvis begge kjønn finnes
        if 'Mann' in result and 'Kvinne' in result:
            m_snitt = result['Mann']['gjennomsnitt']
            k_snitt = result['Kvinne']['gjennomsnitt']
            if m_snitt > 0:
                gap_pct = round((m_snitt - k_snitt) / m_snitt * 100, 1)
                result['lønnsgap_pct'] = gap_pct
                result['lønnsgap_beskrivelse'] = f"Kvinner tjener {abs(gap_pct)}% {'mindre' if gap_pct > 0 else 'mer'} enn menn"
        
        return result
    
    def salary_by_age(self, active_only: bool = True) -> Dict[str, Dict]:
        """Gjennomsnittlig lønn per alderskategori."""
        where = "WHERE er_aktiv = 1 AND lonn IS NOT NULL AND alder IS NOT NULL" if active_only else "WHERE lonn IS NOT NULL AND alder IS NOT NULL"
        
        rows = self._query(f"SELECT alder, lonn FROM ansatte {where}")
        
        by_category = defaultdict(list)
        for row in rows:
            cat = get_age_category(row['alder'])
            by_category[cat].append(row['lonn'])
        
        return {
            cat: {
                'antall': len(salaries),
                'gjennomsnitt': round(sum(salaries) / len(salaries), 0),
                'min': min(salaries),
                'maks': max(salaries)
            }
            for cat, salaries in by_category.items()
        }
    
    def salary_by_job_family(self, active_only: bool = True) -> Dict[str, Dict]:
        """Gjennomsnittlig lønn per jobbfamilie."""
        where = "WHERE er_aktiv = 1 AND lonn IS NOT NULL AND jobbfamilie IS NOT NULL" if active_only else "WHERE lonn IS NOT NULL AND jobbfamilie IS NOT NULL"
        
        rows = self._query(f"""
            SELECT 
                jobbfamilie,
                COUNT(*) as antall,
                AVG(lonn) as snitt,
                MIN(lonn) as min,
                MAX(lonn) as maks
            FROM ansatte {where}
            GROUP BY jobbfamilie
            ORDER BY snitt DESC
        """)
        
        return {
            row['jobbfamilie']: {
                'antall': row['antall'],
                'gjennomsnitt': round(row['snitt'], 0),
                'min': row['min'],
                'maks': row['maks']
            }
            for row in rows
        }
    
    # === JOBBFAMILIE-ANALYSE ===
    
    def job_family_distribution(self, active_only: bool = True) -> Dict[str, int]:
        """Fordeling av ansatte per jobbfamilie."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT COALESCE(jobbfamilie, 'Ikke angitt') as jobbfamilie, COUNT(*) as antall 
            FROM ansatte {where}
            GROUP BY jobbfamilie
            ORDER BY antall DESC
        """)
        return {row['jobbfamilie']: row['antall'] for row in rows}
    
    def job_family_by_country(self, active_only: bool = True) -> Dict[str, Dict[str, int]]:
        """Jobbfamilier fordelt per land."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT 
                COALESCE(arbeidsland, 'Ukjent') as land,
                COALESCE(jobbfamilie, 'Ikke angitt') as jobbfamilie,
                COUNT(*) as antall
            FROM ansatte {where}
            GROUP BY land, jobbfamilie
        """)
        
        result = defaultdict(dict)
        for row in rows:
            result[row['land']][row['jobbfamilie']] = row['antall']
        
        return dict(result)
    
    def job_family_by_gender(self, active_only: bool = True) -> Dict[str, Dict[str, int]]:
        """Kjønnsfordeling per jobbfamilie."""
        where = "WHERE er_aktiv = 1" if active_only else ""
        rows = self._query(f"""
            SELECT 
                COALESCE(jobbfamilie, 'Ikke angitt') as jobbfamilie,
                COALESCE(kjonn, 'Ukjent') as kjonn,
                COUNT(*) as antall
            FROM ansatte {where}
            GROUP BY jobbfamilie, kjonn
        """)
        
        result = defaultdict(lambda: {'Mann': 0, 'Kvinne': 0, 'Ukjent': 0})
        for row in rows:
            result[row['jobbfamilie']][row['kjonn']] = row['antall']
        
        # Legg til prosenter
        for jf in result:
            total = sum(result[jf].values())
            result[jf]['total'] = total
            result[jf]['kvinne_andel_pct'] = round(result[jf]['Kvinne'] / total * 100, 1) if total > 0 else 0
        
        return dict(result)


# Hjelpefunksjoner for enkel bruk
def get_analytics(db_path: Optional[Path] = None) -> HRAnalytics:
    """Opprett en HRAnalytics-instans."""
    return HRAnalytics(db_path)
