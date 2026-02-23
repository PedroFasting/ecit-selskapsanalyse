/**
 * app.js — Navigasjon, datahenting og UI-logikk for HR Analyse.
 */

// === STATE ===
const tabLoaded = {};  // Holder styr på hvilke tabs som har lastet data
let currentUser = null; // Innlogget bruker {id, navn, epost, rolle} eller null

// === API HELPERS ===

/** Sjekk om et API-svar har data (ikke null, ikke tomt objekt). */
function hasData(obj) {
    return obj && typeof obj === 'object' && Object.keys(obj).length > 0;
}

/** Vis «Ingen data»-melding i en chart-container. */
function showNoData(canvasId, melding = 'Ingen data tilgjengelig') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const container = canvas.closest('.chart-container');
    if (!container) return;
    // Fjern eksisterende no-data-melding
    const existing = container.querySelector('.no-data');
    if (existing) existing.remove();
    // Skjul canvas og vis melding
    canvas.style.display = 'none';
    const msg = document.createElement('p');
    msg.className = 'no-data';
    msg.textContent = melding;
    container.appendChild(msg);
}

async function fetchData(url) {
    showLoader();
    try {
        const res = await fetch(url);
        if (res.status === 401) {
            // Sesjon utløpt — nullstill bruker
            if (currentUser) {
                currentUser = null;
                updateUserUI();
                showToast('Sesjonen har utløpt — logg inn på nytt', true);
            }
            return null;
        }
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

// === AUTH ===

/** Vis en kort toast-melding nede i skjermbildet. */
function showToast(msg, isError = false) {
    let toast = document.getElementById('app-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.toggle('error', isError);
    toast.classList.add('visible');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('visible'), 2500);
}

/** Oppdater header-UI basert på innloggingsstatus. */
function updateUserUI() {
    const btnLogin = document.getElementById('btn-login');
    const userInfo = document.getElementById('user-info');
    const userName = document.getElementById('user-name');
    const userRole = document.getElementById('user-role');
    const pinBtn = document.getElementById('btn-pin-analyse');
    const adminTab = document.querySelector('.tab-admin');

    if (currentUser) {
        btnLogin.classList.add('hidden');
        userInfo.classList.remove('hidden');
        userName.textContent = currentUser.navn;
        userRole.textContent = currentUser.rolle;
        userRole.className = 'user-role-badge' + (currentUser.rolle === 'admin' ? ' admin' : '');
        if (pinBtn) pinBtn.style.display = '';
        // Vis admin-tab kun for admin
        if (adminTab) {
            if (currentUser.rolle === 'admin') {
                adminTab.classList.remove('hidden');
            } else {
                adminTab.classList.add('hidden');
            }
        }
    } else {
        btnLogin.classList.remove('hidden');
        userInfo.classList.add('hidden');
        if (pinBtn) pinBtn.style.display = 'none';
        if (adminTab) adminTab.classList.add('hidden');
    }
}

/** Sjekk om brukeren allerede er innlogget (cookie). */
async function checkAuth() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
            currentUser = await res.json();
        } else {
            currentUser = null;
        }
    } catch {
        currentUser = null;
    }
    updateUserUI();
}

/** Vis login-modalen og last brukerliste. */
async function showLoginModal() {
    const modal = document.getElementById('login-modal');
    const select = document.getElementById('login-user-select');
    modal.classList.remove('hidden');

    // Hent brukerliste
    try {
        const res = await fetch('/api/users');
        const users = await res.json();
        select.innerHTML = users.map(u =>
            `<option value="${u.id}">${u.navn} (${u.rolle})</option>`
        ).join('');
    } catch {
        select.innerHTML = '<option disabled>Kunne ikke laste brukere</option>';
    }
}

function hideLoginModal() {
    document.getElementById('login-modal').classList.add('hidden');
}

/** Utfør innlogging med valgt bruker. */
async function doLogin() {
    const select = document.getElementById('login-user-select');
    const userId = select.value;
    if (!userId) return;

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: parseInt(userId) }),
        });
        if (!res.ok) throw new Error('Innlogging feilet');
        currentUser = await res.json();
        updateUserUI();
        hideLoginModal();
        showToast(`Logget inn som ${currentUser.navn}`);

        // Migrer localStorage-pins om de finnes
        await migrateLocalPins();

        // Oppdater dashboard hvis vi er på oversikt
        if (tabLoaded['oversikt']) {
            tabLoaded['oversikt'] = false;
            loadOversikt();
        }
    } catch (err) {
        showToast('Innlogging feilet: ' + err.message, true);
    }
}

/** Logg ut. */
async function doLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch { /* ignorer */ }
    currentUser = null;
    updateUserUI();
    showToast('Logget ut');

    // Oppdater dashboard
    if (tabLoaded['oversikt']) {
        tabLoaded['oversikt'] = false;
        loadOversikt();
    }
}

