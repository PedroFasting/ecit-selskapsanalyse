#!/usr/bin/env python3
"""
HR Database CLI - Interaktivt terminalprogram for HR-analyse.

Bruk: python hr_cli.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date

# Legg til prosjektmappen i path
sys.path.insert(0, str(Path(__file__).parent))

from hr_database import (
    init_database, import_excel, list_imports, 
    get_analytics, reset_database, generate_report
)


def clear_screen():
    """Tøm terminalskjermen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Print en fin overskrift."""
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_table(headers: list, rows: list, widths: list = None):
    """Print en enkel tabell."""
    if not widths:
        widths = [max(len(str(h)), max(len(str(r[i])) for r in rows) if rows else 5) + 2 
                  for i, h in enumerate(headers)]
    
    # Header
    header_line = "".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-" * sum(widths))
    
    # Rader
    for row in rows:
        row_line = "".join(str(c).ljust(w) for c, w in zip(row, widths))
        print(row_line)


def print_dict(data: dict, title: str = None, indent: int = 2):
    """Print en dict som tabell."""
    if title:
        print(f"\n{title}:")
    
    max_key = max(len(str(k)) for k in data.keys()) if data else 10
    
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{' ' * indent}{key}:")
            print_dict(value, indent=indent + 2)
        else:
            print(f"{' ' * indent}{str(key).ljust(max_key + 2)}: {value}")


class HRCLI:
    """Hovedklasse for CLI-applikasjonen."""
    
    def __init__(self):
        self.analytics = None
        self._init_analytics()
    
    def _init_analytics(self):
        """Initialiser analytics hvis database eksisterer."""
        try:
            self.analytics = get_analytics()
            # Test om tabellen eksisterer
            self.analytics.total_employees()
        except Exception:
            self.analytics = None
    
    def run(self):
        """Kjør hovedløkken."""
        clear_screen()
        self.print_welcome()
        
        while True:
            choice = self.main_menu()
            
            if choice == '0':
                print("\nHa det!")
                break
            elif choice == '1':
                self.import_data()
            elif choice == '2':
                self.show_overview()
            elif choice == '3':
                self.age_analysis()
            elif choice == '4':
                self.geographic_analysis()
            elif choice == '5':
                self.churn_analysis()
            elif choice == '6':
                self.tenure_analysis()
            elif choice == '7':
                self.gender_analysis()
            elif choice == '8':
                self.search_employees()
            elif choice == '9':
                self.combined_analysis()
            elif choice == '10':
                self.planned_departures()
            elif choice == '11':
                self.salary_analysis()
            elif choice == '12':
                self.job_family_analysis()
            elif choice == '13':
                self.advanced_menu()
            else:
                print("Ugyldig valg, prøv igjen.")
            
            input("\nTrykk Enter for å fortsette...")
    
    def print_welcome(self):
        """Print velkomstmelding."""
        print("""
