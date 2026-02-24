/**
 * utils.js — Funciones utilitarias reutilizables
 * ================================================
 */

/**
 * Muestra un mensaje de estado en el contenedor indicado.
 * @param {HTMLElement} statusEl - Elemento DOM del status.
 * @param {string} message - Texto del mensaje.
 * @param {'success'|'error'|'info'} type - Tipo de mensaje.
 */
export function showStatus(statusEl, message, type) {
    statusEl.textContent = message;
    statusEl.className = 'status ' + type;
}

/**
 * Configura un input de archivo con feedback visual de drag & drop.
 * @param {HTMLInputElement} input - Input file.
 * @param {HTMLElement} area - Contenedor del área de upload.
 * @param {HTMLElement} nameEl - Elemento donde se muestra el nombre del archivo.
 * @param {Function} onChangeCallback - Callback cuando cambia el archivo.
 */
export function setupFileInput(input, area, nameEl, onChangeCallback) {
    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            nameEl.textContent = '✅ ' + input.files[0].name;
            area.classList.add('has-file');
        } else {
            nameEl.textContent = '';
            area.classList.remove('has-file');
        }
        if (onChangeCallback) onChangeCallback();
    });

    // Drag & drop visual feedback
    area.addEventListener('dragover', (e) => {
        e.preventDefault();
        area.classList.add('dragover');
    });
    area.addEventListener('dragleave', () => {
        area.classList.remove('dragover');
    });
    area.addEventListener('drop', () => {
        area.classList.remove('dragover');
    });
}

/**
 * Dispara la descarga de un Blob como archivo.
 * @param {Blob} blob - Datos del archivo.
 * @param {string} filename - Nombre para la descarga.
 */
export function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Activa el estado de carga en un botón.
 * @param {HTMLButtonElement} btn - Botón a modificar.
 * @param {boolean} loading - true para activar, false para desactivar.
 */
export function setButtonLoading(btn, loading) {
    if (loading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}
