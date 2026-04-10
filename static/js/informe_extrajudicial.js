/**
 * informe_extrajudicial.js
 * ========================
 * Maneja el formulario de subida, llama al endpoint y renderiza
 * las tablas y gráficas del informe extrajudicial mensual.
 */

import { showStatus, setupFileInput, setButtonLoading } from './utils.js';

// ── Colores ────────────────────────────────────────────────────
const PIE_COLORS = [
    '#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed',
    '#0891b2', '#be185d', '#65a30d', '#ea580c', '#6366f1',
];
const CORREOS_COLORS = ['#16a34a', '#dc2626', '#2563eb', '#9ca3af'];

// ── Referencias DOM ───────────────────────────────────────────
const form           = document.getElementById('form-informe');
const submitBtn      = document.getElementById('submit-btn');
const statusEl       = document.getElementById('status');
const faseUpload     = document.getElementById('fase-upload');
const reporte        = document.getElementById('reporte');
const btnVolver      = document.getElementById('btn-volver');
const btnImprimir    = document.getElementById('btn-imprimir');

const gestionesInput = document.getElementById('gestiones-input');
const gestionesArea  = document.getElementById('gestiones-area');
const gestionesName  = document.getElementById('gestiones-name');

const liquidInput    = document.getElementById('liquidaciones-input');
const liquidArea     = document.getElementById('liquidaciones-area');
const liquidName     = document.getElementById('liquidaciones-name');

const correosInput   = document.getElementById('correos-input');
const correosArea    = document.getElementById('correos-area');
const correosName    = document.getElementById('correos-name');
const rangoFechas    = document.getElementById('rango-fechas');
const fechaInicio    = document.getElementById('fecha-inicio');
const fechaFin       = document.getElementById('fecha-fin');

// Instancias de Chart.js
let chartPie    = null;
let chartCombo  = null;
let chartCorreos = null;

// ── Setup file inputs ─────────────────────────────────────────
setupFileInput(gestionesInput, gestionesArea, gestionesName, actualizarBoton);
setupFileInput(liquidInput,    liquidArea,    liquidName,    actualizarBoton);
setupFileInput(correosInput,   correosArea,   correosName,   () => {
    rangoFechas.style.display = correosInput.files.length > 0 ? '' : 'none';
});

function actualizarBoton() {
    submitBtn.disabled = !(gestionesInput.files.length > 0 && liquidInput.files.length > 0);
}