╔════════════════════════════════════════════════════════╗
║           HR DATABASE ANALYSEVERKØY v1.0               ║
║                                                        ║
║   Verktøy for analyse av ansattdata fra Excel          ║
╚════════════════════════════════════════════════════════╝
        """)
    
    def main_menu(self) -> str:
        """Vis hovedmeny og returner valg."""
        print_header("HOVEDMENY")
        
        if self.analytics:
            try:
                total = self.analytics.total_employees(active_only=False)
                active = self.analytics.total_employees(active_only=True)
                print(f"\n  Database: {total} ansatte ({active} aktive)")
            except Exception:
                print("\n  Database: Ikke initialisert")
        else:
            print("\n  Database: Ikke initialisert - importer data først")
        
        print("""
  [1] Importer data fra Excel
  [2] Vis oversikt
  [3] Aldersanalyse
  [4] Geografisk analyse (land/selskap)
  [5] Churn/turnover-analyse
  [6] Ansettelsestid/tenure
  [7] Kjønnsfordeling
  [8] Søk etter ansatte
  [9] Kombinerte analyser
  [10] Planlagte avganger
  [11] Lønnsanalyse
  [12] Jobbfamilier
  [13] Avansert...
  
  [0] Avslutt
        """)
        
        return input("Velg: ").strip()
    
    def import_data(self):
        """Importer data fra Excel."""
        print_header("IMPORTER DATA")
        
        # Vis tidligere importer
        imports = list_imports()
        if imports:
            print("\nTidligere importer:")
            for imp in imports[:5]:
                print(f"  - {imp['filnavn']} ({imp['antall_rader']} rader, {imp['importert_dato'][:10]})")
        
        print("\nSkriv sti til Excel-fil (eller 'avbryt'):")
        filepath = input("> ").strip()
        
        if filepath.lower() == 'avbryt':
            return
        
        # Fjern evt. fnutter
        filepath = filepath.strip("'\"")
        
        if not os.path.exists(filepath):
            print(f"\nFinner ikke fil: {filepath}")
            return
        
        print("\nSlett eksisterende data først? (j/n)")
        clear = input("> ").strip().lower() == 'j'
        
        try:
            result = import_excel(filepath, clear_existing=clear, verbose=True)
            print(f"\n✓ Importert {result.imported} ansatte")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
            self._init_analytics()
        except Exception as e:
            print(f"\n✗ Feil ved import: {e}")
    
    def show_overview(self):
        """Vis generell oversikt."""
        if not self._check_data():
            return
        
        print_header("OVERSIKT")
        
        summary = self.analytics.employees_summary()
        print_dict(summary, "Ansatte")
        
        # Fordeling per selskap
        by_company = self.analytics.employees_by_company()
        if by_company:
            print_dict(by_company, "\nPer selskap")
        
        # Ansettelsestyper
        emp_types = self.analytics.employment_type_distribution()
        if emp_types:
            print_dict(emp_types, "\nAnsettelsestyper")
        
        # Leder-ratio
        manager = self.analytics.manager_ratio()
        print(f"\nLedere: {manager['ledere']} ({manager['leder_andel_pct']}%)")
        print(f"Ansatte per leder: {manager['ansatte_per_leder']}")
    
    def age_analysis(self):
        """Aldersanalyse."""
        if not self._check_data():
            return
        
        print_header("ALDERSANALYSE")
        
        # Total fordeling
        dist = self.analytics.age_distribution()
        pct = self.analytics.age_distribution_pct()
        
        print("\nAldersfordeling (aktive ansatte):")
        headers = ["Kategori", "Antall", "Prosent"]
        rows = [(k, dist[k], f"{pct[k]}%") for k in dist.keys() if dist[k] > 0]
        print_table(headers, rows, [15, 10, 10])
        
        # Per land
        print("\nVil du se fordeling per land? (j/n)")
        if input("> ").strip().lower() == 'j':
            by_country = self.analytics.age_distribution_by_country()
            for country, ages in by_country.items():
                print(f"\n  {country}:")
                for cat, count in ages.items():
                    if count > 0:
                        print(f"    {cat}: {count}")
    
    def geographic_analysis(self):
        """Geografisk analyse."""
        if not self._check_data():
            return
        
        print_header("GEOGRAFISK ANALYSE")
        
        # Per land
        by_country = self.analytics.employees_by_country()
        total = sum(by_country.values())
        
        print("\nAnsatte per land:")
        headers = ["Land", "Antall", "Andel"]
        rows = [(k, v, f"{round(v/total*100, 1)}%") for k, v in by_country.items()]
        print_table(headers, rows, [20, 10, 10])
        
        # Per selskap
        print("\nVil du se per juridisk selskap? (j/n)")
        if input("> ").strip().lower() == 'j':
            by_company = self.analytics.employees_by_company()
            print("\nAnsatte per selskap:")
            for company, count in by_company.items():
                print(f"  {company}: {count}")
        
        # Per avdeling
        print("\nVil du se per avdeling? (j/n)")
        if input("> ").strip().lower() == 'j':
            by_dept = self.analytics.employees_by_department()
            print("\nAnsatte per avdeling:")
            for dept, count in by_dept.items():
                print(f"  {dept}: {count}")
    
    def churn_analysis(self):
        """Churn/turnover analyse."""
        if not self._check_data():
            return
        
        print_header("CHURN / TURNOVER ANALYSE")
        
        current_year = datetime.now().year
        
        print(f"\n[1] Siste 12 måneder")
        print(f"[2] Inneværende år ({current_year})")
        print(f"[3] Forrige år ({current_year - 1})")
        print(f"[4] Egendefinert periode")
        print(f"[5] Månedlig oversikt for et år")
        
        choice = input("\nVelg: ").strip()
        
        if choice == '1':
            end = date.today()
            start = date(end.year - 1, end.month, end.day)
        elif choice == '2':
            start = date(current_year, 1, 1)
            end = date.today()
        elif choice == '3':
            start = date(current_year - 1, 1, 1)
            end = date(current_year - 1, 12, 31)
        elif choice == '4':
            print("Startdato (YYYY-MM-DD):")
            start = input("> ").strip()
            print("Sluttdato (YYYY-MM-DD):")
            end = input("> ").strip()
        elif choice == '5':
            print(f"Hvilket år? (standard: {current_year})")
            year = input("> ").strip() or str(current_year)
            monthly = self.analytics.monthly_churn(int(year))
            
            print(f"\nMånedlig churn for {year}:")
            headers = ["Måned", "Sluttet", "Nyansatt", "Netto"]
            rows = [(m['måned'], m['sluttet'], m['nyansatte'], m['netto']) for m in monthly]
            print_table(headers, rows, [12, 10, 10, 10])
            return
        else:
            print("Ugyldig valg")
            return
        
        start_str = str(start) if isinstance(start, date) else start
        end_str = str(end) if isinstance(end, date) else end
        
        # Total churn
        churn = self.analytics.calculate_churn(start_str, end_str)
        
        print(f"\nChurn for perioden {churn['periode']}:")
        print(f"  Antall sluttet: {churn['antall_sluttet']}")
        print(f"  Antall nyansatte: {churn['antall_nyansatte']}")
        print(f"  Gjennomsnittlig ansatte: {churn['gjennomsnittlig_ansatte']}")
        print(f"  Churn rate: {churn['churn_rate_pct']}%")
        print(f"  Netto endring: {churn['netto_endring']}")
        
        # Oppsigelsesårsaker
        print("\nVil du se oppsigelsesårsaker? (j/n)")
        if input("> ").strip().lower() == 'j':
            reasons = self.analytics.get_termination_reasons(start_str, end_str)
            print("\nOppsigelsesårsaker:")
            for reason, count in reasons.items():
                print(f"  {reason}: {count}")
    
    def tenure_analysis(self):
        """Analyse av ansettelsestid."""
        if not self._check_data():
            return
        
        print_header("ANSETTELSESTID / TENURE")
        
        avg = self.analytics.average_tenure()
        print(f"\nGjennomsnittlig ansettelsestid: {avg} år")
        
        dist = self.analytics.tenure_distribution()
        print("\nFordeling:")
        for category, count in dist.items():
            print(f"  {category}: {count}")
        
        # Heltid vs deltid
        ft_pt = self.analytics.fulltime_vs_parttime()
        print("\nHeltid vs deltid:")
        for typ, count in ft_pt.items():
            print(f"  {typ}: {count}")
    
    def gender_analysis(self):
        """Kjønnsfordeling."""
        if not self._check_data():
            return
        
        print_header("KJØNNSFORDELING")
        
        gender = self.analytics.gender_distribution()
        total = sum(gender.values())
        
        print("\nKjønnsfordeling (aktive):")
        for g, count in gender.items():
            pct = round(count / total * 100, 1) if total > 0 else 0
            print(f"  {g}: {count} ({pct}%)")
        
        # Per land
        print("\nVil du se per land? (j/n)")
        if input("> ").strip().lower() == 'j':
            by_country = self.analytics.gender_by_country()
            print("\nKjønnsfordeling per land:")
            for country, genders in by_country.items():
                total_c = sum(genders.values())
                print(f"\n  {country}:")
                for g, count in genders.items():
                    if count > 0:
                        pct = round(count / total_c * 100, 1)
                        print(f"    {g}: {count} ({pct}%)")
    
    def search_employees(self):
        """Søk etter ansatte."""
        if not self._check_data():
            return
        
        print_header("SØK ETTER ANSATTE")
        
        print("\nSøkekriterier (la tom for å hoppe over):")
        
        print("Navn:")
        name = input("> ").strip() or None
        
        print("Avdeling:")
        dept = input("> ").strip() or None
        
        print("Land:")
        country = input("> ").strip() or None
        
        print("Selskap:")
        company = input("> ").strip() or None
        
        print("Inkluder sluttede? (j/n)")
        active_only = input("> ").strip().lower() != 'j'
        
        results = self.analytics.search_employees(
            name=name,
            department=dept,
            country=country,
            company=company,
            active_only=active_only
        )
        
        if not results:
            print("\nIngen treff.")
            return
        
        print(f"\n{len(results)} treff:")
        headers = ["ID", "Navn", "Tittel", "Avdeling", "Land", "Aktiv"]
        rows = [
            (
                r['id'],
                f"{r['fornavn']} {r['etternavn']}",
                (r['tittel'] or '')[:25],
                (r['avdeling'] or '')[:15],
                r['arbeidsland'] or '',
                'Ja' if r['er_aktiv'] else 'Nei'
            )
            for r in results
        ]
        print_table(headers, rows, [6, 25, 27, 17, 12, 8])
    
    def advanced_menu(self):
        """Avansert meny."""
        print_header("AVANSERT")
        
        print("""
  [1] Initialiser ny database
  [2] Reset database (SLETTER ALLE DATA)
  [3] Se import-historikk
  [4] Eksporter rapport (PDF)
        """)
        
        choice = input("Velg: ").strip()
        
        if choice == '1':
            init_database()
            self._init_analytics()
            print("Database initialisert.")
        elif choice == '2':
            print("\nER DU SIKKER? Skriv 'JA SLETT' for å bekrefte:")
            if input("> ").strip() == 'JA SLETT':
                reset_database()
                self._init_analytics()
                print("Database slettet og opprettet på nytt.")
            else:
                print("Avbrutt.")
        elif choice == '3':
            imports = list_imports()
            if imports:
                headers = ["Fil", "Dato", "Rader", "Status"]
                rows = [(i['filnavn'][:30], i['importert_dato'][:16], i['antall_rader'], i['status']) 
                        for i in imports]
                print_table(headers, rows, [32, 18, 8, 10])
            else:
                print("Ingen importer ennå.")
        elif choice == '4':
            self._export_report()
    
    def combined_analysis(self):
        """Kombinerte analyser."""
        if not self._check_data():
            return
        
        print_header("KOMBINERTE ANALYSER")
        
        print("""
  [1] Alder + land (aldersfordeling per land)
  [2] Alder + churn (hvilke aldersgrupper slutter mest)
  [3] Churn + land (turnover per land)
  [4] Kjønn + churn (turnover per kjønn)
  [5] Land + kjønn + alder (full oversikt per land)
  [6] Sammendrag for ett land
        """)
        
        choice = input("Velg: ").strip()
        
        if choice == '1':
            # Alder per land
            by_country = self.analytics.age_distribution_by_country()
            print("\nAldersfordeling per land:")
            for country, ages in by_country.items():
                print(f"\n  {country}:")
                for cat, count in ages.items():
                    if count > 0:
                        print(f"    {cat}: {count}")
        
        elif choice == '2':
            # Alder + churn
            start, end = self._get_period()
            if not start:
                return
            
            churn_age = self.analytics.churn_by_age(start, end)
            print(f"\nChurn per alderskategori ({start} til {end}):")
            headers = ["Aldersgruppe", "Totalt", "Sluttet", "Churn %"]
            rows = [(cat, d['totalt'], d['sluttet'], f"{d['churn_rate_pct']}%") 
                    for cat, d in churn_age.items() if d['totalt'] > 0]
            print_table(headers, rows, [15, 10, 10, 10])
        
        elif choice == '3':
            # Churn per land
            start, end = self._get_period()
            if not start:
                return
            
            churn_country = self.analytics.churn_by_country(start, end)
            print(f"\nChurn per land ({start} til {end}):")
            headers = ["Land", "Totalt", "Sluttet", "Churn %"]
            rows = [(country, d['totalt'], d['sluttet'], f"{d['churn_rate_pct']}%") 
                    for country, d in churn_country.items()]
            print_table(headers, rows, [20, 10, 10, 10])
        
        elif choice == '4':
            # Kjønn + churn
            start, end = self._get_period()
            if not start:
                return
            
            churn_gender = self.analytics.churn_by_gender(start, end)
            print(f"\nChurn per kjønn ({start} til {end}):")
            headers = ["Kjønn", "Totalt", "Sluttet", "Churn %"]
            rows = [(gender, d['totalt'], d['sluttet'], f"{d['churn_rate_pct']}%") 
                    for gender, d in churn_gender.items()]
            print_table(headers, rows, [15, 10, 10, 10])
        
        elif choice == '5':
            # Full oversikt per land
            data = self.analytics.age_and_gender_by_country()
            print("\nFull oversikt per land:")
            for country, info in data.items():
                print(f"\n  === {country} ({info['total']} ansatte) ===")
                print(f"  Snitt alder: {info['snitt_alder']} år")
                print("  Kjønn:")
                for g, c in info['kjønn'].items():
                    if c > 0:
                        pct = round(c / info['total'] * 100, 1)
                        print(f"    {g}: {c} ({pct}%)")
                print("  Alder:")
                for cat, c in info['alder'].items():
                    if c > 0:
                        print(f"    {cat}: {c}")
        
        elif choice == '6':
            # Sammendrag for ett land
            countries = self.analytics.employees_by_country()
            print("\nTilgjengelige land:", ", ".join(countries.keys()))
            print("Velg land:")
            country_input = input("> ").strip()
            # Finn riktig land med case-insensitive matching
            country = None
            for c in countries:
                if c.lower() == country_input.lower():
                    country = c
                    break
            
            if country:
                summary = self.analytics.combined_summary(country=country)
                if 'feil' in summary:
                    print(f"\n{summary['feil']}")
                else:
                    print(f"\n=== {country} ===")
                    print(f"Antall: {summary['antall']}")
                    print(f"Snitt alder: {summary['snitt_alder']} år")
                    print("\nKjønn:")
                    for g, pct in summary['kjønn_pct'].items():
                        print(f"  {g}: {summary['kjønnsfordeling'][g]} ({pct}%)")
                    print("\nAlder:")
                    for cat, pct in summary['alder_pct'].items():
                        if pct > 0:
                            print(f"  {cat}: {summary['aldersfordeling'][cat]} ({pct}%)")
    
    def planned_departures(self):
        """Vis planlagte avganger."""
        if not self._check_data():
            return
        
        print_header("PLANLAGTE AVGANGER")
        
        print("Hvor mange måneder fremover? (standard: 12)")
        months = input("> ").strip()
        months = int(months) if months.isdigit() else 12
        
        departures = self.analytics.planned_departures(months_ahead=months)
        
        if not departures:
            print(f"\nIngen planlagte avganger de neste {months} månedene.")
            return
        
        print(f"\n{len(departures)} planlagte avganger de neste {months} månedene:")
        headers = ["Navn", "Tittel", "Avdeling", "Land", "Sluttdato"]
        rows = [
            (
                f"{d['fornavn']} {d['etternavn']}",
                (d['tittel'] or '')[:20],
                (d['avdeling'] or '')[:15],
                d['arbeidsland'] or '',
                d['slutdato_ansettelse']
            )
            for d in departures
        ]
        print_table(headers, rows, [25, 22, 17, 12, 12])
    
    def _get_period(self):
        """Hjelpefunksjon for å velge tidsperiode."""
        current_year = datetime.now().year
        
        print(f"\n[1] Siste 12 måneder")
        print(f"[2] Inneværende år ({current_year})")
        print(f"[3] Forrige år ({current_year - 1})")
        print(f"[4] Egendefinert periode")
        
        choice = input("\nVelg periode: ").strip()
        
        if choice == '1':
            end = date.today()
            start = date(end.year - 1, end.month, end.day)
        elif choice == '2':
            start = date(current_year, 1, 1)
            end = date.today()
        elif choice == '3':
            start = date(current_year - 1, 1, 1)
            end = date(current_year - 1, 12, 31)
        elif choice == '4':
            print("Startdato (YYYY-MM-DD):")
            start = input("> ").strip()
            print("Sluttdato (YYYY-MM-DD):")
            end = input("> ").strip()
            return start, end
        else:
            return None, None
        
        return str(start), str(end)
    
    def salary_analysis(self):
        """Lønnsanalyse."""
        if not self._check_data():
            return
        
        print_header("LØNNSANALYSE")
        
        # Sjekk om det finnes lønnsdata
        summary = self.analytics.salary_summary()
        if summary.get('antall_med_lonn', 0) == 0:
            print("\nIngen lønnsdata i databasen.")
            print("Sørg for at Excel-filen har en 'Lønn'-kolonne med data.")
            return
        
        print(f"\nLønnsdata tilgjengelig for {summary['antall_med_lonn']} ansatte")
        
        print("""
  [1] Lønnsoversikt (total)
  [2] Lønn per avdeling
  [3] Lønn per land
  [4] Lønn per kjønn (likestilling)
  [5] Lønn per alderskategori
  [6] Lønn per jobbfamilie
        """)
        
        choice = input("Velg: ").strip()
        
        if choice == '1':
            print("\nLønnsoversikt:")
            print(f"  Antall med lønn: {summary['antall_med_lonn']}")
            print(f"  Gjennomsnitt: {summary['gjennomsnitt']:,.0f}")
            print(f"  Min: {summary['min']:,.0f}")
            print(f"  Maks: {summary['maks']:,.0f}")
            print(f"  Total lønnsmasse: {summary['total_lonnsmasse']:,.0f}")
        
        elif choice == '2':
            by_dept = self.analytics.salary_by_department()
            print("\nLønn per avdeling:")
            headers = ["Avdeling", "Antall", "Snitt", "Min", "Maks"]
            rows = [(d[:20], data['antall'], f"{data['gjennomsnitt']:,.0f}", 
                    f"{data['min']:,.0f}", f"{data['maks']:,.0f}") 
                   for d, data in by_dept.items()]
            print_table(headers, rows, [22, 8, 12, 12, 12])
        
        elif choice == '3':
            by_country = self.analytics.salary_by_country()
            print("\nLønn per land:")
            headers = ["Land", "Antall", "Snitt", "Total lønnsmasse"]
            rows = [(c, data['antall'], f"{data['gjennomsnitt']:,.0f}", 
                    f"{data['total_lonnsmasse']:,.0f}") 
                   for c, data in by_country.items()]
            print_table(headers, rows, [15, 8, 12, 18])
        
        elif choice == '4':
            by_gender = self.analytics.salary_by_gender()
            print("\nLønn per kjønn:")
            for g, data in by_gender.items():
                if isinstance(data, dict):
                    print(f"\n  {g}:")
                    print(f"    Antall: {data['antall']}")
                    print(f"    Gjennomsnitt: {data['gjennomsnitt']:,.0f}")
                    print(f"    Min-Maks: {data['min']:,.0f} - {data['maks']:,.0f}")
                else:
                    print(f"\n  {g}: {data}")
            
            if 'lønnsgap_beskrivelse' in by_gender:
                print(f"\n  === LØNNSGAP ===")
                print(f"  {by_gender['lønnsgap_beskrivelse']}")
        
        elif choice == '5':
            by_age = self.analytics.salary_by_age()
            print("\nLønn per alderskategori:")
            headers = ["Alder", "Antall", "Snitt", "Min", "Maks"]
            rows = [(cat, data['antall'], f"{data['gjennomsnitt']:,.0f}", 
                    f"{data['min']:,.0f}", f"{data['maks']:,.0f}") 
                   for cat, data in by_age.items()]
            print_table(headers, rows, [12, 8, 12, 12, 12])
        
        elif choice == '6':
            by_jf = self.analytics.salary_by_job_family()
            if not by_jf:
                print("\nIngen jobbfamilie-data tilgjengelig.")
                return
            print("\nLønn per jobbfamilie:")
            headers = ["Jobbfamilie", "Antall", "Snitt", "Min", "Maks"]
            rows = [(jf[:25], data['antall'], f"{data['gjennomsnitt']:,.0f}", 
                    f"{data['min']:,.0f}", f"{data['maks']:,.0f}") 
                   for jf, data in by_jf.items()]
            print_table(headers, rows, [27, 8, 12, 12, 12])
    
    def job_family_analysis(self):
        """Jobbfamilie-analyse."""
        if not self._check_data():
            return
        
        print_header("JOBBFAMILIER")
        
        dist = self.analytics.job_family_distribution()
        if len(dist) == 1 and 'Ikke angitt' in dist:
            print("\nIngen jobbfamilie-data i databasen.")
            print("Sørg for at Excel-filen har en 'Jobbfamilie'-kolonne med data.")
            return
        
        print("""
  [1] Fordeling (antall per jobbfamilie)
  [2] Per land
  [3] Kjønnsfordeling per jobbfamilie
        """)
        
        choice = input("Velg: ").strip()
        
        if choice == '1':
            print("\nAnsatte per jobbfamilie:")
            total = sum(dist.values())
            for jf, count in dist.items():
                pct = round(count / total * 100, 1)
                print(f"  {jf}: {count} ({pct}%)")
        
        elif choice == '2':
            by_country = self.analytics.job_family_by_country()
            print("\nJobbfamilier per land:")
            for country, families in by_country.items():
                print(f"\n  === {country} ===")
                for jf, count in sorted(families.items(), key=lambda x: -x[1]):
                    print(f"    {jf}: {count}")
        
        elif choice == '3':
            by_gender = self.analytics.job_family_by_gender()
            print("\nKjønnsfordeling per jobbfamilie:")
            headers = ["Jobbfamilie", "Total", "Menn", "Kvinner", "Kvinneandel"]
            rows = [
                (jf[:25], data['total'], data['Mann'], data['Kvinne'], 
                 f"{data['kvinne_andel_pct']}%")
                for jf, data in by_gender.items()
            ]
            print_table(headers, rows, [27, 8, 8, 10, 12])
    
    def _export_report(self):
        """Eksporter HR-rapport som PDF."""
        if not self._check_data():
            return
        
        print("\nGenererer PDF-rapport...")
        print("(Standardplassering: rapporter/hr_rapport_DATO.pdf)")
        print("\nAngi filsti (eller trykk Enter for standard):")
        custom_path = input("> ").strip()
        
        output_path = custom_path if custom_path else None
        
        try:
            path = generate_report(self.analytics, output_path=output_path)
            print(f"\n✓ Rapport generert: {path}")
        except Exception as e:
            print(f"\n✗ Feil ved generering av rapport: {e}")
    
    def _check_data(self) -> bool:
        """Sjekk om det finnes data i databasen."""
        if not self.analytics:
            print("\nIngen data i databasen. Importer data først (valg 1).")
            return False
        
        try:
            count = self.analytics.total_employees(active_only=False)
            if count == 0:
                print("\nDatabasen er tom. Importer data først (valg 1).")
                return False
        except Exception:
            print("\nDatabase ikke initialisert. Importer data først (valg 1).")
            return False
        
        return True


def main():
    """Hovedfunksjon."""
    cli = HRCLI()
    cli.run()


if __name__ == "__main__":
    main()