/** Migrer localStorage-pins til serveren ved første innlogging. */
async function migrateLocalPins() {
    const PINNED_KEY = 'dashboard_pinned_charts';
    try {
        const raw = localStorage.getItem(PINNED_KEY);
        if (!raw) return;
        const pins = JSON.parse(raw);
        if (!Array.isArray(pins) || pins.length === 0) return;

        const res = await fetch('/api/dashboard/pins/migrate-local', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pins }),
        });
        if (res.ok) {
            const result = await res.json();
            localStorage.removeItem(PINNED_KEY);
            if (result.migrated > 0) {
                showToast(`${result.migrated} lokale grafer migrert til serveren`);
            }
        }
    } catch { /* ignorer migrasjonsfeil */ }
}

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
    // Sjekk om brukeren allerede er innlogget
    await checkAuth();

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
        case 'churn': return loadChurn();
        case 'tenure': return loadTenure();
        case 'lonn': return loadLonn();
        case 'analyse': return loadAnalyse();
        case 'sok': return; // Søk laster on-demand
        case 'import': return loadImportHistory();
        case 'admin': return loadAdmin();
    }
}

// === OVERSIKT ===

async function loadOversikt() {
    const [summary, empTypes, ftPt, mgmt] = await Promise.all([
        fetchData('/api/overview/summary'),
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

    if (empTypes) {
        renderPieChart('chart-employment-types', Object.keys(empTypes), Object.values(empTypes));
    }
    if (ftPt) {
        renderDoughnutChart('chart-fulltime-parttime', Object.keys(ftPt), Object.values(ftPt), {
            colors: [COLORS.primary, COLORS.accent, COLORS.unknown],
        });
    }

    // Populer profil-dropdown fra API (eller fallback til statisk)
    const presetSel = document.getElementById('dashboard-preset');
    await populateProfileDropdown(presetSel);

    // Rendre festede grafer for valgt profil
    await renderDashboardCharts(presetSel.value);

    // Lytter for profil-endring (kun én gang)
    if (!presetSel.dataset.listenerAttached) {
        presetSel.dataset.listenerAttached = 'true';
        presetSel.addEventListener('change', async () => {
            await renderDashboardCharts(presetSel.value);
        });
    }
}

/**
 * Populer profil-dropdown fra API. Viser profiler tilgjengelig for innlogget bruker.
 * Fallback: viser kun "Ikke innlogget" hvis brukeren ikke er logget inn.
 */
async function populateProfileDropdown(selectEl) {
    if (!currentUser) {
        selectEl.innerHTML = '<option value="" disabled>Logg inn for å se dashboard</option>';
        return;
    }

    try {
        const profiles = await fetchData('/api/dashboard/profiles');
        if (!profiles) throw new Error('no data');

        selectEl.innerHTML = profiles.map(p => {
            const val = p.id === null ? '' : p.id;
            return `<option value="${val}">${p.navn}</option>`;
        }).join('');
    } catch {
        selectEl.innerHTML = '<option value="">Mine grafer</option>';
    }
}

/**
 * Rendre grafer basert på valgt profil via API.
 * profileIdStr: '' for 'Mine grafer', eller en numeric profile ID.
 */
async function renderDashboardCharts(profileIdStr) {
    if (!currentUser) {
        const container = document.getElementById('pinned-charts-container');
        if (container) container.innerHTML = '<p style="text-align:center;color:var(--text-light);padding:24px;">Logg inn for å se festede grafer.</p>';
        return;
    }

    const url = profileIdStr
        ? `/api/dashboard/pins?profile_id=${profileIdStr}`
        : '/api/dashboard/pins';

    try {
        const pins = await fetchData(url);
        if (!pins) {
            await renderPinnedCharts([], false);
            return;
        }

        // Map API field names (tittel → title) for renderPinnedCharts compatibility
        const mapped = pins.map(p => ({
            id: p.id,
            metric: p.metric,
            group_by: p.group_by,
            split_by: p.split_by || null,
            filter_dim: p.filter_dim || null,
            filter_val: p.filter_val || null,
            chart_type: p.chart_type || null,
            title: p.tittel,
        }));

        // "Mine grafer" (profileIdStr='') → showUnpin=true; named profiles → only admin can unpin
        const canUnpin = !profileIdStr || (currentUser && currentUser.rolle === 'admin');
        await renderPinnedCharts(mapped, canUnpin);
    } catch (err) {
        console.error('Feil ved lasting av dashboard-pins:', err);
        await renderPinnedCharts([], false);
    }
}

/**
 * Rendre festede grafer i oversikt-dashboardet.
 * Henter data fra /api/analyze for hver pin og rendrer i #pinned-charts-container.
 */
async function renderPinnedCharts(pins, showUnpin = true) {
    const container = document.getElementById('pinned-charts-container');
    if (!container) return;

    // Ødelegg eksisterende pinned chart-instanser
    container.querySelectorAll('canvas').forEach(c => destroyChart(c.id));
    // Tøm eksisterende festede grafer og grid-wrapper
    container.innerHTML = '';

    if (!pins || pins.length === 0) return;

    // Opprett grid-wrapper
    const grid = document.createElement('div');
    grid.className = 'grid-2 pinned-charts-grid';

    for (const pin of pins) {
        // Bygg query-params
        const params = new URLSearchParams({ metric: pin.metric, group_by: pin.group_by });
        if (pin.split_by) params.set('split_by', pin.split_by);
        if (pin.filter_dim && pin.filter_val) params.set(`filter_${pin.filter_dim}`, pin.filter_val);

        const canvasId = 'pinned-' + pin.id;

        // Opprett chart-container
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-container pinned-chart';
        chartDiv.dataset.pinId = pin.id;
        const unpinBtn = showUnpin
            ? `<button class="btn-chart-action btn-unpin" title="Fjern fra oversikt" onclick="unpinChart('${pin.id}')">&#x2715;</button>`
            : '';
        chartDiv.innerHTML = `
            <div class="chart-header">
                <h3>${pin.title}</h3>
                <div class="chart-actions">
                    ${unpinBtn}
                </div>
            </div>
            <canvas id="${canvasId}"></canvas>
        `;
        grid.appendChild(chartDiv);
    }

    container.appendChild(grid);

    // Hent data og rendre grafer parallelt
    const renderPromises = pins.map(async (pin) => {
        const params = new URLSearchParams({ metric: pin.metric, group_by: pin.group_by });
        if (pin.split_by) params.set('split_by', pin.split_by);
        if (pin.filter_dim && pin.filter_val) params.set(`filter_${pin.filter_dim}`, pin.filter_val);

        const canvasId = 'pinned-' + pin.id;

        try {
            const result = await fetchData(`/api/analyze?${params.toString()}`);
            if (!result || !result.data) {
                showNoData(canvasId, 'Kunne ikke laste data');
                return;
            }

            // "Alle"-gruppering: vis KPI-kort i stedet for graf
            if (pin.group_by === 'alle') {
                const value = Object.values(result.data)[0];
                const chartDiv = document.querySelector(`[data-pin-id="${pin.id}"]`);
                const canvas = chartDiv.querySelector('canvas');
                if (canvas) canvas.style.display = 'none';
                const kpiDiv = document.createElement('div');
                kpiDiv.className = 'cards';
                kpiDiv.innerHTML = card(result.meta.metric_label, formatNumber(value));
                chartDiv.appendChild(kpiDiv);
                return;
            }

            const hasSplitBy = !!pin.split_by;
            const chartType = pin.chart_type || suggestChartType(result.data, hasSplitBy).default;
            renderChartByType(canvasId, chartType, result.data, hasSplitBy);
        } catch (err) {
            console.error(`Feil ved rendering av festet graf ${pin.id}:`, err);
            showNoData(canvasId, 'Feil ved lasting');
        }
    });

    await Promise.all(renderPromises);
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
    const [summary, byGender] = await Promise.all([
        fetchData('/api/salary/summary'),
        fetchData('/api/salary/by-gender'),
    ]);

    if (summary && summary.antall_med_lonn > 0) {
        const cards = document.getElementById('salary-cards');
        cards.innerHTML = `
            ${card('Snitt lønn', formatNumber(summary.gjennomsnitt))}
            ${card('Median lønn', formatNumber(summary.median))}
            ${card('Lavest', formatNumber(summary.min))}
            ${card('Høyest', formatNumber(summary.maks))}
            ${card('Total lønnsmasse', formatNumber(summary.total_lonnsmasse))}
        `;
    }

    if (byGender && Object.keys(byGender).filter(k => !k.startsWith('lønn')).length > 0) {
        const labels = Object.keys(byGender).filter(k => !k.startsWith('lønn'));
        const avgs = labels.map(k => byGender[k].gjennomsnitt);
        const colors = labels.map(l => l === 'Mann' ? COLORS.male : l === 'Kvinne' ? COLORS.female : COLORS.unknown);
        renderBarChart('chart-salary-gender', labels, avgs, { colors });
    } else {
        showNoData('chart-salary-gender');
    }
}

// === SØK ===

// === ANALYSE (Custom Analysis Builder) ===

let analyseOptions = null;  // Cache for /api/analyze/options data
let analyseChartType = null; // Currently selected chart type (null = auto)

async function loadAnalyse() {
    await loadAnalyseOptions();
    refreshTemplateDropdown();
}

async function loadAnalyseOptions() {
    analyseOptions = await fetchData('/api/analyze/options');
    if (!analyseOptions) return;

    // Populer metrikk-dropdown
    const metricSel = document.getElementById('analyse-metric');
    metricSel.innerHTML = analyseOptions.metrics.map(m =>
        `<option value="${m.id}">${m.label}</option>`
    ).join('');

    // Populer gruppering-dropdown
    const groupSel = document.getElementById('analyse-group-by');
    groupSel.innerHTML = analyseOptions.dimensions.map(d =>
        `<option value="${d.id}">${d.label}</option>`
    ).join('');

    // Populer inndeling-dropdown (med "Ingen" valg)
    const splitSel = document.getElementById('analyse-split-by');
    splitSel.innerHTML = '<option value="">Ingen</option>' +
        analyseOptions.dimensions.map(d =>
            `<option value="${d.id}">${d.label}</option>`
        ).join('');

    // Populer filter-dimensjon dropdown
    const filterDimSel = document.getElementById('analyse-filter-dim');
    filterDimSel.innerHTML = '<option value="">Ingen filter</option>' +
        analyseOptions.filter_dimensions.map(d =>
            `<option value="${d.id}">${d.label}</option>`
        ).join('');

    // Reset mal-dropdown når brukeren endrer valg manuelt
    function resetTemplateSelection() {
        const tplSel = document.getElementById('analyse-template-list');
        if (tplSel) tplSel.value = '';
    }
    metricSel.addEventListener('change', resetTemplateSelection);
    groupSel.addEventListener('change', resetTemplateSelection);
    splitSel.addEventListener('change', resetTemplateSelection);
    filterDimSel.addEventListener('change', resetTemplateSelection);

    // Filter-kaskade: velg dimensjon → populer verdi-dropdown
    filterDimSel.addEventListener('change', () => {
        const dim = filterDimSel.value;
        const filterValSel = document.getElementById('analyse-filter-val');
        if (!dim) {
            filterValSel.innerHTML = '<option value="">Velg filter først</option>';
            filterValSel.disabled = true;
            return;
        }
        const values = analyseOptions.filter_values[dim] || [];
        filterValSel.innerHTML = '<option value="">Alle</option>' +
            values.map(v => `<option value="${v}">${v}</option>`).join('');
        filterValSel.disabled = false;
    });

    // Reset mal-dropdown også ved endring av filterverdi
    const filterValSel2 = document.getElementById('analyse-filter-val');
    filterValSel2.addEventListener('change', resetTemplateSelection);

    // "Alle"-gruppering: skjul split_by og chart-type pills
    const groupSel2 = document.getElementById('analyse-group-by');
    groupSel2.addEventListener('change', () => {
        const isAlle = groupSel2.value === 'alle';
        const splitLabel = document.getElementById('analyse-split-by').closest('label');
        if (splitLabel) splitLabel.style.display = isAlle ? 'none' : '';
        if (isAlle) {
            document.getElementById('analyse-split-by').value = '';
            document.getElementById('analyse-chart-types').classList.add('hidden');
        }
    });
}

async function runAnalysis() {
    const metric = document.getElementById('analyse-metric').value;
    const groupBy = document.getElementById('analyse-group-by').value;
    const splitBy = document.getElementById('analyse-split-by').value;
    const filterDim = document.getElementById('analyse-filter-dim').value;
    const filterVal = document.getElementById('analyse-filter-val').value;

    if (!metric || !groupBy) return;

    // Bygg query-params
    const params = new URLSearchParams({ metric, group_by: groupBy });
    if (splitBy && groupBy !== 'alle') params.set('split_by', splitBy);
    if (filterDim && filterVal) params.set(`filter_${filterDim}`, filterVal);

    const result = await fetchData(`/api/analyze?${params.toString()}`);
    if (!result || !result.data) return;

    const hasSplitBy = !!splitBy && groupBy !== 'alle';
    const data = result.data;

    // Bygg tittel
    let title = result.meta.metric_label;
    if (groupBy !== 'alle') {
        title += ' per ' + result.meta.group_by_label;
        if (hasSplitBy) title += ' og ' + result.meta.split_by_label;
    }
    if (filterDim && filterVal) {
        const dimLabel = analyseOptions.filter_dimensions.find(d => d.id === filterDim)?.label || filterDim;
        title += ` (${dimLabel}: ${filterVal})`;
    }

    // Vis resultat-container
    document.getElementById('analyse-result').classList.remove('hidden');

    // "Alle" = vis KPI-kort i stedet for graf
    if (groupBy === 'alle') {
        document.getElementById('analyse-chart-types').classList.add('hidden');
        const value = Object.values(data)[0];
        const resultEl = document.getElementById('analyse-result');
        resultEl.innerHTML = `
            <div class="cards">
                ${card(result.meta.metric_label, formatNumber(value))}
            </div>
        `;
        // Skjul pin-knapp (ikke meningsfylt å feste et enkelt-tall)
        return;
    }

    // Bestem graftype
    const suggestion = suggestChartType(data, hasSplitBy);
    updateChartTypePills(suggestion, hasSplitBy);

    // Gjenopprett canvas + chart-header om det ble fjernet av KPI-kort-rendering
    const resultEl = document.getElementById('analyse-result');
    if (!resultEl.querySelector('canvas')) {
        resultEl.innerHTML = `
            <div class="chart-header">
                <h3 id="analyse-chart-title">${title}</h3>
                <div class="chart-actions">
                    <button class="btn-chart-action" id="btn-pin-analyse" title="Fest til oversikt" onclick="showPinModal()">&#x1F4CC;</button>
                </div>
            </div>
            <canvas id="chart-analyse"></canvas>
        `;
    } else {
        // Oppdater tittel i eksisterende header
        const titleEl = document.getElementById('analyse-chart-title');
        if (titleEl) titleEl.textContent = title;
    }

    const chartType = analyseChartType || suggestion.default;
    renderAnalyseChart(chartType, data, hasSplitBy, result.meta);
}

function suggestChartType(data, hasSplitBy) {
    const groupCount = Object.keys(data).length;
    if (hasSplitBy) return { default: 'stacked', available: ['stacked', 'grouped', 'horizontalBar'] };
    if (groupCount <= 6) return { default: 'pie', available: ['pie', 'bar', 'horizontalBar', 'doughnut'] };
    if (groupCount > 15) return { default: 'horizontalBar', available: ['horizontalBar', 'bar'] };
    return { default: 'bar', available: ['bar', 'horizontalBar', 'pie', 'doughnut'] };
}

const CHART_TYPE_LABELS = {
    bar: 'Stolpe',
    horizontalBar: 'Horisontal',
    stacked: 'Stablet',
    grouped: 'Gruppert',
    pie: 'Kake',
    doughnut: 'Ring',
};

function updateChartTypePills(suggestion, hasSplitBy) {
    const container = document.getElementById('analyse-chart-types');
    const pillsEl = document.getElementById('analyse-pills');
    container.classList.remove('hidden');

    const activeType = analyseChartType || suggestion.default;

    pillsEl.innerHTML = suggestion.available.map(type => {
        const active = type === activeType ? ' active' : '';
        const label = CHART_TYPE_LABELS[type] || type;
        return `<button class="chart-type-pill${active}" data-chart-type="${type}">${label}</button>`;
    }).join('');

    // Click handlers
    pillsEl.querySelectorAll('.chart-type-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            analyseChartType = btn.dataset.chartType;
            // Oppdater aktiv pill
            pillsEl.querySelectorAll('.chart-type-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Re-render
            runAnalysis();
        });
    });
}

