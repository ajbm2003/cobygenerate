/**
 * ordenes_pago.js — Lógica del módulo Órdenes de Pago Inmediato
 * ===============================================================
 */

import { showStatus, setupFileInput, downloadBlob, setButtonLoading } from './utils.js';

// === Elementos del DOM ===
const form            = document.getElementById('form-ordenes');
const excelInput      = document.getElementById('excel-base-input');
const pdfsInput       = document.getElementById('pdfs-input');
const excelArea       = document.getElementById('excel-base-area');
const pdfsArea        = document.getElementById('pdfs-area');
const excelName       = document.getElementById('excel-base-name');
const pdfsName        = document.getElementById('pdfs-name');
const pdfsList        = document.getElementById('pdfs-list');
const submitBtn       = document.getElementById('submit-ordenes-btn');
const statusDiv       = document.getElementById('status-ordenes');
const statsDiv        = document.getElementById('stats-ordenes');
const previewSection  = document.getElementById('preview-section');
const previewTbody    = document.getElementById('preview-tbody');
const previewInfo     = document.getElementById('preview-info');

// Almacenar archivos PDF (para soportar drop de carpeta y selección múltiple)
let pdfFiles = [];

// === Verificar que los archivos requeridos estén seleccionados ===
function checkReady() {
    submitBtn.disabled = !(excelInput.files.length > 0 && pdfFiles.length > 0);
}

// === Configurar el input del Excel ===
setupFileInput(excelInput, excelArea, excelName, checkReady);

// === Extraer número del nombre del PDF ===
function extractNumero(filename) {
    const match = filename.match(/-(\d+-\d+)\.pdf$/i);
    return match ? match[1] : null;
}

// === Mostrar lista de PDFs detectados ===
function renderPdfList() {
    if (pdfFiles.length === 0) {
        pdfsList.innerHTML = '';
        pdfsName.textContent = '';
        pdfsArea.classList.remove('has-file');
        return;
    }

    pdfsName.textContent = `✅ ${pdfFiles.length} archivo(s) PDF seleccionado(s)`;
    pdfsArea.classList.add('has-file');

    // Mostrar los primeros 10 + resumen
    const maxShow = 10;
    let html = '<div class="pdf-chips">';
    const toShow = pdfFiles.slice(0, maxShow);
    for (const f of toShow) {
        const numero = extractNumero(f.name);
        const tag = numero ? `JC-PIC-${numero}` : '⚠️ sin número';
        html += `<span class="file-chip">📄 ${f.name} → <strong>${tag}</strong></span>`;
    }
    if (pdfFiles.length > maxShow) {
        html += `<span class="file-chip">… y ${pdfFiles.length - maxShow} archivo(s) más</span>`;
    }
    html += '</div>';
    pdfsList.innerHTML = html;
}

// === Configurar input de PDFs (carpeta / múltiple) ===
pdfsInput.addEventListener('change', () => {
    pdfFiles = [];
    if (pdfsInput.files.length > 0) {
        for (const f of pdfsInput.files) {
            if (f.name.toLowerCase().endsWith('.pdf')) {
                pdfFiles.push(f);
            }
        }
    }
    renderPdfList();
    checkReady();
});

// Drag & drop visual feedback para el área de PDFs
pdfsArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    pdfsArea.classList.add('dragover');
});

pdfsArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    pdfsArea.classList.remove('dragover');
});

pdfsArea.addEventListener('drop', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    pdfsArea.classList.remove('dragover');

    pdfFiles = [];

    // Intentar leer carpetas con DataTransferItem.webkitGetAsEntry
    const items = e.dataTransfer.items;
    if (items && items.length > 0) {
        const filePromises = [];
        for (const item of items) {
            const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
            if (entry) {
                filePromises.push(readEntry(entry));
            }
        }
        const results = await Promise.all(filePromises);
        pdfFiles = results.flat().filter(f => f.name.toLowerCase().endsWith('.pdf'));
    } else {
        // Fallback: archivos directos
        for (const f of e.dataTransfer.files) {
            if (f.name.toLowerCase().endsWith('.pdf')) {
                pdfFiles.push(f);
            }
        }
    }

    renderPdfList();
    checkReady();
});

