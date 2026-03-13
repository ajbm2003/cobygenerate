/**
 * cruces.js — Lógica de cruces de datos
 * =====================================
 */

import { showStatus, setupFileInput, downloadBlob, setButtonLoading } from './utils.js';

// === Elementos del DOM ===
const form = document.getElementById('form-cruces');
const archivo1Input = document.getElementById('archivo1-input');
const archivo2Input = document.getElementById('archivo2-input');
const archivo1Area = document.getElementById('archivo1-area');
const archivo2Area = document.getElementById('archivo2-area');
const archivo1Name = document.getElementById('archivo1-name');
const archivo2Name = document.getElementById('archivo2-name');
const submitBtn = document.getElementById('submit-btn');
const statusDiv = document.getElementById('status');

const faseUpload = document.getElementById('fase-upload');
const faseResultados = document.getElementById('fase-resultados');
const columnasSection = document.getElementById('columnas-section');
const columnasGrid = document.getElementById('columnas-grid');
const tablaResultados = document.getElementById('tabla-resultados');
const tablaDatos = document.getElementById('tabla-datos');
const tablaHead = document.getElementById('tabla-head');
const tablaBody = document.getElementById('tabla-body');
const totalCoincidenciasDiv = document.getElementById('total-coincidencias');
const btnAplicarFiltro = document.getElementById('btn-aplicar-filtro');
const btnVolver = document.getElementById('btn-volver');
const btnDescargar = document.getElementById('btn-descargar');

// Estado global
let datosActuales = null;
let columnasDisponibles = [];

// === Verificar que los archivos requeridos estén seleccionados ===
function checkReady() {
    submitBtn.disabled = !(archivo1Input.files.length > 0 && archivo2Input.files.length > 0);
}

// === Configurar inputs de archivo ===
setupFileInput(archivo1Input, archivo1Area, archivo1Name, checkReady);
setupFileInput(archivo2Input, archivo2Area, archivo2Name, checkReady);

// === Envío del formulario (Procesar cruces) ===
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('archivo1', archivo1Input.files[0]);
    formData.append('archivo2', archivo2Input.files[0]);

    setButtonLoading(submitBtn, true);
    showStatus(statusDiv, '⏳ Procesando cruces... Por favor espera.', 'info');

    try {
        const response = await fetch('/procesar-cruces', {
            method: 'POST',
            body: formData,
        });

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

        const resultado = await response.json();
        datosActuales = resultado.datos;
        columnasDisponibles = resultado.columnas;

        // Mostrar resultados
        mostrarFaseResultados(resultado);
        showStatus(statusDiv, '✅ ¡Cruces procesados exitosamente!', 'success');

    } catch (err) {
        showStatus(statusDiv, '❌ Error de conexión: ' + err.message, 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
});

// === Mostrar fase de resultados ===
function mostrarFaseResultados(resultado) {
    // Ocultar fase de upload
    faseUpload.style.display = 'none';

    // Actualizar total
    totalCoincidenciasDiv.textContent = `Se encontraron ${resultado.total_coincidencias} coincidencias`;

    // Generar checkboxes de columnas
    columnasGrid.innerHTML = '';
    columnasDisponibles.forEach(columna => {
        const div = document.createElement('div');
        div.className = 'columna-checkbox';
        div.innerHTML = `
            <input type="checkbox" id="col-${columna}" value="${columna}" checked>
            <label for="col-${columna}">${columna}</label>
        `;
        columnasGrid.appendChild(div);
    });

    // Mostrar secciones
    columnasSection.classList.add('visible');
    faseResultados.style.display = 'block';

    // Mostrar tabla con todas las columnas inicialmente
    mostrarTabla(datosActuales, columnasDisponibles);
}

// === Mostrar tabla con datos ===
function mostrarTabla(datos, columnas) {
    // Limpiar tabla
    tablaHead.innerHTML = '';
    tablaBody.innerHTML = '';

    if (!datos || datos.length === 0) {
        tablaBody.innerHTML = '<tr><td colspan="' + columnas.length + '" style="text-align: center;">No hay datos para mostrar</td></tr>';
        return;
    }

    // Headers
    columnas.forEach(columna => {
        const th = document.createElement('th');
        th.textContent = columna;
        tablaHead.appendChild(th);
    });

    // Filas
    datos.forEach(fila => {
        const tr = document.createElement('tr');
        columnas.forEach(columna => {
            const td = document.createElement('td');
            const valor = fila[columna] || '-';
            td.textContent = String(valor).substring(0, 50); // Limitar longitud
            tr.appendChild(td);
        });
        tablaBody.appendChild(tr);
    });

    tablaResultados.classList.add('visible');
    btnDescargar.style.display = 'inline-block';
}

// === Aplicar filtro de columnas ===
btnAplicarFiltro.addEventListener('click', () => {
    const columnasSeleccionadas = Array.from(
        document.querySelectorAll('#columnas-grid input[type="checkbox"]:checked')
    ).map(input => input.value);

    if (columnasSeleccionadas.length === 0) {
        showStatus(statusDiv, '❌ Debes seleccionar al menos una columna', 'error');
        return;
    }

    mostrarTabla(datosActuales, columnasSeleccionadas);
});

// === Descargar Excel ===
btnDescargar.addEventListener('click', async () => {
    const columnasSeleccionadas = Array.from(
        document.querySelectorAll('#columnas-grid input[type="checkbox"]:checked')
    ).map(input => input.value);

    if (columnasSeleccionadas.length === 0) {
        showStatus(statusDiv, '❌ Debes seleccionar al menos una columna', 'error');
        return;
    }

    setButtonLoading(btnDescargar, true);
    showStatus(statusDiv, '⏳ Generando Excel...', 'info');

    try {
        const payload = {
            datos: datosActuales,
            columnas_seleccionadas: columnasSeleccionadas,
        };

        const response = await fetch('/descargar-cruces', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}`);
        }

        const blob = await response.blob();
        downloadBlob(blob, 'cruces_resultado.xlsx');
        showStatus(statusDiv, '✅ ¡Descarga iniciada!', 'success');

    } catch (err) {
        showStatus(statusDiv, '❌ Error al descargar: ' + err.message, 'error');
    } finally {
        setButtonLoading(btnDescargar, false);
    }
});

// === Volver ===
btnVolver.addEventListener('click', () => {
    faseResultados.style.display = 'none';
    faseUpload.style.display = 'block';
    statusDiv.textContent = '';
    datosActuales = null;
    columnasDisponibles = [];
});
