/**
 * app.js — Navigasjon, datahenting og UI-logikk for HR Analyse.
 */

// === STATE ===
const tabLoaded = {};  // Holder styr på hvilke tabs som har lastet data

// === API HELPERS ===

async function fetchData(url) {
    showLoader();
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`Feil ved henting av ${url}:`, err);
        return null;
    } finally {
        hideLoader();
    }
}

function showLoader() { document.getElementById('loader').classList.remove('hidden'); }
function hideLoader() { document.getElementById('loader').classList.add('hidden'); }

// === TAB NAVIGATION ===

function switchTab(tabName) {
    // Oppdater nav
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab[data-tab="${tabName}"]`)?.classList.add('active');

    // Oppdater innhold
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    document.getElementById(`tab-${tabName}`)?.classList.add('active');

    // Last data om ikke allerede gjort
    if (!tabLoaded[tabName]) {
        loadTabData(tabName);
    }

    // Oppdater URL hash
    window.location.hash = tabName;
}

// Tab-klikk
document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// === INITIAL LOAD ===

async function init() {
    // Sjekk database-status
    const status = await fetchData('/api/status');
    const badge = document.getElementById('status-badge');

    if (!status || status.totalt_ansatte === 0) {
        badge.textContent = 'Ingen data';
        badge.className = 'badge empty';
        document.getElementById('empty-state').classList.remove('hidden');
        return;
    }

    badge.textContent = `${status.aktive_ansatte} aktive ansatte`;
    badge.className = 'badge ok';
    document.getElementById('empty-state').classList.add('hidden');

    // Last initial tab basert på hash eller default
    const hash = window.location.hash.replace('#', '') || 'oversikt';
    switchTab(hash);
}

// === TAB DATA LOADING (lazy) ===

async function loadTabData(tabName) {
    tabLoaded[tabName] = true;

    switch (tabName) {
        case 'oversikt': return loadOversikt();
        case 'alder': return loadAlder();
        case 'geografi': return loadGeografi();
        case 'kjonn': return loadKjonn();
        case 'churn': return loadChurn();
        case 'tenure': return loadTenure();
        case 'lonn': return loadLonn();
        case 'jobbfamilier': return loadJobbfamilier();
        case 'sok': return; // Søk laster on-demand
        case 'import': return loadImportHistory();
    }
}

// === OVERSIKT ===

async function loadOversikt() {
    const [summary, byCountry, byCompany, empTypes, ftPt, mgmt] = await Promise.all([
        fetchData('/api/overview/summary'),
        fetchData('/api/overview/by-country'),
        fetchData('/api/overview/by-company'),
        fetchData('/api/employment/types'),
        fetchData('/api/employment/fulltime-parttime'),
        fetchData('/api/management/ratio'),
    ]);

    if (summary) {
        const cards = document.getElementById('overview-cards');
        cards.innerHTML = `
            ${card('Aktive ansatte', summary.aktive)}
            ${card('Totalt registrert', summary.totalt)}
            ${card('Sluttede', summary.sluttede, 'negative')}
            ${card('Snitt alder', summary.gjennomsnitt_alder)}
            ${mgmt ? card('Lederandel', mgmt.leder_andel_pct + '%') : ''}
            ${mgmt ? card('Ansatte/leder', mgmt.ansatte_per_leder) : ''}
        `;
    }

    if (byCountry) {
        renderBarChart('chart-by-country', Object.keys(byCountry), Object.values(byCountry));
    }
    if (byCompany) {
        renderHorizontalBarChart('chart-by-company', Object.keys(byCompany), Object.values(byCompany), { colors: COLORS.secondary });
    }
    if (empTypes) {
        renderPieChart('chart-employment-types', Object.keys(empTypes), Object.values(empTypes));
    }
    if (ftPt) {
        renderDoughnutChart('chart-fulltime-parttime', Object.keys(ftPt), Object.values(ftPt), {
            colors: [COLORS.primary, COLORS.accent, COLORS.unknown],
        });
    }
}

// === ALDER ===

async function loadAlder() {
    const [dist, pct, byCountry] = await Promise.all([
        fetchData('/api/age/distribution'),
        fetchData('/api/age/distribution-pct'),
        fetchData('/api/age/by-country'),
    ]);

    if (dist) {
        const labels = Object.keys(dist).filter(k => k !== 'Ukjent');
        const values = labels.map(k => dist[k]);
        renderBarChart('chart-age-dist', labels, values, { colors: COLORS.secondary });
    }
    if (pct) {
        const labels = Object.keys(pct).filter(k => k !== 'Ukjent');
        const values = labels.map(k => pct[k]);
        renderBarChart('chart-age-pct', labels, values, { colors: COLORS.accent });
    }
    if (byCountry) {
        // Stacked bar: land på x-aksen, alderskategorier som datasets
        const countries = Object.keys(byCountry);
        const cats = ['Under 25', '25-34', '35-44', '45-54', '55-64', '65+'];
        const datasets = cats.map((cat, i) => ({
            label: cat,
            data: countries.map(c => byCountry[c][cat] || 0),
            backgroundColor: PALETTE[i % PALETTE.length],
        }));
        renderStackedBarChart('chart-age-country', countries, datasets);
    }
}

// === GEOGRAFI ===

async function loadGeografi() {
    const [byCountry, byCompany, byDept] = await Promise.all([
        fetchData('/api/overview/by-country'),
        fetchData('/api/overview/by-company'),
        fetchData('/api/overview/by-department'),
    ]);

    if (byCountry) {
        renderBarChart('chart-geo-country', Object.keys(byCountry), Object.values(byCountry));
    }
    if (byCompany) {
        renderHorizontalBarChart('chart-geo-company', Object.keys(byCompany), Object.values(byCompany), { colors: COLORS.secondary });
    }
    if (byDept) {
        renderHorizontalBarChart('chart-geo-department', Object.keys(byDept), Object.values(byDept), { colors: COLORS.accent });
    }
}

// === KJØNN ===

async function loadKjonn() {
    const [dist, byCountry] = await Promise.all([
        fetchData('/api/gender/distribution'),
        fetchData('/api/gender/by-country'),
    ]);

    if (dist) {
        const labels = Object.keys(dist);
        const colors = labels.map(l => l === 'Mann' ? COLORS.male : l === 'Kvinne' ? COLORS.female : COLORS.unknown);
        renderPieChart('chart-gender-dist', labels, Object.values(dist), { colors });
    }
    if (byCountry) {
        const countries = Object.keys(byCountry);
        const datasets = [
            { label: 'Menn', data: countries.map(c => byCountry[c]['Mann'] || 0), backgroundColor: COLORS.male },
            { label: 'Kvinner', data: countries.map(c => byCountry[c]['Kvinne'] || 0), backgroundColor: COLORS.female },
        ];
        renderStackedBarChart('chart-gender-country', countries, datasets);
    }
}

// === CHURN ===

async function loadChurn() {
    // Sett datoer for periodevalg (default: 1. jan inneværende år til i dag)
    const currentYear = new Date().getFullYear();
    const today = new Date().toISOString().split('T')[0];
    const startInput = document.getElementById('churn-start');
    const endInput = document.getElementById('churn-end');
    startInput.value = `${currentYear}-01-01`;
    endInput.value = today;

    await loadChurnPeriod();
}

async function loadChurnPeriod() {
    const start = document.getElementById('churn-start').value;
    const end = document.getElementById('churn-end').value;
    if (!start || !end) return;

    // Beregn år fra startdato for månedlig churn
    const year = new Date(start).getFullYear();

    const [summary, monthly, byAge, byCountry, byGender, reasons] = await Promise.all([
        fetchData(`/api/churn/calculate?start_date=${start}&end_date=${end}`),
        fetchData(`/api/churn/monthly?year=${year}`),
        fetchData(`/api/churn/by-age?start_date=${start}&end_date=${end}`),
        fetchData(`/api/churn/by-country?start_date=${start}&end_date=${end}`),
        fetchData(`/api/churn/by-gender?start_date=${start}&end_date=${end}`),
        fetchData(`/api/churn/reasons?start_date=${start}&end_date=${end}`),
    ]);

    // Oppsummeringskort
    if (summary) {
        const container = document.getElementById('churn-summary-cards');
        container.innerHTML = `
            ${card('Periode', summary.periode)}
            ${card('Sluttet', summary.antall_sluttet, 'negative')}
            ${card('Nyansatte', summary.antall_nyansatte, 'positive')}
            ${card('Netto endring', summary.netto_endring, summary.netto_endring >= 0 ? 'positive' : 'negative')}
            ${card('Churn rate', summary.churn_rate_pct + '%')}
        `;
    }

    // Månedlig churn-graf
    if (monthly) {
        const labels = monthly.map(m => m['m\u00e5ned'] || m.maaned || m['måned']);
        renderLineChart('chart-churn-monthly', labels, [
            { label: 'Sluttet', data: monthly.map(m => m.sluttet), borderColor: COLORS.negative, tension: 0.3, pointRadius: 4 },
            { label: 'Nyansatte', data: monthly.map(m => m.nyansatte), borderColor: COLORS.positive, tension: 0.3, pointRadius: 4 },
            { label: 'Netto', data: monthly.map(m => m.netto), borderColor: COLORS.neutral, borderDash: [5, 5], tension: 0.3, pointRadius: 3 },
        ]);
    }

    // Churn per aldersgruppe
    if (byAge) {
        const labels = Object.keys(byAge);
        const values = labels.map(k => byAge[k].sluttet);
        renderBarChart('chart-churn-age', labels, values, { colors: COLORS.negative });
    }

    // Churn per land
    if (byCountry) {
        const labels = Object.keys(byCountry);
        const values = labels.map(k => byCountry[k].sluttet);
        renderBarChart('chart-churn-country', labels, values, { colors: COLORS.accent });
    }

    // Churn per kjønn
    if (byGender) {
        const labels = Object.keys(byGender);
        const values = labels.map(k => byGender[k].sluttet);
        const colors = labels.map(l => l === 'Mann' ? COLORS.male : l === 'Kvinne' ? COLORS.female : COLORS.unknown);
        renderPieChart('chart-churn-gender', labels, values, { colors });
    }

    // Oppsigelsesårsaker
    if (reasons && Object.keys(reasons).length > 0) {
        renderHorizontalBarChart('chart-churn-reasons', Object.keys(reasons), Object.values(reasons), { colors: COLORS.negative });
    }
}

// === TENURE ===

async function loadTenure() {
    const [avg, dist, ftPt] = await Promise.all([
        fetchData('/api/tenure/average'),
        fetchData('/api/tenure/distribution'),
        fetchData('/api/employment/fulltime-parttime'),
    ]);

    if (avg) {
        document.getElementById('tenure-cards').innerHTML = card('Snitt ansettelsestid', avg.gjennomsnitt_ar + ' år');
    }
    if (dist) {
        renderBarChart('chart-tenure-dist', Object.keys(dist), Object.values(dist), { colors: COLORS.positive });
    }
    if (ftPt) {
        renderDoughnutChart('chart-tenure-ft-pt', Object.keys(ftPt), Object.values(ftPt), {
            colors: [COLORS.primary, COLORS.accent, COLORS.unknown],
        });
    }
}

// === LØNN ===

async function loadLonn() {
    const [summary, byDept, byCountry, byGender, byAge, byJobFam] = await Promise.all([
        fetchData('/api/salary/summary'),
        fetchData('/api/salary/by-department'),
        fetchData('/api/salary/by-country'),
        fetchData('/api/salary/by-gender'),
        fetchData('/api/salary/by-age'),
        fetchData('/api/salary/by-job-family'),
    ]);

    if (summary && summary.antall_med_lonn > 0) {
        const cards = document.getElementById('salary-cards');
        cards.innerHTML = `
            ${card('Snitt lønn', formatNumber(summary.gjennomsnitt))}
            ${card('Lavest', formatNumber(summary.min))}
            ${card('Høyest', formatNumber(summary.maks))}
            ${card('Total lønnsmasse', formatNumber(summary.total_lonnsmasse))}
        `;
    }

    if (byDept) {
        const labels = Object.keys(byDept);
        const avgs = labels.map(k => byDept[k].gjennomsnitt);
        renderHorizontalBarChart('chart-salary-dept', labels, avgs, { colors: COLORS.primary });
    }
    if (byCountry) {
        const labels = Object.keys(byCountry);
        const avgs = labels.map(k => byCountry[k].gjennomsnitt);
        renderBarChart('chart-salary-country', labels, avgs, { colors: COLORS.accent });
    }
    if (byGender) {
        const labels = Object.keys(byGender).filter(k => !k.startsWith('lønn'));
        const avgs = labels.map(k => byGender[k].gjennomsnitt);
        const colors = labels.map(l => l === 'Mann' ? COLORS.male : l === 'Kvinne' ? COLORS.female : COLORS.unknown);
        renderBarChart('chart-salary-gender', labels, avgs, { colors });
    }
    if (byAge) {
        const labels = Object.keys(byAge);
        const avgs = labels.map(k => byAge[k].gjennomsnitt);
        renderBarChart('chart-salary-age', labels, avgs, { colors: COLORS.secondary });
    }
    if (byJobFam) {
        const labels = Object.keys(byJobFam);
        const avgs = labels.map(k => byJobFam[k].gjennomsnitt);
        renderHorizontalBarChart('chart-salary-jobfam', labels, avgs);
    }
}

// === JOBBFAMILIER ===

async function loadJobbfamilier() {
    const [dist, byCountry, byGender] = await Promise.all([
        fetchData('/api/job-family/distribution'),
        fetchData('/api/job-family/by-country'),
        fetchData('/api/job-family/by-gender'),
    ]);

    if (dist) {
        renderHorizontalBarChart('chart-jf-dist', Object.keys(dist), Object.values(dist));
    }
    if (byCountry) {
        const countries = Object.keys(byCountry);
        const allFamilies = new Set();
        countries.forEach(c => Object.keys(byCountry[c]).forEach(f => allFamilies.add(f)));
        const families = [...allFamilies];
        const datasets = families.map((fam, i) => ({
            label: fam,
            data: countries.map(c => byCountry[c][fam] || 0),
            backgroundColor: PALETTE[i % PALETTE.length],
        }));
        renderStackedBarChart('chart-jf-country', countries, datasets);
    }
    if (byGender) {
        const families = Object.keys(byGender);
        const datasets = [
            { label: 'Menn', data: families.map(f => byGender[f]['Mann'] || 0), backgroundColor: COLORS.male },
            { label: 'Kvinner', data: families.map(f => byGender[f]['Kvinne'] || 0), backgroundColor: COLORS.female },
        ];
        renderStackedBarChart('chart-jf-gender', families, datasets);
    }
}

// === SØK ===

async function doSearch() {
    const params = new URLSearchParams();
    const name = document.getElementById('search-name').value;
    const dept = document.getElementById('search-dept').value;
    const country = document.getElementById('search-country').value;
    const company = document.getElementById('search-company').value;
    const activeOnly = document.getElementById('search-active').checked;

    if (name) params.set('name', name);
    if (dept) params.set('department', dept);
    if (country) params.set('country', country);
    if (company) params.set('company', company);
    params.set('active_only', activeOnly);

    const data = await fetchData(`/api/search?${params.toString()}`);
    const container = document.getElementById('search-results');

    if (!data || data.length === 0) {
        container.innerHTML = '<p class="text-center" style="padding:24px;color:var(--text-light)">Ingen resultater.</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Navn</th>
                    <th>Tittel</th>
                    <th>Avdeling</th>
                    <th>Land</th>
                    <th>Selskap</th>
                    <th>Alder</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(r => `
                    <tr>
                        <td>${r.fornavn || ''} ${r.etternavn || ''}</td>
                        <td>${r.tittel || '–'}</td>
                        <td>${r.avdeling || '–'}</td>
                        <td>${r.arbeidsland || '–'}</td>
                        <td>${r.juridisk_selskap || '–'}</td>
                        <td>${r.alder || '–'}</td>
                        <td>${r.er_aktiv ? 'Aktiv' : 'Sluttet'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <p class="text-center mt-16" style="color:var(--text-light)">${data.length} resultater</p>
    `;
}

// Enter-tast for søk
document.querySelectorAll('#tab-sok input[type="text"]').forEach(input => {
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });
});

// === IMPORT ===

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) uploadFile(fileInput.files[0]);
});

async function uploadFile(file) {
    const statusEl = document.getElementById('import-status');
    statusEl.className = 'loading';
    statusEl.style.display = 'block';
    statusEl.textContent = `Importerer ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);
    const clearExisting = document.getElementById('import-clear').checked;

    try {
        const res = await fetch(`/api/import/upload?clear_existing=${clearExisting}`, {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();

        if (res.ok) {
            statusEl.className = 'success';
            statusEl.style.display = 'block';
            statusEl.textContent = data.melding;
            // Oppdater status og reload oversikt
            Object.keys(tabLoaded).forEach(k => delete tabLoaded[k]);
            await init();
            loadImportHistory();
        } else {
            statusEl.className = 'error';
            statusEl.style.display = 'block';
            statusEl.textContent = data.detail || 'Ukjent feil ved import.';
        }
    } catch (err) {
        statusEl.className = 'error';
        statusEl.style.display = 'block';
        statusEl.textContent = 'Nettverksfeil: ' + err.message;
    }
}

async function loadImportHistory() {
    const data = await fetchData('/api/import/history');
    const container = document.getElementById('import-history-list');

    if (!data || data.length === 0) {
        container.innerHTML = '<p style="color:var(--text-light)">Ingen importer registrert.</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <thead><tr><th>Fil</th><th>Dato</th><th>Rader</th><th>Status</th></tr></thead>
            <tbody>
                ${data.map(r => `
                    <tr>
                        <td>${r.filnavn || '–'}</td>
                        <td>${r.importert_dato || '–'}</td>
                        <td>${r.antall_rader || '–'}</td>
                        <td>${r.status || '–'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// === PDF DOWNLOAD ===

async function downloadPDF() {
    showLoader();
    try {
        const res = await fetch('/api/report/pdf');
        if (!res.ok) throw new Error('Kunne ikke generere PDF');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'hr_rapport.pdf';
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        alert('Feil ved PDF-generering: ' + err.message);
    } finally {
        hideLoader();
    }
}

// === HELPERS ===

function card(label, value, type = '') {
    const cls = type ? ` ${type}` : '';
    return `<div class="card"><div class="label">${label}</div><div class="value${cls}">${value}</div></div>`;
}

// === START ===
init();
