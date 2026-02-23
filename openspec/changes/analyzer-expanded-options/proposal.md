# Proposal: Utvide analysatorens metrikker og dimensjoner

## Problemstilling
Den generiske analysatoren har 6 metrikker og 9 dimensjoner, men databasen inneholder mer data som ikke utnyttes. Viktige HR-KPIer som ansiennitet, arbeidstidsmønster, kjønnsbalanse og lederdekning mangler. Flere dimensjoner fra databasen (nasjonalitet, ansettelsesnivå, arbeidssted) er heller ikke tilgjengelige.

## Løsning
Utvide analysatoren med:
- **4 nye metrikker**: avg_tenure, avg_work_hours, pct_female, pct_leaders
- **4 nye dimensjoner**: tenure_gruppe, ansettelsesniva, nasjonalitet, arbeidssted
- **Oppdaterte dashboard-presets** som utnytter de nye mulighetene
- **Nytt "Mangfold"-preset** med fokus på kjønnsbalanse, nasjonalitet og aldersfordeling

## Status
**GODKJENT** — implementering starter.
