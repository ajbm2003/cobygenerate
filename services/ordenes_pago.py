"""
ordenes_pago.py — Procesamiento de órdenes de pago inmediato
"""

import os
import re
from datetime import datetime

import pandas as pd


# Patrón para extraer número del nombre del PDF
_PATRON_PDF = re.compile(r"-(\d+-\d+)\.pdf$", re.IGNORECASE)


def extraer_registros_pdfs(nombres_pdf: list[str]) -> list[dict]:
    """
    Extrae números de los nombres de archivos PDF y genera registros.

    Args:
        nombres_pdf: Lista de nombres de archivo PDF.

    Returns:
        Lista de dicts con CUENTA_CONTRATO y Attachment.
    """
    registros = []
    for nombre in nombres_pdf:
        nombre_base = os.path.basename(nombre)
        match = _PATRON_PDF.search(nombre_base)
        if match:
            registros.append({
                "CUENTA_CONTRATO": f"JC-PIC-{match.group(1)}",
                "Attachment": nombre_base,
            })
    return registros


def cruzar_con_excel(df_base: pd.DataFrame, registros: list[dict]) -> pd.DataFrame:
    """
    Cruza los registros extraídos de PDFs con el Excel base.

    Args:
        df_base: DataFrame del Excel con columnas 'ORDEN DE PAGO INMEDIATO',
                 'Nombre cliente', 'Cédula/RUC'.
        registros: Lista de dicts con CUENTA_CONTRATO y Attachment.

    Returns:
        DataFrame con columnas: Email, NOMBRE_CLIENTE, NUMERO_TITULO,
        CUENTA_CONTRATO, Attachment.
    """
    df_pdfs = pd.DataFrame(registros)

    # Asegurar tipos string para el merge
    df_base["ORDEN DE PAGO INMEDIATO"] = df_base["ORDEN DE PAGO INMEDIATO"].astype(str).str.strip()
    df_pdfs["CUENTA_CONTRATO"] = df_pdfs["CUENTA_CONTRATO"].astype(str).str.strip()

    # Merge
    df_merged = df_pdfs.merge(
        df_base[["ORDEN DE PAGO INMEDIATO", "Nombre cliente", "Cédula/RUC"]],
        left_on="CUENTA_CONTRATO",
        right_on="ORDEN DE PAGO INMEDIATO",
        how="left",
    )

    return pd.DataFrame({
        "Email": "",
        "NOMBRE_CLIENTE": df_merged["Nombre cliente"],
        "NUMERO_TITULO": df_merged["Cédula/RUC"],
        "CUENTA_CONTRATO": df_merged["CUENTA_CONTRATO"].str.replace("JC-PIC-", "", regex=False),
        "Attachment": df_merged["Attachment"],
    })


def generar_nombre_archivo() -> str:
    """Genera el nombre del archivo de salida con la fecha actual."""
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    return f"NOTIFICACIONESCOACTIVA_OPI_{fecha_hoy}.xlsx"
