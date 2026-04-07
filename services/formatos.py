"""
formatos.py — Funciones compartidas de formateo de valores.
"""

import pandas as pd


def formatear_valor1(valor) -> str:
    """Formatea VALOR1 a número con 2 decimales. Si falta o es inválido, usa 40.00."""
    if valor is None or pd.isna(valor):
        return "40.00"

    texto = str(valor).strip()
    if texto == "":
        return "40.00"

    # Soporta: 40, 40.5, 40,5, 1,234.56, 1234,56
    normalizado = texto.replace(" ", "")
    if "," in normalizado and "." in normalizado:
        normalizado = normalizado.replace(",", "")
    elif "," in normalizado:
        normalizado = normalizado.replace(",", ".")

    try:
        numero = float(normalizado)
    except (TypeError, ValueError):
        return "40.00"

    return f"{numero:.2f}"
