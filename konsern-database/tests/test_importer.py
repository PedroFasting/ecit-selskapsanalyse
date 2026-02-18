"""Tests for hr_database.importer module."""

import sys
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from hr_database.importer import parse_date, clean_value, COLUMN_MAPPING


class TestParseDate:
    """Tests for date parsing from various formats."""

    def test_iso_format(self):
        assert parse_date("2024-01-15") == "2024-01-15"

    def test_norwegian_format(self):
        assert parse_date("15.01.2024") == "2024-01-15"

    def test_slash_format(self):
        assert parse_date("15/01/2024") == "2024-01-15"

    def test_dash_dmy_format(self):
        assert parse_date("15-01-2024") == "2024-01-15"

    def test_slash_ymd_format(self):
        assert parse_date("2024/01/15") == "2024-01-15"

    def test_datetime_object(self):
        dt = datetime(2024, 1, 15, 10, 30)
        assert parse_date(dt) == "2024-01-15"

    def test_none_returns_none(self):
        assert parse_date(None) is None

    def test_nan_returns_none(self):
        import numpy as np
        assert parse_date(np.nan) is None

    def test_empty_string_returns_none(self):
        assert parse_date("") is None

    def test_whitespace_string_returns_none(self):
        assert parse_date("   ") is None

    def test_invalid_string_returns_none(self):
        assert parse_date("not-a-date") is None


class TestCleanValue:
    """Tests for value cleaning."""

    def test_normal_string(self):
        assert clean_value("hello") == "hello"

    def test_strips_whitespace(self):
        assert clean_value("  hello  ") == "hello"

    def test_empty_string_becomes_none(self):
        assert clean_value("") is None

    def test_whitespace_only_becomes_none(self):
        assert clean_value("   ") is None

    def test_none_stays_none(self):
        assert clean_value(None) is None

    def test_nan_becomes_none(self):
        import numpy as np
        assert clean_value(np.nan) is None

    def test_float_nan_becomes_none(self):
        import numpy as np
        assert clean_value(float("nan")) is None

    def test_number_preserved(self):
        assert clean_value(42) == 42

    def test_float_preserved(self):
        assert clean_value(37.5) == 37.5


class TestColumnMapping:
    """Tests for the Excel-to-DB column mapping."""

    def test_mapping_is_not_empty(self):
        assert len(COLUMN_MAPPING) > 0

    def test_key_columns_mapped(self):
        """Critical columns should be present in the mapping."""
        db_columns = set(COLUMN_MAPPING.values())
        required = {
            "fornavn", "etternavn", "kjonn", "alder",
            "arbeidsland", "land", "medarbeidernummer",
            "ansettelsens_startdato", "slutdato_ansettelse",
            "lonn", "avdeling", "juridisk_selskap",
        }
        for col in required:
            assert col in db_columns, f"Missing DB column in mapping: {col}"

    def test_arbeidsland_mapped_from_land_with_space(self):
        """The trailing-space 'Land ' column should map to arbeidsland."""
        assert "Land " in COLUMN_MAPPING
        assert COLUMN_MAPPING["Land "] == "arbeidsland"

    def test_land_mapped_from_land_without_space(self):
        """The 'Land' column (no space) should map to land."""
        assert "Land" in COLUMN_MAPPING
        assert COLUMN_MAPPING["Land"] == "land"
