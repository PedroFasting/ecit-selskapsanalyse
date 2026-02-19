/**
 * charts.js — Chart.js wrapper-funksjoner for HR Analyse.
 * Konsistent stil, norske etiketter, ECIT-inspirert fargeskjema.
 */

// Fargeskjema (ECIT-inspirert: navy, blå, beige)
const COLORS = {
    primary: '#002C55',
    secondary: '#57A5E4',
    accent: '#BE3030',
    positive: '#3A7D3A',
    negative: '#BE3030',
    neutral: '#7A7A7A',
    male: '#002C55',
    female: '#57A5E4',
    unknown: '#B4A78D',
};

const PALETTE = [
    '#002C55', '#57A5E4', '#3E417F', '#BE3030', '#2377BA',
    '#B4A78D', '#03223F', '#7BA3C9', '#6B5B8A', '#4A7A5B',
];

// Hold styr på aktive charts (for destroy før re-render)
const chartInstances = {};

// SVG-ikoner for chart-knapper
const COPY_ICON = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5.5" y="5.5" width="9" height="9" rx="1.5"/><path d="M10.5 5.5V3a1.5 1.5 0 0 0-1.5-1.5H3A1.5 1.5 0 0 0 1.5 3v6A1.5 1.5 0 0 0 3 10.5h2.5"/></svg>`;
const DOWNLOAD_ICON = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v8.5M4.5 7.5 8 11l3.5-3.5"/><path d="M2.5 12.5v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1"/></svg>`;
const CHECK_ICON = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 8.5 6.5 12 13 4"/></svg>`;

/**
 * Hent tittelen til en chart fra h3 i chart-containeren.
 */
function getChartTitle(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return '';
    const container = canvas.closest('.chart-container');
    if (!container) return '';
    const h3 = container.querySelector('h3');
    return h3 ? h3.textContent.trim() : '';
}

/**
 * Bygg et eksport-canvas med hvit bakgrunn og tittel over grafen.
 */
function buildExportCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const title = getChartTitle(canvasId);
    const padding = 24;
    const titleHeight = title ? 40 : 0;

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width + padding * 2;
    tempCanvas.height = canvas.height + padding * 2 + titleHeight;
    const ctx = tempCanvas.getContext('2d');

    // Hvit bakgrunn
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    // Tegn tittel
    if (title) {
        ctx.fillStyle = '#03223F';
        ctx.font = '600 16px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
        ctx.textBaseline = 'middle';
        ctx.fillText(title, padding, padding + titleHeight / 2);
    }

    // Tegn grafen
    ctx.drawImage(canvas, padding, padding + titleHeight);

    return tempCanvas;
}

/**
 * Kopier en chart som PNG-bilde til utklippstavlen (med tittel).
 */
async function copyChart(canvasId) {
    const exportCanvas = buildExportCanvas(canvasId);
    if (!exportCanvas) return;

    try {
        const blob = await new Promise(resolve => exportCanvas.toBlob(resolve, 'image/png'));
        await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': blob })
        ]);
        showButtonFeedback(canvasId, 'copy', true);
    } catch (err) {
        console.error('Kunne ikke kopiere graf:', err);
        showButtonFeedback(canvasId, 'copy', false);
    }
}

/**
 * Last ned en chart som PNG-fil (med tittel).
 */
function downloadChart(canvasId) {
    const exportCanvas = buildExportCanvas(canvasId);
    if (!exportCanvas) return;

    const title = getChartTitle(canvasId) || canvasId;
    // Lag filnavn fra tittelen: lowercase, erstatt mellomrom/spesialtegn med bindestrek
    const filename = title
        .toLowerCase()
        .replace(/[æ]/g, 'ae').replace(/[ø]/g, 'o').replace(/[å]/g, 'aa')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        + '.png';

    const link = document.createElement('a');
    link.download = filename;
    link.href = exportCanvas.toDataURL('image/png');
    link.click();

    showButtonFeedback(canvasId, 'download', true);
}

/**
 * Vis kort visuell feedback etter kopiering/nedlasting.
 */
function showButtonFeedback(canvasId, action, success) {
    const selector = action === 'copy'
        ? `[data-copy-target="${canvasId}"]`
        : `[data-download-target="${canvasId}"]`;
    const btn = document.querySelector(selector);
    if (!btn) return;

    const originalIcon = action === 'copy' ? COPY_ICON : DOWNLOAD_ICON;
    const originalTitle = action === 'copy' ? 'Kopier graf' : 'Last ned graf';

    btn.innerHTML = success ? CHECK_ICON : '!';
    btn.classList.add(success ? 'copied' : 'copy-error');
    btn.title = success ? (action === 'copy' ? 'Kopiert!' : 'Lastet ned!') : 'Feil';

    setTimeout(() => {
        btn.innerHTML = originalIcon;
        btn.classList.remove('copied', 'copy-error');
        btn.title = originalTitle;
    }, 1500);
}

