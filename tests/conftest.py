"""
Shared test fixtures for HR database tests.

Provides a temporary SQLite database pre-populated with known test data,
so every test runs against predictable, isolated data.
"""

import sqlite3
from pathlib import Path
from datetime import date, datetime

import pytest

from hr.database import init_database, get_connection
from hr.analytics import HRAnalytics


# ---------------------------------------------------------------------------
# Test data: 10 employees with enough variety to exercise all analytics
# ---------------------------------------------------------------------------
TEST_EMPLOYEES = [
    # (fornavn, etternavn, kjonn, alder, fodselsdato, nasjonalitet,
    #  arbeidsland, land, juridisk_selskap, avdeling, jobbfamilie,
    #  ansettelsetype, ansettelsens_startdato, slutdato_ansettelse,
    #  oppsigelsesarsak, arbeidstid_per_uke, heltid_per_uke,
    #  er_leder, lonn, medarbeidernummer, tittel,
    #  ansettelsesniva, arbeidssted, divisjon, rolle)
    ("Ola", "Nordmann", "Mann", 30, "1996-01-15", "Norsk",
     "Norge", "Norge", "ECIT AS", "Regnskap", "Finance",
     "Fast", "2020-01-01", None,
     None, 37.5, 37.5,
     "Nei", 550000, "M001", "Regnskapsfører",
     "Medarbeider", "Oslo", "Økonomi", "Regnskapsfører"),

    ("Kari", "Hansen", "Kvinne", 42, "1984-03-20", "Norsk",
     "Norge", "Norge", "ECIT AS", "Regnskap", "Finance",
     "Fast", "2018-06-01", None,
     None, 37.5, 37.5,
     "Ja", 720000, "M002", "Regnskapsleder",
     "Leder", "Oslo", "Økonomi", "Leder"),

    ("Erik", "Berg", "Mann", 55, "1971-07-10", "Norsk",
     "Norge", "Norway", "ECIT Consulting", "IT", "Technology",
     "Fast", "2015-03-15", None,
     None, 37.5, 37.5,
     "Nei", 680000, "M003", "Seniorkonsulent",
     "Senior", "Bergen", "Teknologi", "Konsulent"),

    ("Anna", "Jensen", "Kvinne", 28, "1998-05-22", "Dansk",
     "Danmark", "DK", "ECIT DK", "Regnskap", "Finance",
     "Fast", "2022-01-10", None,
     None, 37.0, 37.0,
     "Nei", 420000, "M004", "Regnskapsfører",
     "Medarbeider", "København", "Økonomi", "Regnskapsfører"),

    ("Lars", "Petersen", "Mann", 35, "1991-11-03", "Dansk",
     "Danmark", "Danmark", "ECIT DK", "Salg", "Commercial",
     "Fast", "2019-08-01", None,
     None, 37.0, 37.0,
     "Ja", 580000, "M005", "Salgssjef",
     "Leder", "København", "Salg", "Leder"),

    ("Sofia", "Lindqvist", "Kvinne", 38, "1988-09-14", "Svensk",
     "Sverige", "Sverige", "ECIT SE", "Regnskap", "Finance",
     "Fast", "2021-02-01", None,
     None, 40.0, 40.0,
     "Nei", 490000, "M006", "Regnskapsfører",
     "Medarbeider", "Stockholm", "Økonomi", "Regnskapsfører"),

    ("Morten", "Bakke", "Mann", 24, "2002-04-28", "Norsk",
     "Norge", "Norge", "ECIT AS", "IT", "Technology",
     "Vikar", "2024-06-01", None,
     None, 20.0, 37.5,
     "Nei", 300000, "M007", "Juniorutvikler",
     "Junior", "Oslo", "Teknologi", "Utvikler"),

    # Sluttet ansatt (terminert i 2025)
    ("Per", "Olsen", "Mann", 48, "1978-02-11", "Norsk",
     "Norge", "Norge", "ECIT AS", "Regnskap", "Finance",
     "Fast", "2017-01-15", "2025-06-30",
     "Frivillig", 37.5, 37.5,
     "Nei", 600000, "M008", "Controller",
     "Senior", "Oslo", "Økonomi", "Controller"),

    # Sluttet ansatt (terminert i 2024)
    ("Lise", "Dahl", "Kvinne", 33, "1993-08-19", "Dansk",
     "Danmark", "DK", "ECIT DK", "Regnskap", "Finance",
     "Fast", "2020-03-01", "2024-12-31",
     "Ufrivillig", 37.0, 37.0,
     "Nei", 440000, "M009", "Regnskapsfører",
     "Medarbeider", "København", "Økonomi", "Regnskapsfører"),

    # Planlagt avgang (slutdato i fremtiden)
    ("Vidar", "Holm", "Mann", 62, "1964-06-05", "Norsk",
     "Norge", "Norge", "ECIT Consulting", "IT", "Technology",
     "Fast", "2010-01-01", "2027-06-30",
     None, 37.5, 37.5,
     "Nei", 750000, "M010", "Sjefsarkitekt",
     "Senior", "Bergen", "Teknologi", "Arkitekt"),
]

EMPLOYEE_COLUMNS = [
    "fornavn", "etternavn", "kjonn", "alder", "fodselsdato", "nasjonalitet",
    "arbeidsland", "land", "juridisk_selskap", "avdeling", "jobbfamilie",
    "ansettelsetype", "ansettelsens_startdato", "slutdato_ansettelse",
    "oppsigelsesarsak", "arbeidstid_per_uke", "heltid_per_uke",
    "er_leder", "lonn", "medarbeidernummer", "tittel",
    "ansettelsesniva", "arbeidssted", "divisjon", "rolle",
]


def _compute_er_aktiv(slutdato: str | None) -> bool:
    """Mirror the import logic for computing er_aktiv."""
    if slutdato is None:
        return True
    try:
        return datetime.strptime(slutdato, "%Y-%m-%d").date() > date.today()
    except (ValueError, TypeError):
        return True


def seed_employees(db_path: Path) -> None:
    """Insert test employees into the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cols = EMPLOYEE_COLUMNS + ["er_aktiv", "kilde_fil"]
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO ansatte ({col_names}) VALUES ({placeholders})"

    for emp in TEST_EMPLOYEES:
        slutdato = emp[13]  # slutdato_ansettelse
        er_aktiv = _compute_er_aktiv(slutdato)
        values = list(emp) + [er_aktiv, "test_data.xlsx"]
        cursor.execute(sql, values)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(tmp_path) -> Path:
    """
    Create a temporary database with known test data.
    Returns the Path to the database file.
    """
    db_path = tmp_path / "test_ansatte.db"
    init_database(db_path)
    seed_employees(db_path)
    return db_path


@pytest.fixture
def analytics(test_db) -> HRAnalytics:
    """Return an HRAnalytics instance connected to the test database."""
    return HRAnalytics(db_path=test_db)


@pytest.fixture
def db_conn(test_db) -> sqlite3.Connection:
    """Return a raw connection to the test database (for verification)."""
    conn = get_connection(test_db)
    yield conn
    conn.close()
