/**
 * generar_archivos.js — Lógica del módulo Generación de Archivos
 * ================================================================
 */

import { showStatus, setupFileInput, downloadBlob, setButtonLoading } from './utils.js';

// === Elementos del DOM ===
const form          = document.getElementById('form-generar');
const excelInput    = document.getElementById('excel-gen-input');
const plantillaInput = document.getElementById('plantilla-gen-input');
const excelArea     = document.getElementById('excel-gen-area');
const plantillaArea = document.getElementById('plantilla-gen-area');
const excelName     = document.getElementById('excel-gen-name');
const plantillaName = document.getElementById('plantilla-gen-name');
const submitBtn     = document.getElementById('submit-gen-btn');
const statusDiv     = document.getElementById('status-gen');
const statsDiv      = document.getElementById('stats-gen');

// === Verificar que los archivos requeridos estén seleccionados ===
function checkReady() {
    submitBtn.disabled = !(excelInput.files.length > 0 && plantillaInput.files.length > 0);
}

// === Configurar inputs de archivo ===
setupFileInput(excelInput, excelArea, excelName, checkReady);
setupFileInput(plantillaInput, plantillaArea, plantillaName, checkReady);

// === Envío del formulario ===
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('excel', excelInput.files[0]);
    formData.append('plantilla', plantillaInput.files[0]);

    setButtonLoading(submitBtn, true);
    showStatus(statusDiv, '⏳ Generando documentos... Esto puede tardar unos segundos.', 'info');
    statsDiv.style.display = 'none';

    const startTime = Date.now();

    try {
        const response = await fetch('/generar-archivos', {
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

        const blob = await response.blob();
        const sizeKB = (blob.size / 1024).toFixed(0);
        const totalDocs = response.headers.get('X-Total-Docs') || '?';

        downloadBlob(blob, 'documentos_generados.zip');

        showStatus(statusDiv, '✅ ¡Documentos generados exitosamente! Descarga iniciada.', 'success');

        document.getElementById('stat-gen-docs').textContent = totalDocs;
        document.getElementById('stat-gen-time').textContent = elapsed + 's';
        document.getElementById('stat-gen-size').textContent = sizeKB + ' KB';
        statsDiv.style.display = 'flex';

    } catch (err) {
        showStatus(statusDiv, '❌ Error de conexión: ' + err.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
});