// ── Submit ────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('gestiones',     gestionesInput.files[0]);
    formData.append('liquidaciones', liquidInput.files[0]);

    if (correosInput.files.length > 0) {
        formData.append('correos', correosInput.files[0]);
        if (fechaInicio.value) formData.append('fecha_inicio', fechaInicio.value);
        if (fechaFin.value)    formData.append('fecha_fin',    fechaFin.value);
    }

    setButtonLoading(submitBtn, true);
    showStatus(statusEl, 'Procesando archivos…', 'info');

    try {
        const res = await fetch('/analizar-informe-extrajudicial', {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
            throw new Error(err.detail || 'Error en el servidor');
        }

        const data = await res.json();
        statusEl.className = 'status';

        renderizarInforme(data);

        faseUpload.style.display = 'none';
        reporte.classList.add('visible');

    } catch (err) {
        showStatus(statusEl, `❌ ${err.message}`, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
});

// ── Volver ────────────────────────────────────────────────────
btnVolver.addEventListener('click', () => {
    reporte.classList.remove('visible');
    faseUpload.style.display = '';
    statusEl.className = 'status';
    rangoFechas.style.display = 'none';
});

// ── Imprimir ──────────────────────────────────────────────────
btnImprimir.addEventListener('click', () => window.print());

// ── Renderizado principal ─────────────────────────────────────
function renderizarInforme(data) {
    const periodo = data.periodo || '';
    const periodoRango = data.periodo_rango || periodo;

    // Encabezado de impresión
    document.getElementById('print-periodo-texto').textContent = `Período: ${periodoRango}`;

    if (data.gestiones.resumen) {
        renderizarResumen(data.gestiones.resumen, periodo);
        document.getElementById('bloque-resumen').style.display = '';
    } else {
        document.getElementById('bloque-resumen').style.display = 'none';
    }
    renderizarGestiones(data.gestiones, periodo);
    renderizarLiquidaciones(data.liquidaciones, periodo);

    const bloqueCorreos = document.getElementById('bloque-correos');
    if (data.correos) {
        renderizarCorreos(data.correos, periodo);
        bloqueCorreos.style.display = '';
    } else {
        bloqueCorreos.style.display = 'none';
    }
}

// ── Bloque 0: Resumen por agente y módulo ────────────────────
function renderizarResumen(r, _periodo) {
    document.getElementById('titulo-resumen').textContent = r.titulo;

    // Tabla agente
    const bodyAgente = document.getElementById('body-agente');
    bodyAgente.innerHTML = '';
    r.tabla_agente.forEach(row => {
        bodyAgente.insertAdjacentHTML('beforeend', `
            <tr>
                <td>${row.agente}</td>
                <td style="text-align:right">${row.gestiones}</td>
                <td style="text-align:right">${row.porcentaje.toFixed(2)}%</td>
            </tr>`);
    });
    bodyAgente.insertAdjacentHTML('beforeend', `
        <tr class="fila-total">
            <td>Total general</td>
            <td style="text-align:right">${r.total}</td>
            <td style="text-align:right">100,00%</td>
        </tr>`);

    // Pivot módulo × sub-respuesta
    const bodyPivot = document.getElementById('body-pivot');
    bodyPivot.innerHTML = '';
    r.grupos.forEach(grupo => {
        // Fila de módulo
        bodyPivot.insertAdjacentHTML('beforeend', `
            <tr class="fila-modulo">
                <td colspan="2">${grupo.modulo}</td>
            </tr>`);
        // Sub-filas
        grupo.filas.forEach(fila => {
            bodyPivot.insertAdjacentHTML('beforeend', `
                <tr class="fila-sub">
                    <td>${fila.sub}</td>
                    <td style="text-align:right">${fila.count}</td>
                </tr>`);
        });
        // Subtotal del módulo
        bodyPivot.insertAdjacentHTML('beforeend', `
            <tr class="fila-subtotal">
                <td>Subtotal ${grupo.modulo}</td>
                <td style="text-align:right">${grupo.subtotal}</td>
            </tr>`);
    });
    bodyPivot.insertAdjacentHTML('beforeend', `
        <tr class="fila-total">
            <td>Total general</td>
            <td style="text-align:right">${r.total}</td>
        </tr>`);
}

// ── Bloque 1: Gestiones ───────────────────────────────────────
function renderizarGestiones(g, _periodo) {
    document.getElementById('titulo-gestiones').textContent = g.titulo;

    const tbody = document.getElementById('body-gestiones');
    tbody.innerHTML = '';
    g.tabla.forEach(row => {
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td>${row.etiqueta}</td>
                <td class="num">${row.cantidad}</td>
                <td class="num">${row.porcentaje.toFixed(2)}%</td>
            </tr>`);
    });
    tbody.insertAdjacentHTML('beforeend', `
        <tr class="fila-total">
            <td>Total general</td>
            <td class="num">${g.total}</td>
            <td class="num">100,00%</td>
        </tr>`);

    if (chartPie) chartPie.destroy();
    chartPie = new Chart(document.getElementById('chart-pie').getContext('2d'), {
        type: 'pie',
        data: {
            labels: g.labels,
            datasets: [{
                data: g.values,
                backgroundColor: PIE_COLORS.slice(0, g.labels.length),
                borderWidth: 1,
                borderColor: '#fff',
            }],
        },
        options: {
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const pct = ((ctx.parsed / g.total) * 100).toFixed(2);
                            return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });

    const lista = document.getElementById('leyenda-pie-lista');
    lista.innerHTML = '';
    g.labels.forEach((label, i) => {
        lista.insertAdjacentHTML('beforeend', `
            <li>
                <span class="dot" style="background:${PIE_COLORS[i % PIE_COLORS.length]}"></span>
                ${label}
            </li>`);
    });
}

// ── Bloque 2: Pagos ───────────────────────────────────────────
function renderizarLiquidaciones(l, periodo) {
    document.getElementById('titulo-liquidaciones').textContent =
        `GESTIÓN EXTRAJUDICIAL ${periodo} — ${l.titulo}`;

    const tbody = document.getElementById('body-liquidaciones');
    tbody.innerHTML = '';

    if (l.sin_datos || !l.tabla.length) {
        tbody.insertAdjacentHTML('beforeend', `
            <tr><td colspan="3" style="text-align:center;color:#888;padding:1.5rem">
                Sin registros de liquidaciones para el período ${periodo}
            </td></tr>`);
        if (chartCombo) { chartCombo.destroy(); chartCombo = null; }
        return;
    }

    l.tabla.forEach(row => {
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td>${row.fecha}</td>
                <td class="num">${row.comision.toFixed(2)}</td>
                <td class="num">${row.num_clientes}</td>
            </tr>`);
    });
    tbody.insertAdjacentHTML('beforeend', `
        <tr class="fila-total">
            <td>Total general</td>
            <td class="num">${l.total_comision.toFixed(2)}</td>
            <td class="num">${l.total_clientes}</td>
        </tr>`);

    if (chartCombo) chartCombo.destroy();
    chartCombo = new Chart(document.getElementById('chart-combo').getContext('2d'), {
        data: {
            labels: l.fechas,
            datasets: [
                {
                    type: 'bar',
                    label: 'NUM CLIENTES',
                    data: l.num_clientes,
                    backgroundColor: '#dc2626',
                    yAxisID: 'yClientes',
                    order: 2,
                },
                {
                    type: 'line',
                    label: 'COMISIÓN',
                    data: l.comisiones,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37,99,235,0.08)',
                    pointBackgroundColor: '#2563eb',
                    pointRadius: 5,
                    tension: 0.3,
                    yAxisID: 'yComision',
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'bottom', labels: { font: { size: 12 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ctx.dataset.label === 'COMISIÓN'
                            ? ` COMISIÓN: $${ctx.parsed.y.toFixed(2)}`
                            : ` NUM CLIENTES: ${ctx.parsed.y}`,
                    },
                },
            },
            scales: {
                yClientes: {
                    type: 'linear', position: 'left',
                    ticks: { stepSize: 1 }, grid: { drawOnChartArea: false },
                },
                yComision: {
                    type: 'linear', position: 'right',
                    grid: { color: 'rgba(0,0,0,0.05)' },
                },
            },
        },
    });
}

