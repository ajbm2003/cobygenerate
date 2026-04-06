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
from datetime import datetime
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

def formatear_fecha_larga_es(fecha: datetime) -> str:
    """Devuelve fecha en formato: '19 de marzo del 2026'."""
    return f"{fecha.day} de {MESES_ES[fecha.month]} del {fecha.year}"

from services.fechas import procesar_csv_fechas
from services.razones import generar_razones
from services.ordenes_pago import extraer_registros_pdfs, cruzar_con_excel, generar_nombre_archivo
from services.generar_documentos import generar_documentos_desde_excel
from services.preprocesamiento import (
    preprocesar_datos_opis,
    obtener_reemplazos_sexo,
    obtener_reemplazos_auto_de_pago,
)
from services.cruces import cruzar_archivos, filtrar_columnas_resultado
import json

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


@app.get("/generar-archivos", response_class=HTMLResponse, summary="Interfaz — Generación de Archivos")
async def pagina_generar_archivos():
    return HTMLResponse((BASE_DIR / "templates" / "generar_archivos.html").read_text(encoding="utf-8"))


@app.get("/cruces", response_class=HTMLResponse, summary="Interfaz — Cruces de datos")
async def pagina_cruces():
    return HTMLResponse((BASE_DIR / "templates" / "cruces.html").read_text(encoding="utf-8"))


@app.get("/cruces", response_class=HTMLResponse, summary="Interfaz — Cruces de datos")
async def pagina_cruces():
    return HTMLResponse((BASE_DIR / "templates" / "cruces.html").read_text(encoding="utf-8"))


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


# ============================================================
# Endpoint: Generación de archivos desde plantilla
# ============================================================

@app.post(
    "/generar-archivos",
    summary="Generar documentos Word desde Excel y plantilla",
    description=(
        "Sube un Excel (.xlsx) con datos y una plantilla Word (.docx) con marcadores [COLUMNA]. "
        "Genera un documento por cada fila del Excel reemplazando los marcadores. "
        "Devuelve un ZIP con todos los documentos generados."
    ),
)
async def generar_archivos_endpoint(
    excel: UploadFile = File(..., description="Excel (.xlsx) con datos"),
    plantilla: UploadFile = File(..., description="Plantilla Word (.docx) con marcadores [COLUMNA]"),
):
    _validar_extension(excel.filename, (".xlsx", ".xls"), "El archivo de datos debe ser .xlsx o .xls")
    _validar_extension(plantilla.filename, (".docx",), "La plantilla debe ser un archivo .docx")

    tmp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(tmp_dir, "documentos_generados")
    os.makedirs(output_dir)

    try:
        excel_path = os.path.join(tmp_dir, "datos.xlsx")
        plantilla_path = os.path.join(tmp_dir, "plantilla.docx")
        await _guardar_upload(excel, excel_path)
        await _guardar_upload(plantilla, plantilla_path)

        df = _leer_excel(excel_path)
        if df.empty:
            raise HTTPException(status_code=400, detail="El Excel no contiene filas de datos.")

        df.columns = [str(col).strip() for col in df.columns]

        # Preprocesar: si tiene VALOR1/VALOR2, agregar columnas en letras
        df = preprocesar_datos_opis(df)

        obtener_reemplazos_previos = None
        nombre_excel = (excel.filename or "").lower()
        es_ampliaciones = ("ampliaciones" in nombre_excel) or ("amplicaciones" in nombre_excel)
        if es_ampliaciones:
            df["HOY"] = formatear_fecha_larga_es(datetime.now())

        obtener_nombre_archivo = None
        if es_ampliaciones and "NOMBRES" in df.columns:
            def _nombre_archivo_ampliaciones(row, i):
                nombre_cliente = str(row.get("NOMBRES", "")).strip()
                if not nombre_cliente:
                    return f"documento-{i + 1}"
                return f"documento-{nombre_cliente}"

            obtener_nombre_archivo = _nombre_archivo_ampliaciones
        if es_ampliaciones:
            def _reemplazos_ampliaciones(row):
                reemplazos = []
                if "SEXO" in df.columns:
                    reemplazos.extend(obtener_reemplazos_sexo(row.get("SEXO", "")))
                if "AUTO DE PAGO" in df.columns:
                    reemplazos.extend(obtener_reemplazos_auto_de_pago(row.get("AUTO DE PAGO", "")))
                return reemplazos

            obtener_reemplazos_previos = _reemplazos_ampliaciones

        archivos = generar_documentos_desde_excel(
            df,
            plantilla_path,
            output_dir,
            obtener_reemplazos_previos=obtener_reemplazos_previos,
            obtener_nombre_archivo=obtener_nombre_archivo,
        )
        if not archivos:
            raise HTTPException(status_code=400, detail="No se generaron documentos.")

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for archivo in archivos:
                zf.write(archivo, os.path.basename(archivo))
        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=documentos_generados.zip",
                "X-Total-Docs": str(len(archivos)),
            },
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# Endpoint: Cruces de datos entre dos archivos
# ============================================================