function renderAnalyseChart(chartType, data, hasSplitBy, meta) {
    renderChartByType('chart-analyse', chartType, data, hasSplitBy);
}

// === PIN MODAL & API-BASED PINS ===

/**
 * Vis pin-modal. Leser nåværende analyse-verdier og lar bruker velge profil.
 * Admin: ser dropdown med alle profiler.
 * Bruker: ser "Mine grafer" (ingen dropdown), med hint om at admin styrer profiler.
 */
async function showPinModal() {
    if (!currentUser) {
        showToast('Logg inn for å feste grafer', true);
        return;
    }

    const metric = document.getElementById('analyse-metric').value;
    const groupBy = document.getElementById('analyse-group-by').value;
    if (!metric || !groupBy) return;

    const title = document.getElementById('analyse-chart-title')?.textContent || 'Ukjent';

    // Vis tittelen i modalen
    document.getElementById('pin-modal-title').textContent = title;

    // Dropdown og hint-elementer
    const profileSel = document.getElementById('pin-profile-select');
    const profileLabel = document.getElementById('pin-profile-label');
    const hintEl = document.getElementById('pin-modal-hint');

    if (currentUser.rolle === 'admin') {
        // Admin: vis dropdown med alle profiler
        profileLabel.classList.remove('hidden');
        try {
            const profiles = await fetchData('/api/dashboard/profiles');
            if (!profiles) throw new Error('no data');

            profileSel.innerHTML = profiles.map(p => {
                const val = p.id === null ? '' : p.id;
                return `<option value="${val}">${p.navn}</option>`;
            }).join('');
        } catch {
            profileSel.innerHTML = '<option value="">Mine grafer</option>';
        }

        // Pre-velg profilen som er aktiv på Oversikt-fanen
        const presetSel = document.getElementById('dashboard-preset');
        if (presetSel && presetSel.value !== undefined) {
            const lastProfile = presetSel.value;
            const optionExists = Array.from(profileSel.options).some(o => o.value === lastProfile);
            if (optionExists) {
                profileSel.value = lastProfile;
            }
        }

        hintEl.textContent = 'Velg hvilken dashboard-profil grafen skal vises under på Oversikt-fanen.';
    } else {
        // Vanlig bruker: skjul dropdown, vis tydelig melding
        profileLabel.classList.add('hidden');
        profileSel.innerHTML = '<option value="">Mine grafer</option>';
        hintEl.textContent = 'Grafen legges under «Mine grafer» på Oversikt-fanen. Kontakt admin for å legge til grafer i felles profiler (HR-oversikt, Ledelse osv.).';
    }

    document.getElementById('pin-modal').classList.remove('hidden');
}