// ── Bloque 3: Correos ─────────────────────────────────────────
function renderizarCorreos(c, periodo) {
    document.getElementById('titulo-correos').textContent =
        `GESTIÓN EXTRAJUDICIAL ${periodo} — ${c.titulo}`;
    document.getElementById('periodo-correos').textContent =
        `Período: ${c.periodo_correos}`;

    const tbody = document.getElementById('body-correos');
    tbody.innerHTML = '';
    c.tabla.forEach(row => {
        const esTotalRow = row.concepto === 'Total enviados';
        const trClass = esTotalRow ? 'class="fila-total"' : '';
        tbody.insertAdjacentHTML('beforeend', `
            <tr ${trClass}>
                <td>${row.concepto}</td>
                <td class="num">${row.cantidad}</td>
                <td class="num">${row.porcentaje.toFixed(2)}%</td>
            </tr>`);
    });

    if (chartCorreos) chartCorreos.destroy();
    // Mostramos solo Entregados, No entregados, Leídos, No leídos (sin "Total")
    chartCorreos = new Chart(document.getElementById('chart-correos').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: c.labels,
            datasets: [{
                data: c.values,
                backgroundColor: CORREOS_COLORS,
                borderWidth: 2,
                borderColor: '#fff',
            }],
        },
        options: {
            cutout: '55%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { size: 11 }, padding: 10 },
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const pct = ((ctx.parsed / c.total) * 100).toFixed(1);
                            return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}