/**
 * Legg til kopier- og nedlast-knapper i chart-containeren.
 */
function ensureChartActions(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const container = canvas.closest('.chart-container');
    if (!container) return;

    // Sjekk om knappene allerede finnes
    if (container.querySelector(`[data-copy-target="${canvasId}"]`)) return;

    // Finn h3 og wrap i header-linje
    const h3 = container.querySelector('h3');
    if (!h3) return;

    // Opprett wrapper om den ikke finnes
    if (!h3.parentElement.classList.contains('chart-header')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'chart-header';
        h3.parentNode.insertBefore(wrapper, h3);
        wrapper.appendChild(h3);
    }

    const headerEl = h3.parentElement;

    // Knapp-gruppe
    const btnGroup = document.createElement('div');
    btnGroup.className = 'chart-actions';

    // Kopier-knapp
    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn-chart-action';
    copyBtn.setAttribute('data-copy-target', canvasId);
    copyBtn.title = 'Kopier graf';
    copyBtn.innerHTML = COPY_ICON;
    copyBtn.addEventListener('click', () => copyChart(canvasId));

    // Nedlast-knapp
    const dlBtn = document.createElement('button');
    dlBtn.className = 'btn-chart-action';
    dlBtn.setAttribute('data-download-target', canvasId);
    dlBtn.title = 'Last ned graf';
    dlBtn.innerHTML = DOWNLOAD_ICON;
    dlBtn.addEventListener('click', () => downloadChart(canvasId));

    btnGroup.appendChild(copyBtn);
    btnGroup.appendChild(dlBtn);
    headerEl.appendChild(btnGroup);
}

/**
 * Formater tall med mellomrom som tusenskilletegn (norsk format).
 */
function formatNumber(n) {
    if (n == null) return '–';
    return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

/**
 * Ødelegg eksisterende chart på et canvas før re-render.
 */
function destroyChart(canvasId) {
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }
}

/**
 * Felles Chart.js defaults.
 */
const defaultOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
        legend: { display: false },
        tooltip: {
            callbacks: {
                label: (ctx) => `${ctx.dataset.label || ''}: ${formatNumber(ctx.parsed.y ?? ctx.parsed)}`.trim(),
            },
        },
    },
};

// === CHART FUNKSJONER ===

function renderBarChart(canvasId, labels, data, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: options.colors || COLORS.primary,
                borderRadius: 4,
            }],
        },
        options: {
            ...defaultOptions,
            ...options.chartOptions,
            plugins: {
                ...defaultOptions.plugins,
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => formatNumber(ctx.parsed.y),
                    },
                },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}

function renderHorizontalBarChart(canvasId, labels, data, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: options.colors || COLORS.primary,
                borderRadius: 4,
            }],
        },
        options: {
            ...defaultOptions,
            indexAxis: 'y',
            plugins: {
                ...defaultOptions.plugins,
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => formatNumber(ctx.parsed.x),
                    },
                },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}

function renderPieChart(canvasId, labels, data, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: options.colors || PALETTE,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'right', labels: { font: { size: 13 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${formatNumber(ctx.parsed)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}

function renderLineChart(canvasId, labels, datasets, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            ...defaultOptions,
            plugins: {
                ...defaultOptions.plugins,
                legend: { display: true, position: 'top' },
            },
            scales: {
                y: { beginAtZero: true },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}

function renderStackedBarChart(canvasId, labels, datasets, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            ...defaultOptions,
            plugins: {
                ...defaultOptions.plugins,
                legend: { display: true, position: 'top' },
            },
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}

function renderDoughnutChart(canvasId, labels, data, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: options.colors || PALETTE,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'right', labels: { font: { size: 13 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${formatNumber(ctx.parsed)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}

function renderGroupedBarChart(canvasId, labels, datasets, options = {}) {
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            ...defaultOptions,
            plugins: {
                ...defaultOptions.plugins,
                legend: { display: true, position: 'top' },
            },
            scales: {
                x: { stacked: false },
                y: { stacked: false, beginAtZero: true },
            },
        },
    });
    ensureChartActions(canvasId);
    return chartInstances[canvasId];
}