function hidePinModal() {
    document.getElementById('pin-modal').classList.add('hidden');
}

/**
 * Bekreft pin — send til API, vis profilnavn i toast, naviger til Oversikt.
 */
async function confirmPin() {
    const metric = document.getElementById('analyse-metric').value;
    const groupBy = document.getElementById('analyse-group-by').value;
    const splitBy = document.getElementById('analyse-split-by').value;
    const filterDim = document.getElementById('analyse-filter-dim').value;
    const filterVal = document.getElementById('analyse-filter-val').value;
    const title = document.getElementById('analyse-chart-title')?.textContent || 'Ukjent';
    const profileSelect = document.getElementById('pin-profile-select');
    const profileIdStr = profileSelect.value;
    const profileName = profileSelect.options[profileSelect.selectedIndex]?.text || 'Mine grafer';

    if (!metric || !groupBy) return;

    const body = {
        metric,
        group_by: groupBy,
        split_by: splitBy || null,
        filter_dim: filterDim || null,
        filter_val: filterVal || null,
        chart_type: analyseChartType || null,
        tittel: title,
    };
    if (profileIdStr) {
        body.profile_id = parseInt(profileIdStr);
    }

    try {
        const res = await fetch('/api/dashboard/pins', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (res.status === 409) {
            showToast('Denne grafen finnes allerede i «' + profileName + '»', true);
            hidePinModal();
            return;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Ukjent feil');
        }

        hidePinModal();
        showToast('Graf festet til «' + profileName + '»! Går til Oversikt\u2026');

        // Naviger til Oversikt-fanen og vis den aktuelle profilen
        await _navigateToProfile(profileIdStr);
    } catch (err) {
        showToast('Feil ved festing: ' + err.message, true);
    }
}

/**
 * Naviger til Oversikt-fanen og velg angitt profil i dropdown.
 * Brukes etter pin for å gi umiddelbar visuell bekreftelse.
 */
async function _navigateToProfile(profileIdStr) {
    // Bytt til Oversikt-fanen
    const oversiktTab = document.querySelector('[data-tab="oversikt"]');
    if (oversiktTab) oversiktTab.click();

    // Vent litt så tab-innhold rendres, deretter velg riktig profil
    await new Promise(r => setTimeout(r, 150));

    const presetSel = document.getElementById('dashboard-preset');
    if (presetSel) {
        presetSel.value = profileIdStr;
        await renderDashboardCharts(profileIdStr);
    }
}

/**
 * Fjern en festet graf via API.
 */
async function unpinChart(pinId) {
    if (!currentUser) return;

    try {
        const res = await fetch(`/api/dashboard/pins/${pinId}`, { method: 'DELETE' });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Feil ved fjerning');
        }

        // Destroy chart og fjern DOM-element
        destroyChart('pinned-' + pinId);
        const el = document.querySelector(`[data-pin-id="${pinId}"]`);
        if (el) el.remove();

        // Fjern tom grid-wrapper om ingen festede gjenstår
        const container = document.getElementById('pinned-charts-container');
        if (container) {
            const grid = container.querySelector('.pinned-charts-grid');
            if (grid && grid.querySelectorAll('.pinned-chart').length === 0) {
                grid.remove();
            }
        }

        showToast('Graf fjernet');
    } catch (err) {
        showToast(err.message, true);
    }
}

