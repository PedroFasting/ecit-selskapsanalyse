"""
Rapportgenerator - Genererer PDF-rapport med grafer fra HR-analyse.

Bruker matplotlib til å lage profesjonelle grafer som samles i én PDF.
"""

import os
from datetime import datetime, date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for PDF generation

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as ticker


# -- Konsistent fargepalett --
COLORS = {
    'primary': '#2E5090',
    'secondary': '#4A90D9',
    'accent': '#E8913A',
    'positive': '#5BA55B',
    'negative': '#D94A4A',
    'neutral': '#888888',
    'male': '#4A90D9',
    'female': '#E8913A',
    'unknown': '#BBBBBB',
}

CATEGORY_PALETTE = [
    '#2E5090', '#E8913A', '#5BA55B', '#D94A4A', '#8E6BBF',
    '#4ABBD9', '#D9A84A', '#6BBF8E', '#BF6B8E', '#90A02E',
]

# Norske etiketter
LABELS = {
    'Mann': 'Menn',
    'Kvinne': 'Kvinner',
    'Ukjent': 'Ukjent',
}


def _setup_figure(title: str, figsize=(10, 6)):
    """Opprett en figur med konsistent stil."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    return fig, ax


def _add_bar_labels(ax, bars, fmt='{:.0f}'):
    """Legg til verdi-etiketter over stolper."""
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.annotate(fmt.format(height),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 4), textcoords='offset points',
                        ha='center', va='bottom', fontsize=9)


def _save_page(pdf, fig):
    """Lagre figur til PDF og lukk."""
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    pdf.savefig(fig)
    plt.close(fig)


# ============================================================
# Individuelle grafer
# ============================================================

def plot_employees_by_country(analytics, pdf):
    """Stolpediagram: Ansatte per land."""
    data = analytics.employees_by_country(active_only=True)
    if not data:
        return

    # Sorter synkende
    countries = sorted(data.keys(), key=lambda c: data[c], reverse=True)
    counts = [data[c] for c in countries]

    fig, ax = _setup_figure('Aktive ansatte per land')
    bars = ax.bar(countries, counts, color=COLORS['primary'], edgecolor='white')
    _add_bar_labels(ax, bars)
    ax.set_ylabel('Antall ansatte')
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    _save_page(pdf, fig)


def plot_gender_distribution(analytics, pdf):
    """Kakediagram: Total kjønnsfordeling + stolpediagram per land."""
    total = analytics.gender_distribution(active_only=True)
    by_country = analytics.gender_by_country(active_only=True)

    if not total:
        return

    # -- Side 1: Kakediagram totalt --
    fig, ax = _setup_figure('Kjønnsfordeling (aktive)', figsize=(8, 6))

    labels_order = ['Mann', 'Kvinne', 'Ukjent']
    values = [total.get(g, 0) for g in labels_order]
    colors = [COLORS['male'], COLORS['female'], COLORS['unknown']]

    # Fjern kategorier med 0
    filtered = [(l, v, c) for l, v, c in zip(labels_order, values, colors) if v > 0]
    if filtered:
        labels_f, values_f, colors_f = zip(*filtered)
        wedges, texts, autotexts = ax.pie(
            values_f, labels=[LABELS.get(l, l) for l in labels_f],
            colors=colors_f, autopct='%1.1f%%',
            startangle=90, pctdistance=0.75)
        for t in autotexts:
            t.set_fontsize(11)
            t.set_fontweight('bold')
    _save_page(pdf, fig)

    # -- Side 2: Stablet stolpe per land --
    if not by_country:
        return

    countries = sorted(by_country.keys())
    men = [by_country[c].get('Mann', 0) for c in countries]
    women = [by_country[c].get('Kvinne', 0) for c in countries]
    unknown = [by_country[c].get('Ukjent', 0) for c in countries]

    fig, ax = _setup_figure('Kjønnsfordeling per land')
    x = range(len(countries))
    bar_w = 0.6

    b1 = ax.bar(x, men, bar_w, label='Menn', color=COLORS['male'])
    b2 = ax.bar(x, women, bar_w, bottom=men, label='Kvinner', color=COLORS['female'])
    if any(u > 0 for u in unknown):
        bottoms = [m + w for m, w in zip(men, women)]
        ax.bar(x, unknown, bar_w, bottom=bottoms, label='Ukjent', color=COLORS['unknown'])

    ax.set_xticks(x)
    ax.set_xticklabels(countries)
    ax.set_ylabel('Antall ansatte')
    ax.legend()
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    _save_page(pdf, fig)


def plot_age_distribution(analytics, pdf):
    """Stolpediagram: Aldersfordeling."""
    data = analytics.age_distribution(active_only=True)
    if not data:
        return

    # Behold rekkefølge (Under 25, 25-34, ...)
    categories = list(data.keys())
    counts = list(data.values())

    # Fjern "Ukjent" om den er 0
    if categories[-1] == 'Ukjent' and counts[-1] == 0:
        categories = categories[:-1]
        counts = counts[:-1]

    fig, ax = _setup_figure('Aldersfordeling (aktive)')
    bars = ax.bar(categories, counts, color=COLORS['secondary'], edgecolor='white')
    _add_bar_labels(ax, bars)
    ax.set_ylabel('Antall ansatte')
    ax.set_xlabel('Alderskategori')
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    _save_page(pdf, fig)


def plot_monthly_churn(analytics, pdf, year: int = None):
    """Linjediagram: Månedlig churn (sluttet vs nyansatte)."""
    if year is None:
        year = date.today().year

    data = analytics.monthly_churn(year)
    if not data:
        return

    months = [d['måned'][-2:] for d in data]  # '01', '02', ...
    sluttet = [d['sluttet'] for d in data]
    nyansatte = [d['nyansatte'] for d in data]
    netto = [d['netto'] for d in data]

    fig, ax = _setup_figure(f'Månedlig churn — {year}')
    ax.plot(months, sluttet, 'o-', color=COLORS['negative'], label='Sluttet', linewidth=2)
    ax.plot(months, nyansatte, 's-', color=COLORS['positive'], label='Nyansatte', linewidth=2)
    ax.plot(months, netto, '^--', color=COLORS['neutral'], label='Netto', linewidth=1.5, alpha=0.7)
    ax.axhline(y=0, color='#CCCCCC', linewidth=0.8)
    ax.set_xlabel('Måned')
    ax.set_ylabel('Antall')
    ax.legend()
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    _save_page(pdf, fig)


def plot_salary_analysis(analytics, pdf):
    """Lønnsanalyse: snitt per avdeling, per land, og per kjønn med lønnsgap."""
    # -- Per avdeling --
    by_dept = analytics.salary_by_department()
    if by_dept:
        depts = sorted(by_dept.keys(), key=lambda d: by_dept[d]['gjennomsnitt'], reverse=True)
        avgs = [by_dept[d]['gjennomsnitt'] for d in depts]

        fig, ax = _setup_figure('Gjennomsnittslønn per avdeling', figsize=(10, max(6, len(depts) * 0.5)))
        bars = ax.barh(depts, avgs, color=COLORS['primary'], edgecolor='white')
        for bar in bars:
            width = bar.get_width()
            ax.annotate(f'{width:,.0f}',
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=9)
        ax.set_xlabel('Gjennomsnittslønn (kr)')
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        ax.invert_yaxis()
        _save_page(pdf, fig)

    # -- Per land --
    by_country = analytics.salary_by_country()
    if by_country:
        countries = sorted(by_country.keys(), key=lambda c: by_country[c]['gjennomsnitt'], reverse=True)
        avgs = [by_country[c]['gjennomsnitt'] for c in countries]

        fig, ax = _setup_figure('Gjennomsnittslønn per land')
        bars = ax.bar(countries, avgs, color=COLORS['accent'], edgecolor='white')
        _add_bar_labels(ax, bars, fmt='{:,.0f}')
        ax.set_ylabel('Gjennomsnittslønn (kr)')
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        _save_page(pdf, fig)

    # -- Per kjønn med lønnsgap --
    by_gender = analytics.salary_by_gender()
    if by_gender and 'Mann' in by_gender and 'Kvinne' in by_gender:
        fig, ax = _setup_figure('Gjennomsnittslønn per kjønn')

        genders = ['Mann', 'Kvinne']
        avgs = [by_gender[g]['gjennomsnitt'] for g in genders]
        colors = [COLORS['male'], COLORS['female']]
        bars = ax.bar([LABELS[g] for g in genders], avgs, color=colors, edgecolor='white', width=0.5)
        _add_bar_labels(ax, bars, fmt='{:,.0f}')

        if 'lønnsgap_pct' in by_gender:
            gap = by_gender['lønnsgap_pct']
            desc = by_gender.get('lønnsgap_beskrivelse', '')
            ax.text(0.5, 0.02, f'Lønnsgap: {gap}% — {desc}',
                    transform=ax.transAxes, ha='center', fontsize=10,
                    style='italic', color=COLORS['neutral'])

        ax.set_ylabel('Gjennomsnittslønn (kr)')
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        _save_page(pdf, fig)


def plot_tenure_distribution(analytics, pdf):
    """Stolpediagram: Ansettelsestid-fordeling."""
    dist = analytics.tenure_distribution(active_only=True)
    if not dist:
        return

    categories = list(dist.keys())
    counts = list(dist.values())

    avg = analytics.average_tenure(active_only=True)

    fig, ax = _setup_figure('Fordeling av ansettelsestid (aktive)')
    bars = ax.bar(categories, counts, color=COLORS['positive'], edgecolor='white')
    _add_bar_labels(ax, bars)

    ax.set_ylabel('Antall ansatte')
    ax.set_xlabel('Ansettelsestid')
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    if avg is not None:
        ax.text(0.98, 0.95, f'Snitt: {avg:.1f} år',
                transform=ax.transAxes, ha='right', va='top',
                fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#F0F0F0', alpha=0.8))

    _save_page(pdf, fig)


def plot_job_family_distribution(analytics, pdf):
    """Stolpediagram: Ansatte per jobbfamilie."""
    dist = analytics.job_family_distribution(active_only=True)
    if not dist or (len(dist) == 1 and 'Ikke angitt' in dist):
        return

    # Sorter synkende, men hold "Ikke angitt" sist
    families = sorted(dist.keys(), key=lambda f: (f == 'Ikke angitt', -dist[f]))
    counts = [dist[f] for f in families]

    fig, ax = _setup_figure('Ansatte per jobbfamilie (aktive)',
                            figsize=(10, max(6, len(families) * 0.5)))
    colors = [COLORS['neutral'] if f == 'Ikke angitt' else CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)]
              for i, f in enumerate(families)]
    bars = ax.barh(families, counts, color=colors, edgecolor='white')
    for bar in bars:
        width = bar.get_width()
        if width > 0:
            ax.annotate(f'{width:.0f}',
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=9)
    ax.set_xlabel('Antall ansatte')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.invert_yaxis()
    _save_page(pdf, fig)


def plot_job_family_by_country(analytics, pdf):
    """Stablet stolpediagram: Jobbfamilier fordelt per land."""
    by_country = analytics.job_family_by_country(active_only=True)
    if not by_country:
        return

    countries = sorted(by_country.keys())
    # Samle alle jobbfamilier på tvers av land
    all_families = set()
    for families in by_country.values():
        all_families.update(families.keys())
    # Sorter, "Ikke angitt" sist
    all_families = sorted(all_families, key=lambda f: (f == 'Ikke angitt', f))

    fig, ax = _setup_figure('Jobbfamilier per land',
                            figsize=(max(10, len(countries) * 1.5), 7))
    x = range(len(countries))
    bottoms = [0] * len(countries)

    for i, family in enumerate(all_families):
        values = [by_country[c].get(family, 0) for c in countries]
        color = COLORS['neutral'] if family == 'Ikke angitt' else CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)]
        ax.bar(x, values, bottom=bottoms, label=family, color=color, edgecolor='white', width=0.7)
        bottoms = [b + v for b, v in zip(bottoms, values)]

    ax.set_xticks(x)
    ax.set_xticklabels(countries)
    ax.set_ylabel('Antall ansatte')
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    _save_page(pdf, fig)


def plot_job_family_gender(analytics, pdf):
    """Stolpediagram: Kvinneandel per jobbfamilie."""
    by_gender = analytics.job_family_by_gender(active_only=True)
    if not by_gender:
        return

    # Filtrer bort familier uten data
    families = [f for f, d in by_gender.items() if d.get('total', 0) > 0]
    if not families:
        return

    # Sorter på kvinneandel synkende
    families = sorted(families, key=lambda f: by_gender[f].get('kvinne_andel_pct', 0), reverse=True)
    pcts = [by_gender[f].get('kvinne_andel_pct', 0) for f in families]
    totals = [by_gender[f].get('total', 0) for f in families]

    fig, ax = _setup_figure('Kvinneandel per jobbfamilie',
                            figsize=(10, max(6, len(families) * 0.5)))

    colors = [COLORS['female'] if p >= 50 else COLORS['male'] for p in pcts]
    bars = ax.barh(families, pcts, color=colors, edgecolor='white', alpha=0.85)

    for bar, total in zip(bars, totals):
        width = bar.get_width()
        ax.annotate(f'{width:.0f}% (n={total})',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0), textcoords='offset points',
                    ha='left', va='center', fontsize=9)

    ax.set_xlabel('Kvinneandel (%)')
    ax.set_xlim(0, max(pcts) * 1.25 if pcts else 100)
    ax.axvline(x=50, color=COLORS['neutral'], linestyle='--', linewidth=0.8, alpha=0.6)
    ax.invert_yaxis()
    _save_page(pdf, fig)


# ============================================================
# Forside
# ============================================================

def _add_cover_page(analytics, pdf):
    """Lag en forside med nøkkeltall."""
    fig = plt.figure(figsize=(10, 6))
    fig.patch.set_facecolor('white')

    # Tittel
    fig.text(0.5, 0.85, 'HR-RAPPORT', fontsize=24, fontweight='bold',
             ha='center', color=COLORS['primary'])
    fig.text(0.5, 0.78, datetime.now().strftime('%d. %B %Y'),
             fontsize=12, ha='center', color=COLORS['neutral'])

    # Nøkkeltall
    try:
        summary = analytics.employees_summary()
        manager = analytics.manager_ratio()
        avg_tenure = analytics.average_tenure(active_only=True)

        metrics = [
            ('Totalt ansatte', str(summary.get('totalt', '-'))),
            ('Aktive', str(summary.get('aktive', '-'))),
            ('Sluttede', str(summary.get('sluttede', '-'))),
            ('Snittalder', f"{summary.get('gjennomsnitt_alder', '-')} år"),
            ('Snitt ansettelsestid', f'{avg_tenure:.1f} år' if avg_tenure else '-'),
            ('Lederandel', f"{manager.get('leder_andel_pct', '-')}%"),
        ]

        y_start = 0.60
        for i, (label, value) in enumerate(metrics):
            y = y_start - i * 0.08
            fig.text(0.35, y, label, fontsize=12, ha='right', color=COLORS['neutral'])
            fig.text(0.40, y, value, fontsize=12, ha='left', fontweight='bold',
                     color=COLORS['primary'])
    except Exception:
        fig.text(0.5, 0.5, 'Kunne ikke hente nøkkeltall', fontsize=12,
                 ha='center', color=COLORS['negative'])

    fig.text(0.5, 0.05, 'Generert av HR Database Analyseverktøy',
             fontsize=9, ha='center', color=COLORS['neutral'])

    pdf.savefig(fig)
    plt.close(fig)


# ============================================================
# Hovedfunksjon
# ============================================================

def generate_report(analytics, output_path: str = None, year: int = None) -> str:
    """
    Generer en komplett HR-rapport som PDF.

    Args:
        analytics: HRAnalytics-instans
        output_path: Sti for PDF-filen. Standard: ./rapporter/hr_rapport_YYYY-MM-DD.pdf
        year: År for churn-analyse. Standard: inneværende år.

    Returns:
        Absolutt sti til den genererte PDF-filen.
    """
    if year is None:
        year = date.today().year

    if output_path is None:
        rapport_dir = Path(__file__).parent.parent / 'data' / 'rapporter'
        rapport_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(rapport_dir / f'hr_rapport_{date.today().isoformat()}.pdf')

    with PdfPages(output_path) as pdf:
        _add_cover_page(analytics, pdf)
        plot_employees_by_country(analytics, pdf)
        plot_gender_distribution(analytics, pdf)
        plot_age_distribution(analytics, pdf)
        plot_monthly_churn(analytics, pdf, year=year)
        plot_salary_analysis(analytics, pdf)
        plot_tenure_distribution(analytics, pdf)
        plot_job_family_distribution(analytics, pdf)
        plot_job_family_by_country(analytics, pdf)
        plot_job_family_gender(analytics, pdf)

    return os.path.abspath(output_path)
