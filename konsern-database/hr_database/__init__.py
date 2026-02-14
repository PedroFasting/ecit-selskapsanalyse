"""
HR Database - Verktøy for analyse av ansattdata.

Moduler:
- database: Database-håndtering
- importer: Excel-import
- analytics: Statistikk og analyse
"""

from .database import init_database, get_connection, reset_database
from .importer import import_excel, list_imports
from .analytics import HRAnalytics, get_analytics

__version__ = "1.0.0"
__all__ = [
    'init_database',
    'get_connection', 
    'reset_database',
    'import_excel',
    'list_imports',
    'HRAnalytics',
    'get_analytics',
]