/**
 * Gjenbrukbar chart-rendering. Brukes av både analyse-tab og festede grafer.
 * Rendrer data til en gitt canvasId med gitt chartType.
 */
function renderChartByType(canvasId, chartType, data, hasSplitBy) {
    if (hasSplitBy) {
        const labels = Object.keys(data);
        const allSplits = new Set();
        labels.forEach(g => Object.keys(data[g]).forEach(s => allSplits.add(s)));
        const splits = [...allSplits];

        const datasets = splits.map((s, i) => ({
            label: s,
            data: labels.map(g => data[g][s] || 0),
            backgroundColor: PALETTE[i % PALETTE.length],
        }));

        if (chartType === 'stacked') {
            renderStackedBarChart(canvasId, labels, datasets);
        } else if (chartType === 'grouped') {
            renderGroupedBarChart(canvasId, labels, datasets);
        } else {
            const totals = labels.map(g => Object.values(data[g]).reduce((a, b) => a + b, 0));
            renderHorizontalBarChart(canvasId, labels, totals);
        }
    } else {
        const labels = Object.keys(data);
        const values = Object.values(data);

        switch (chartType) {
            case 'bar':
                renderBarChart(canvasId, labels, values);
                break;
            case 'horizontalBar':
                renderHorizontalBarChart(canvasId, labels, values);
                break;
            case 'pie':
                renderPieChart(canvasId, labels, values);
                break;
            case 'doughnut':
                renderDoughnutChart(canvasId, labels, values);
                break;
            default:
                renderBarChart(canvasId, labels, values);
        }
    }
}

