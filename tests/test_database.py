"""Tests for hr_database.database module."""

import sqlite3
from pathlib import Path

import pytest

from hr.database import init_database, reset_database, get_connection


class TestInitDatabase:
    """Tests for init_database()."""

    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        assert not db_path.exists()
        init_database(db_path)
        assert db_path.exists()

    def test_creates_ansatte_table(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ansatte'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_import_logg_table(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='import_logg'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_indexes(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_ansatte_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected = [
            "idx_ansatte_land",
            "idx_ansatte_arbeidsland",
            "idx_ansatte_juridisk_selskap",
            "idx_ansatte_avdeling",
            "idx_ansatte_slutdato",
            "idx_ansatte_startdato",
            "idx_ansatte_alder",
        ]
        for idx_name in expected:
            assert idx_name in indexes, f"Missing index: {idx_name}"

    def test_idempotent(self, tmp_path):
        """Running init_database twice should not fail."""
        db_path = tmp_path / "test.db"
        init_database(db_path)
        init_database(db_path)  # should not raise

    def test_ansatte_has_expected_columns(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ansatte)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        required = {
            "id", "fornavn", "etternavn", "kjonn", "alder",
            "arbeidsland", "land", "juridisk_selskap", "avdeling",
            "lonn", "er_aktiv", "medarbeidernummer",
            "ansettelsens_startdato", "slutdato_ansettelse",
        }
        for col in required:
            assert col in columns, f"Missing column: {col}"


class TestGetConnection:
    """Tests for get_connection()."""

    def test_returns_connection(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_row_factory_set(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestResetDatabase:
    """Tests for reset_database()."""

    def test_clears_data(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)

        # Insert a row
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO ansatte (fornavn, medarbeidernummer) VALUES ('Test', 'T001')"
        )
        conn.commit()
        conn.close()

        # Reset
        reset_database(db_path)

        # Verify empty
        conn = get_connection(db_path)
        count = conn.execute("SELECT COUNT(*) FROM ansatte").fetchone()[0]
        conn.close()
        assert count == 0

    def test_tables_still_exist(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        reset_database(db_path)

        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "ansatte" in tables
        assert "import_logg" in tables


class TestAlderskategorierSeed:
    """Tests for alderskategorier table creation and seed data."""

    def test_creates_alderskategorier_table(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alderskategorier'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_seed_creates_default_categories(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        rows = conn.execute(
            "SELECT min_alder, maks_alder, etikett FROM alderskategorier ORDER BY sortering"
        ).fetchall()
        conn.close()

        assert len(rows) == 6
        labels = [r["etikett"] for r in rows]
        assert labels == ["Under 25", "25-34", "35-44", "45-54", "55-64", "65+"]

    def test_seed_idempotent(self, tmp_path):
        """Running init_database twice should not duplicate seed data."""
        db_path = tmp_path / "test.db"
        init_database(db_path)
        init_database(db_path)
        conn = get_connection(db_path)
        count = conn.execute("SELECT COUNT(*) FROM alderskategorier").fetchone()[0]
        conn.close()
        assert count == 6

    def test_seed_boundaries_cover_full_range(self, tmp_path):
        """Verify default categories start at 0 and end at 150 (65+)."""
        db_path = tmp_path / "test.db"
        init_database(db_path)
        conn = get_connection(db_path)
        rows = conn.execute(
            "SELECT min_alder, maks_alder FROM alderskategorier ORDER BY sortering"
        ).fetchall()
        conn.close()

        assert rows[0]["min_alder"] == 0
        assert rows[-1]["maks_alder"] == 150
