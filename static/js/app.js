/**
 * app.js — Lógica principal de la aplicación
 * =============================================
 */

import { showStatus, setupFileInput, downloadBlob, setButtonLoading } from './utils.js';

// === Elementos del DOM ===
const form          = document.getElementById('form');
const excelInput    = document.getElementById('excel-input');
const plantillaInput = document.getElementById('plantilla-input');
const csvInput      = document.getElementById('csv-input');
const excelArea     = document.getElementById('excel-area');
const plantillaArea = document.getElementById('plantilla-area');
const csvArea       = document.getElementById('csv-area');
const excelName     = document.getElementById('excel-name');
const plantillaName = document.getElementById('plantilla-name');
const csvName       = document.getElementById('csv-name');
const submitBtn     = document.getElementById('submit-btn');
const statusDiv     = document.getElementById('status');
const statsDiv      = document.getElementById('stats');

// === Verificar que los archivos requeridos estén seleccionados ===
function checkReady() {
    submitBtn.disabled = !(excelInput.files.length > 0 && plantillaInput.files.length > 0);
}

// === Configurar inputs de archivo ===
setupFileInput(excelInput, excelArea, excelName, checkReady);
setupFileInput(plantillaInput, plantillaArea, plantillaName, checkReady);
setupFileInput(csvInput, csvArea, csvName, null);

// === Envío del formulario ===
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('excel', excelInput.files[0]);
    formData.append('plantilla', plantillaInput.files[0]);
    if (csvInput.files.length > 0) {
        formData.append('csv_fechas', csvInput.files[0]);
    }

    setButtonLoading(submitBtn, true);
    showStatus(statusDiv, '⏳ Generando documentos... Esto puede tardar unos segundos.', 'info');
    statsDiv.style.display = 'none';

    const startTime = Date.now();

    try {
        const response = await fetch('/generar-razones', {
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

        // Obtener el blob del ZIP y descargarlo
        const blob = await response.blob();
        const sizeKB = (blob.size / 1024).toFixed(0);

        downloadBlob(blob, 'razones_notificacion.zip');

        showStatus(statusDiv, '✅ ¡Documentos generados exitosamente! Descarga iniciada.', 'success');

        // Mostrar estadísticas
        document.getElementById('stat-time').textContent = elapsed + 's';
        document.getElementById('stat-size').textContent = sizeKB + ' KB';
        document.getElementById('stat-docs').textContent = '✓';
        statsDiv.style.display = 'flex';

    } catch (err) {
        showStatus(statusDiv, '❌ Error de conexión: ' + err.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
});