// === Leer entradas del filesystem recursivamente ===
function readEntry(entry) {
    return new Promise((resolve) => {
        if (entry.isFile) {
            entry.file((f) => resolve([f]));
        } else if (entry.isDirectory) {
            const reader = entry.createReader();
            const allFiles = [];
            const readBatch = () => {
                reader.readEntries(async (entries) => {
                    if (entries.length === 0) {
                        resolve(allFiles);
                        return;
                    }
                    const promises = entries.map(e => readEntry(e));
                    const results = await Promise.all(promises);
                    allFiles.push(...results.flat());
                    readBatch(); // Leer siguiente lote
                });
            };
            readBatch();
        } else {
            resolve([]);
        }
    });
}

// === Envío del formulario ===
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('excel', excelInput.files[0]);

    // Agregar todos los PDFs
    for (const pdf of pdfFiles) {
        formData.append('pdfs', pdf);
    }

    setButtonLoading(submitBtn, true);
    showStatus(statusDiv, '⏳ Procesando órdenes de pago... Esto puede tardar unos segundos.', 'info');
    statsDiv.style.display = 'none';
    previewSection.style.display = 'none';

    const startTime = Date.now();

    try {
        const response = await fetch('/procesar-ordenes-pago', {
            method: 'POST',
            body: formData,
        });

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

        if (!response.ok) {
            let errorMsg = 'Error desconocido';
            try {
                const err = await response.json();
                errorMsg = err.detail || errorMsg;
            } catch (_) {
                errorMsg = `Error HTTP ${response.status}`;
            }
            showStatus(statusDiv, '❌ ' + errorMsg, 'error');
            return;
        }

        // Obtener el blob del Excel y descargarlo
        const blob = await response.blob();
        const hoy = new Date().toISOString().slice(0, 10);
        downloadBlob(blob, `NOTIFICACIONESCOACTIVA_OPI_${hoy}.xlsx`);

        showStatus(statusDiv, '✅ ¡Archivo generado exitosamente! Descarga iniciada.', 'success');

        // Mostrar estadísticas
        const totalPdfs = pdfFiles.length;
        const pdfsConNumero = pdfFiles.filter(f => extractNumero(f.name)).length;
        document.getElementById('stat-pdfs').textContent = totalPdfs;
        document.getElementById('stat-matches').textContent = pdfsConNumero;
        document.getElementById('stat-ordenes-time').textContent = elapsed + 's';
        statsDiv.style.display = 'flex';

        // Generar preview local
        generatePreview();

    } catch (err) {
        showStatus(statusDiv, '❌ Error de conexión: ' + err.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
});

// === Generar vista previa local basada en los PDFs ===
function generatePreview() {
    previewTbody.innerHTML = '';
    let count = 0;
    const maxPreview = 20;

    for (const f of pdfFiles) {
        const numero = extractNumero(f.name);
        if (!numero) continue;

        const cuenta = `JC-PIC-${numero}`;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td></td>
            <td class="pending">Desde Excel</td>
            <td class="pending">Desde Excel</td>
            <td><strong>${cuenta}</strong></td>
            <td>${f.name}</td>
        `;
        previewTbody.appendChild(tr);
        count++;
        if (count >= maxPreview) break;
    }

    if (count > 0) {
        previewInfo.textContent = pdfFiles.length > maxPreview
            ? `Mostrando ${maxPreview} de ${pdfFiles.length} registros. Los datos de NOMBRE_CLIENTE y NUMERO_TITULO se completan en el Excel descargado.`
            : `${count} registro(s). Los datos de NOMBRE_CLIENTE y NUMERO_TITULO se completan en el Excel descargado.`;
        previewSection.style.display = 'block';
    }
}
