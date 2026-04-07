"""
razones.py — Generación de documentos Word de razones de notificación
"""

import os
import re

import pandas as pd
from docx import Document

from .documentos import reemplazar_en_documento
from .fechas import formatear_fechas_notificacion


def _normalizar_cedula(valor) -> str:
    """Normaliza una cédula/RUC conservando solo dígitos."""
    return re.sub(r"\D", "", str(valor or "").strip())


def _extraer_cedula_de_correo(email: str) -> str:
    """Extrae secuencias de 10 o 13 dígitos del correo del destinatario."""
    texto = str(email or "").strip()
    if not texto:
        return ""

    # Priorizar longitudes típicas: cédula (10) o RUC (13)
    for patron in (r"\d{13}", r"\d{10}"):
        match = re.search(patron, texto)
        if match:
            return match.group(0)

    # Fallback: si hay dígitos, usarlos completos
    return _normalizar_cedula(texto)


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

    # Si hay fechas, asignar FECHA_NOTIFICACION al DataFrame.
    # Regla principal: cruzar por cédula extraída del correo del CSV.
    # Regla fallback: cruzar por email exacto para compatibilidad.
    if dic_fechas:
        dic_lower = {k.lower().strip(): v for k, v in dic_fechas.items()}

        fechas_por_cedula: dict[str, list[str]] = {}
        for destinatario, fechas in dic_fechas.items():
            cedula = _extraer_cedula_de_correo(destinatario)
            if not cedula:
                continue
            fechas_por_cedula.setdefault(cedula, []).extend([str(f) for f in fechas if str(f).strip()])

        def _obtener_fechas_fila(row) -> str:
            cedula_titulo = _normalizar_cedula(row.get("NUMERO_TITULO", ""))
            if cedula_titulo and cedula_titulo in fechas_por_cedula:
                return ", ".join(fechas_por_cedula[cedula_titulo])

            email = str(row.get("Email", "")).lower().strip()
            return ", ".join(dic_lower.get(email, []))

        df["FECHA_NOTIFICACION"] = df.apply(_obtener_fechas_fila, axis=1)

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

        nombre = f"Razon_{datos['CUENTA_CONTRATO']}_{numero_titulo}.docx"
        filepath = os.path.join(output_dir, nombre)
        doc.save(filepath)
        archivos_generados.append(filepath)

    return archivos_generados