// === ANALYSE TEMPLATES (localStorage) ===

const TEMPLATE_KEY = 'analysis_templates';

function getTemplates() {
    try {
        return JSON.parse(localStorage.getItem(TEMPLATE_KEY) || '[]');
    } catch { return []; }
}

function saveTemplates(templates) {
    localStorage.setItem(TEMPLATE_KEY, JSON.stringify(templates));
}

function saveTemplate() {
    const metric = document.getElementById('analyse-metric').value;
    const groupBy = document.getElementById('analyse-group-by').value;
    const splitBy = document.getElementById('analyse-split-by').value;
    const filterDim = document.getElementById('analyse-filter-dim').value;
    const filterVal = document.getElementById('analyse-filter-val').value;

    if (!metric || !groupBy) {
        alert('Velg metrikk og gruppering først.');
        return;
    }

    const name = prompt('Navn på malen:');
    if (!name || !name.trim()) return;

    const templates = getTemplates();

    // Sjekk duplikat-navn
    if (templates.some(t => t.name === name.trim())) {
        if (!confirm(`Malen "${name.trim()}" finnes allerede. Overskriv?`)) return;
        const idx = templates.findIndex(t => t.name === name.trim());
        templates.splice(idx, 1);
    }

    templates.push({
        name: name.trim(),
        metric,
        group_by: groupBy,
        split_by: splitBy || null,
        filter_dim: filterDim || null,
        filter_val: filterVal || null,
        chart_type: analyseChartType,
        created: new Date().toISOString(),
    });

    saveTemplates(templates);
    refreshTemplateDropdown();
}