@app.post(
    "/procesar-cruces",
    summary="Procesar cruce de datos",
    description=(
        "Sube dos archivos Excel (.xlsx) o CSV (.csv) y cruza por el campo JUICIO. "
        "Devuelve las columnas disponibles y los registros que coinciden."
    ),
)
async def procesar_cruces_endpoint(
    archivo1: UploadFile = File(..., description="Primer archivo Excel o CSV"),
    archivo2: UploadFile = File(..., description="Segundo archivo Excel o CSV"),
):
    _validar_extension(
        archivo1.filename,
        (".xlsx", ".xls", ".csv"),
        "El primer archivo debe ser .xlsx, .xls o .csv"
    )
    _validar_extension(
        archivo2.filename,
        (".xlsx", ".xls", ".csv"),
        "El segundo archivo debe ser .xlsx, .xls o .csv"
    )

    tmp_dir = tempfile.mkdtemp()

    try:
        # Guardar archivos
        archivo1_path = os.path.join(tmp_dir, "archivo1.xlsx" if archivo1.filename.endswith((".xlsx", ".xls")) else "archivo1.csv")
        archivo2_path = os.path.join(tmp_dir, "archivo2.xlsx" if archivo2.filename.endswith((".xlsx", ".xls")) else "archivo2.csv")
        
        await _guardar_upload(archivo1, archivo1_path)
        await _guardar_upload(archivo2, archivo2_path)

        # Leer archivos
        if archivo1_path.endswith(".csv"):
            df1 = pd.read_csv(archivo1_path)
        else:
            df1 = _leer_excel(archivo1_path)
        
        if archivo2_path.endswith(".csv"):
            df2 = pd.read_csv(archivo2_path)
        else:
            df2 = _leer_excel(archivo2_path)

        # Normalizar nombres de columnas
        df1.columns = [str(col).strip() for col in df1.columns]
        df2.columns = [str(col).strip() for col in df2.columns]

        # Realizar cruce
        resultado = cruzar_archivos(df1, df2)

        # Guardar en sesión (en memoria)
        coincidencias_json = resultado["coincidencias"].to_json(orient="records", force_ascii=False)

        return {
            "columnas": resultado["columnas"],
            "total_coincidencias": resultado["total_coincidencias"],
            "datos": json.loads(coincidencias_json),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar archivos: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post(
    "/descargar-cruces",
    summary="Descargar resultados de cruces",
    description="Descarga los resultados del cruce como archivo Excel con las columnas seleccionadas.",
)
async def descargar_cruces_endpoint(payload: dict):
    """Endpoint para descargar los datos en Excel."""
    datos = payload.get("datos")
    columnas_seleccionadas = payload.get("columnas_seleccionadas")
    
    if not datos or not columnas_seleccionadas:
        raise HTTPException(status_code=400, detail="Datos o columnas vacías")

    try:
        # Crear DataFrame desde los datos
        df = pd.DataFrame(datos)
        
        # Filtrar columnas
        df_filtrado = filtrar_columnas_resultado(df, columnas_seleccionadas)

        # Generar Excel en memoria
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name="Cruces")
        output_buffer.seek(0)

        return StreamingResponse(
            output_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=cruces_resultado.xlsx",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al generar descarga: {str(e)}")
