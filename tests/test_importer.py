"""Tests for hr.importer module."""

from pathlib import Path
from datetime import datetime

import pytest
import pandas as pd

from hr.importer import (
    parse_date, clean_value, COLUMN_MAPPING,
    validate_columns, build_warnings,
    ImportValidation, ImportResult,
)


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


class TestValidateColumns:
    """Tests for validate_columns() — column matching logic."""

    def test_full_match(self):
        """All expected columns present gives 100% match."""
        columns = pd.Index(list(COLUMN_MAPPING.keys()))
        result = validate_columns(columns)
        assert result.match_ratio == 1.0
        assert len(result.missing_columns) == 0
        assert len(result.matched_columns) == len(COLUMN_MAPPING)

    def test_zero_match(self):
        """Completely unrecognized columns give 0% match."""
        columns = pd.Index(["Foo", "Bar", "Baz"])
        result = validate_columns(columns)
        assert result.match_ratio == 0.0
        assert len(result.matched_columns) == 0
        assert len(result.missing_columns) == len(COLUMN_MAPPING)
        assert set(result.unknown_columns) == {"Foo", "Bar", "Baz"}

    def test_partial_match(self):
        """Some matched, some missing, some unknown."""
        columns = pd.Index(["Fornavn", "Etternavn", "UnknownCol"])
        result = validate_columns(columns)
        assert set(result.matched_columns) == {"Fornavn", "Etternavn"}
        assert "UnknownCol" in result.unknown_columns
        assert "Fornavn" not in result.missing_columns
        assert "Lønn" in result.missing_columns
        assert 0 < result.match_ratio < 1.0

    def test_match_ratio_calculation(self):
        """match_ratio = matched / total expected."""
        # Take exactly half the expected columns
        all_keys = sorted(COLUMN_MAPPING.keys())
        half = all_keys[:len(all_keys) // 2]
        columns = pd.Index(half)
        result = validate_columns(columns)
        expected_ratio = len(half) / len(COLUMN_MAPPING)
        assert abs(result.match_ratio - expected_ratio) < 0.01

    def test_ignores_none_and_empty_columns(self):
        """None and empty-string headers are ignored."""
        columns = pd.Index([None, "", "Fornavn", "  "])
        result = validate_columns(columns)
        assert "Fornavn" in result.matched_columns
        assert None not in result.unknown_columns
        assert "" not in result.unknown_columns

    def test_unknown_columns_detected(self):
        """Columns not in COLUMN_MAPPING are reported as unknown."""
        columns = pd.Index(["Fornavn", "CustomCol1", "CustomCol2"])
        result = validate_columns(columns)
        assert "CustomCol1" in result.unknown_columns
        assert "CustomCol2" in result.unknown_columns


class TestBuildWarnings:
    """Tests for build_warnings() — warning message generation."""

    def test_no_warnings_on_full_match(self):
        """100% match produces no warnings."""
        validation = ImportValidation(
            matched_columns=list(COLUMN_MAPPING.keys()),
            missing_columns=[],
            unknown_columns=[],
            match_ratio=1.0,
        )
        assert build_warnings(validation) == []

    def test_zero_match_warning(self):
        """0% match produces a red-level warning."""
        validation = ImportValidation(
            matched_columns=[],
            missing_columns=list(COLUMN_MAPPING.keys()),
            unknown_columns=["X", "Y"],
            match_ratio=0.0,
        )
        warnings = build_warnings(validation)
        assert len(warnings) == 1
        assert "Ingen av" in warnings[0]
        assert "VerismoHR" in warnings[0]

    def test_low_match_warning(self):
        """<50% match produces a 'mye data vil mangle' warning."""
        all_keys = sorted(COLUMN_MAPPING.keys())
        few = all_keys[:3]
        rest = all_keys[3:]
        validation = ImportValidation(
            matched_columns=few,
            missing_columns=rest,
            unknown_columns=[],
            match_ratio=len(few) / len(COLUMN_MAPPING),
        )
        warnings = build_warnings(validation)
        assert len(warnings) == 1
        assert "Kun" in warnings[0]
        assert "Mye data vil mangle" in warnings[0]

    def test_partial_match_lists_missing(self):
        """50-99% match lists missing column names."""
        all_keys = sorted(COLUMN_MAPPING.keys())
        most = all_keys[:len(all_keys) - 3]
        missing = all_keys[len(all_keys) - 3:]
        validation = ImportValidation(
            matched_columns=most,
            missing_columns=missing,
            unknown_columns=[],
            match_ratio=len(most) / len(COLUMN_MAPPING),
        )
        warnings = build_warnings(validation)
        assert len(warnings) == 1
        assert "kolonner mangler" in warnings[0]

    def test_many_missing_truncated(self):
        """More than 5 missing columns are truncated with '... og N til'."""
        matched = ["Fornavn"]
        # Create 10 fake missing columns
        missing = [f"Missing{i}" for i in range(10)]
        validation = ImportValidation(
            matched_columns=matched,
            missing_columns=missing,
            unknown_columns=[],
            match_ratio=0.6,  # above 50% threshold
        )
        warnings = build_warnings(validation)
        assert len(warnings) == 1
        assert "og 5 til" in warnings[0]


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_default_warnings(self):
        """ImportResult defaults to empty warnings list."""
        validation = ImportValidation(
            matched_columns=[], missing_columns=[], unknown_columns=[], match_ratio=0.0,
        )
        result = ImportResult(imported=10, errors=0, validation=validation)
        assert result.warnings == []

    def test_fields_accessible(self):
        validation = ImportValidation(
            matched_columns=["Fornavn"],
            missing_columns=["Lønn"],
            unknown_columns=["Extra"],
            match_ratio=0.5,
        )
        result = ImportResult(
            imported=42,
            errors=3,
            validation=validation,
            warnings=["Test warning"],
        )
        assert result.imported == 42
        assert result.errors == 3
        assert result.validation.match_ratio == 0.5
        assert result.warnings == ["Test warning"]