function loadTemplate() {
    const sel = document.getElementById('analyse-template-list');
    const name = sel.value;
    if (!name) return;

    const templates = getTemplates();
    const tmpl = templates.find(t => t.name === name);
    if (!tmpl) return;

    // Sett dropdown-verdier
    document.getElementById('analyse-metric').value = tmpl.metric;
    document.getElementById('analyse-group-by').value = tmpl.group_by;
    document.getElementById('analyse-split-by').value = tmpl.split_by || '';

    // Sett filter
    const filterDimSel = document.getElementById('analyse-filter-dim');
    filterDimSel.value = tmpl.filter_dim || '';
    filterDimSel.dispatchEvent(new Event('change')); // Trigger kaskade

    if (tmpl.filter_dim && tmpl.filter_val) {
        // Vent litt på at kaskade-oppdatering kjører
        setTimeout(() => {
            document.getElementById('analyse-filter-val').value = tmpl.filter_val;
        }, 50);
    }

    // Åpne "Flere valg" om malen har inndeling eller filter
    if (tmpl.split_by || tmpl.filter_dim) {
        document.getElementById('analyse-extra-options').open = true;
    }

    // Sett graftype
    analyseChartType = tmpl.chart_type;

    // Kjør analyse
    setTimeout(() => runAnalysis(), 100);
}

function deleteTemplate() {
    const sel = document.getElementById('analyse-template-list');
    const name = sel.value;
    if (!name) return;

    if (!confirm(`Slett malen "${name}"?`)) return;

    const templates = getTemplates().filter(t => t.name !== name);
    saveTemplates(templates);
    refreshTemplateDropdown();
}

function refreshTemplateDropdown() {
    const sel = document.getElementById('analyse-template-list');
    const templates = getTemplates();

    if (templates.length === 0) {
        sel.innerHTML = '<option value="">Ingen lagrede maler</option>';
    } else {
        sel.innerHTML = '<option value="">Velg mal...</option>' +
            templates.map(t => `<option value="${t.name}">${t.name}</option>`).join('');
    }
}

