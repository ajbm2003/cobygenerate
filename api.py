"""
API para generar Razones de Notificación y procesar Órdenes de Pago
====================================================================
Ejecutar con:
    uvicorn api:app --reload --port 8000

Documentación interactiva en:
    http://localhost:8000/docs
"""

import os
import shutil
import tempfile
import zipfile
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from services.fechas import procesar_csv_fechas
from services.razones import generar_razones
from services.ordenes_pago import extraer_registros_pdfs, cruzar_con_excel, generar_nombre_archivo

# ============================================================
# Configuración de la aplicación
# ============================================================

app = FastAPI(
    title="Generador de Razones de Notificación",
    description="Sube un Excel con los datos y una plantilla Word. Descarga un ZIP con las razones generadas.",
    version="1.0.0",
)

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ============================================================
# Helpers
# ============================================================

def _validar_extension(filename: str, extensiones: tuple, mensaje: str):
    """Valida que el archivo tenga la extensión correcta."""
    if not filename.endswith(extensiones):
        raise HTTPException(status_code=400, detail=mensaje)


def _leer_excel(path: str) -> pd.DataFrame:
    """Lee un archivo Excel y retorna un DataFrame."""
    try:
        return pd.read_excel(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el Excel: {e}")


def _validar_columnas(df: pd.DataFrame, requeridas: set):
    """Valida que el DataFrame contenga las columnas requeridas."""
    faltantes = requeridas - set(df.columns)
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Columnas faltantes en el Excel: {', '.join(faltantes)}",
        )


async def _guardar_upload(upload: UploadFile, destino: str):
    """Guarda un archivo subido en disco."""
    with open(destino, "wb") as f:
        f.write(await upload.read())


# ============================================================
# Páginas HTML
# ============================================================

@app.get("/", response_class=HTMLResponse, summary="Interfaz — Razones de Notificación")
async def pagina_razones():
    return HTMLResponse((BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8"))


@app.get("/ordenes-pago", response_class=HTMLResponse, summary="Interfaz — Órdenes de Pago")
async def pagina_ordenes_pago():
    return HTMLResponse((BASE_DIR / "templates" / "ordenes_pago.html").read_text(encoding="utf-8"))


# ============================================================
# Endpoint: Generar razones de notificación
# ============================================================

@app.post(
    "/generar-razones",
    summary="Generar razones de notificación",
    description=(
        "Sube un Excel (.xlsx) con columnas: Email, NOMBRE_CLIENTE, NUMERO_TITULO, CUENTA_CONTRATO. "
        "Una plantilla Word (.docx) con marcadores. Opcionalmente un CSV de fechas de CPanel. "
        "Devuelve un ZIP con los documentos generados."
    ),
)
async def generar_razones_endpoint(
    excel: UploadFile = File(..., description="Excel (.xlsx) con datos de clientes"),
    plantilla: UploadFile = File(..., description="Plantilla Word (.docx) con marcadores"),
    csv_fechas: Optional[UploadFile] = File(None, description="CSV de fechas de CPanel (opcional)"),
):
    _validar_extension(excel.filename, (".xlsx", ".xls"), "El archivo de datos debe ser .xlsx o .xls")
    _validar_extension(plantilla.filename, (".docx",), "La plantilla debe ser un archivo .docx")
    if csv_fechas:
        _validar_extension(csv_fechas.filename, (".csv",), "El archivo de fechas debe ser .csv")

    tmp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(tmp_dir, "razones_notificacion")
    os.makedirs(output_dir)

    try:
        # Guardar archivos
        excel_path = os.path.join(tmp_dir, "datos.xlsx")
        plantilla_path = os.path.join(tmp_dir, "plantilla.docx")
        await _guardar_upload(excel, excel_path)
        await _guardar_upload(plantilla, plantilla_path)

        # Procesar CSV de fechas (opcional)
        dic_fechas = None
        if csv_fechas:
            csv_path = os.path.join(tmp_dir, "fechas.csv")
            await _guardar_upload(csv_fechas, csv_path)
            try:
                dic_fechas = procesar_csv_fechas(csv_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error al procesar el CSV de fechas: {e}")

        # Leer y validar Excel
        df = _leer_excel(excel_path)
        _validar_columnas(df, {"Email", "NOMBRE_CLIENTE", "NUMERO_TITULO", "CUENTA_CONTRATO"})

        # Generar documentos
        archivos = generar_razones(df, plantilla_path, output_dir, dic_fechas)
        if not archivos:
            raise HTTPException(status_code=400, detail="No se generaron documentos. Verifica los datos.")

        # Crear ZIP en memoria
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for archivo in archivos:
                zf.write(archivo, os.path.basename(archivo))
        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=razones_notificacion.zip"},
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# Endpoint: Procesar órdenes de pago inmediato
# ============================================================

@app.post(
    "/procesar-ordenes-pago",
    summary="Procesar órdenes de pago inmediato",
    description=(
        "Sube un Excel base con columnas 'ORDEN DE PAGO INMEDIATO', 'Nombre cliente', 'Cédula/RUC', "
        "y archivos PDF. Extrae números de los PDFs, cruza con el Excel y devuelve un Excel resultado."
    ),
)
async def procesar_ordenes_pago_endpoint(
    excel: UploadFile = File(..., description="Excel base con datos de clientes"),
    pdfs: List[UploadFile] = File(..., description="Archivos PDF de órdenes de pago"),
):
    _validar_extension(excel.filename, (".xlsx", ".xls"), "El archivo de datos debe ser .xlsx o .xls")
    if not pdfs:
        raise HTTPException(status_code=400, detail="Debe subir al menos un archivo PDF")

    tmp_dir = tempfile.mkdtemp()

    try:
        # Guardar y leer Excel
        excel_path = os.path.join(tmp_dir, "base.xlsx")
        await _guardar_upload(excel, excel_path)
        df_base = _leer_excel(excel_path)
        _validar_columnas(df_base, {"ORDEN DE PAGO INMEDIATO", "Nombre cliente", "Cédula/RUC"})

        # Extraer números de los PDFs
        nombres_pdf = [pdf.filename for pdf in pdfs]
        registros = extraer_registros_pdfs(nombres_pdf)
        if not registros:
            raise HTTPException(
                status_code=400,
                detail="No se pudo extraer ningún número de los PDFs. "
                       "Formato esperado: ORDEN DE PAGO INMEDIATO-XXXXXX-YYYY.pdf",
            )

        # Cruzar con Excel y generar resultado
        df_resultado = cruzar_con_excel(df_base, registros)
        nombre_archivo = generar_nombre_archivo()

        # Generar Excel de salida
        output_path = os.path.join(tmp_dir, nombre_archivo)
        df_resultado.to_excel(output_path, index=False, sheet_name="Resultado")

        output_buffer = BytesIO()
        with open(output_path, "rb") as f:
            output_buffer.write(f.read())
        output_buffer.seek(0)

        return StreamingResponse(
            output_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
