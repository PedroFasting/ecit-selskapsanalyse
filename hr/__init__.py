"""
HR Database - Verktøy for analyse av ansattdata.

Moduler:
- database: Database-håndtering
- importer: Excel-import
- analytics: Statistikk og analyse
"""

from .database import init_database, get_connection, reset_database
from .importer import import_excel, list_imports, ImportResult, ImportValidation
from .analytics import HRAnalytics, get_analytics
from .analyzer import (
    run_analysis, build_analysis_query, get_filter_values,
    METRICS, DIMENSIONS, FILTERS,
)
from .report_generator import generate_report

__version__ = "1.0.0"
__all__ = [
    'init_database',
    'get_connection', 
    'reset_database',
    'import_excel',
    'list_imports',
    'ImportResult',
    'ImportValidation',
    'HRAnalytics',
    'get_analytics',
    'run_analysis',
    'build_analysis_query',
    'get_filter_values',
    'METRICS',
    'DIMENSIONS',
    'FILTERS',
    'generate_report',
]