// === SØK (continued) ===

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

    // Fjern tidligere advarsler
    const oldWarnings = document.getElementById('import-warnings');
    if (oldWarnings) oldWarnings.remove();

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

            // Vis melding med match-info
            let statusText = data.melding;
            if (data.validering) {
                const v = data.validering;
                statusText += ` (${v.matchede_kolonner}/${v.totalt_forventede} kolonner gjenkjent)`;
            }
            statusEl.textContent = statusText;

            // Vis advarsler hvis de finnes
            if (data.advarsler && data.advarsler.length > 0) {
                statusEl.className = 'warning';
                const warningsEl = document.createElement('div');
                warningsEl.id = 'import-warnings';
                warningsEl.className = 'import-warnings visible';
                const list = data.advarsler.map(w => `<li>${w}</li>`).join('');
                warningsEl.innerHTML = `<strong>Advarsler:</strong><ul>${list}</ul>`;
                if (data.validering && data.validering.manglende.length > 0) {
                    const missing = data.validering.manglende.join(', ');
                    warningsEl.innerHTML += `<div class="import-match-info">Manglende kolonner: ${missing}</div>`;
                }
                statusEl.parentNode.insertBefore(warningsEl, statusEl.nextSibling);
            }

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

// === ADMIN PANEL ===

async function loadAdmin() {
    if (!currentUser || currentUser.rolle !== 'admin') return;
    await Promise.all([loadAdminUsers(), loadAdminProfiles()]);
}

async function loadAdminUsers() {
    const container = document.getElementById('admin-users-list');
    const users = await fetchData('/api/users');
    if (!users || users.length === 0) {
        container.innerHTML = '<p style="color:var(--text-light)">Ingen brukere.</p>';
        return;
    }
    container.innerHTML = `
        <table>
            <thead>
                <tr><th>ID</th><th>Navn</th><th>E-post</th><th>Rolle</th></tr>
            </thead>
            <tbody>
                ${users.map(u => `
                    <tr>
                        <td>${u.id}</td>
                        <td>${u.navn}</td>
                        <td>${u.epost}</td>
                        <td>${u.rolle}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function adminCreateUser() {
    const navn = document.getElementById('admin-user-name').value.trim();
    const epost = document.getElementById('admin-user-email').value.trim();
    const rolle = document.getElementById('admin-user-role').value;

    if (!navn || !epost) {
        showToast('Fyll inn navn og e-post', true);
        return;
    }

    try {
        const res = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ navn, epost, rolle }),
        });
        if (res.status === 409) {
            showToast('E-posten finnes allerede', true);
            return;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Feil ved opprettelse');
        }

        showToast(`Bruker ${navn} opprettet`);
        document.getElementById('admin-user-name').value = '';
        document.getElementById('admin-user-email').value = '';
        await loadAdminUsers();
    } catch (err) {
        showToast(err.message, true);
    }
}

async function loadAdminProfiles() {
    const container = document.getElementById('admin-profiles-list');
    const profiles = await fetchData('/api/dashboard/profiles');
    if (!profiles || profiles.length === 0) {
        container.innerHTML = '<p style="color:var(--text-light)">Ingen profiler.</p>';
        return;
    }

    // Filtrer bort pseudo-profilen "Mine grafer" (id=null)
    const real = profiles.filter(p => p.id !== null);
    if (real.length === 0) {
        container.innerHTML = '<p style="color:var(--text-light)">Ingen profiler opprettet enn&aring;.</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <thead>
                <tr><th>ID</th><th>Navn</th><th>Beskrivelse</th><th></th></tr>
            </thead>
            <tbody>
                ${real.map(p => `
                    <tr>
                        <td>${p.id}</td>
                        <td>${p.navn}</td>
                        <td>${p.beskrivelse || '–'}</td>
                        <td><button class="btn-admin-delete" onclick="adminDeleteProfile(${p.id}, '${p.navn.replace(/'/g, "\\'")}')">Slett</button></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function adminCreateProfile() {
    const navn = document.getElementById('admin-profile-name').value.trim();
    const beskrivelse = document.getElementById('admin-profile-desc').value.trim();

    if (!navn) {
        showToast('Fyll inn profilnavn', true);
        return;
    }

    try {
        const res = await fetch('/api/dashboard/profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ navn, beskrivelse }),
        });
        if (res.status === 409) {
            showToast('Profil med dette navnet finnes allerede', true);
            return;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Feil ved opprettelse');
        }

        showToast(`Profil "${navn}" opprettet`);
        document.getElementById('admin-profile-name').value = '';
        document.getElementById('admin-profile-desc').value = '';
        await loadAdminProfiles();
    } catch (err) {
        showToast(err.message, true);
    }
}

async function adminDeleteProfile(profileId, profileName) {
    if (!confirm(`Slett profilen "${profileName}" og alle tilhørende pins?`)) return;

    try {
        const res = await fetch(`/api/dashboard/profiles/${profileId}`, { method: 'DELETE' });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Feil ved sletting');
        }
        showToast(`Profil "${profileName}" slettet`);
        await loadAdminProfiles();
    } catch (err) {
        showToast(err.message, true);
    }
}

// === START ===
init();
