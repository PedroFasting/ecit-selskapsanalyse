#!/usr/bin/env python3
"""Test-script for HR-databasen."""

import sys
sys.path.insert(0, '/Users/pedrofasting/VS code dokumenter/konsern-database')

from hr_database import init_database, import_excel, get_analytics

# Initialiser og importer
init_database()
count = import_excel('/Users/pedrofasting/VS code dokumenter/konsern-database/VerismoHR-Export-20260213152527_test Pedro.xlsx', clear_existing=True)
print(f'\nImporterte {count} ansatte\n')

# Test analytics
analytics = get_analytics()
print('=== OVERSIKT ===')
summary = analytics.employees_summary()
for k, v in summary.items():
    print(f'  {k}: {v}')

print('\n=== ALDERSFORDELING ===')
age_dist = analytics.age_distribution()
for cat, cnt in age_dist.items():
    if cnt > 0:
        print(f'  {cat}: {cnt}')

print('\n=== PER LAND ===')
by_country = analytics.employees_by_country()
for country, cnt in by_country.items():
    print(f'  {country}: {cnt}')

print('\n=== PER SELSKAP ===')
by_company = analytics.employees_by_company()
for company, cnt in by_company.items():
    print(f'  {company}: {cnt}')

print('\n=== KJØNN ===')
gender = analytics.gender_distribution()
for g, cnt in gender.items():
    print(f'  {g}: {cnt}')

print('\n=== CHURN 2025-2026 ===')
churn = analytics.calculate_churn('2025-01-01', '2026-12-31')
for k, v in churn.items():
    print(f'  {k}: {v}')
