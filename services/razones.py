"""
razones.py — Generación de documentos Word de razones de notificación
"""

import os

import pandas as pd
from docx import Document

from .documentos import reemplazar_en_documento
from .fechas import formatear_fechas_notificacion


def generar_razones(
    df: pd.DataFrame,
    plantilla_path: str,
    output_dir: str,
    dic_fechas: dict | None = None,
) -> list[str]:
    """
    Genera los documentos Word a partir del DataFrame y la plantilla.

    Args:
        df: DataFrame con columnas Email, NOMBRE_CLIENTE, NUMERO_TITULO, CUENTA_CONTRATO.
        plantilla_path: Ruta de la plantilla .docx.
        output_dir: Directorio donde guardar los documentos generados.
        dic_fechas: dict email → [fechas] (opcional, desde CSV de CPanel).

    Returns:
        Lista de rutas de archivos generados.
    """
    # Agrupar emails por NUMERO_TITULO
    emails_por_titulo = df.groupby("NUMERO_TITULO")["Email"].apply(list).to_dict()

    # Si hay fechas, asignar FECHA_NOTIFICACION al DataFrame
    if dic_fechas:
        dic_lower = {k.lower().strip(): v for k, v in dic_fechas.items()}
        df["FECHA_NOTIFICACION"] = df["Email"].apply(
            lambda email: ", ".join(dic_lower.get(str(email).lower().strip(), []))
        )

    archivos_generados = []

    for numero_titulo, emails in emails_por_titulo.items():
        datos = df[df["NUMERO_TITULO"] == numero_titulo].iloc[0]
        correos = ", ".join(str(e) for e in emails)

        # Obtener fechas formateadas
        fechas_texto = ""
        if dic_fechas and "FECHA_NOTIFICACION" in df.columns:
            fechas_texto = formatear_fechas_notificacion(datos.get("FECHA_NOTIFICACION", ""))

        # Cargar plantilla fresca y reemplazar marcadores
        doc = Document(plantilla_path)
        reemplazar_en_documento(doc, {
            "TITULO_CREDITO": str(datos["CUENTA_CONTRATO"]),
            "NOMBRE_CLIENTE": str(datos["NOMBRE_CLIENTE"]),
            "CEDULA_CLIENTE": str(numero_titulo),
            "CORREO": correos,
            "FECHAS": fechas_texto,
        })

        # Guardar documento
        nombre = f"Razon_{datos['CUENTA_CONTRATO']}_{numero_titulo}.docx"
        filepath = os.path.join(output_dir, nombre)
        doc.save(filepath)
        archivos_generados.append(filepath)

    return archivos_generados
