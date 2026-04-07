"""
documentos.py — Reemplazo de marcadores en documentos Word (.docx)
"""

from docx import Document
from .docx_utils import iterar_parrafos_docx
from .formatos import formatear_valor1


def reemplazar_en_parrafo(parrafo, reemplazos: dict) -> None:
    """Reemplaza marcadores [CAMPO] en un párrafo conservando el formato."""
    for marcador, valor in reemplazos.items():
        marcador_normalizado = str(marcador).strip().strip("[]").upper()
        valor_texto = formatear_valor1(valor) if marcador_normalizado == "VALOR1" else str(valor)

        if marcador not in parrafo.text:
            continue
        # Intentar reemplazar en cada run individual
        for run in parrafo.runs:
            if marcador in run.text:
                run.text = run.text.replace(marcador, valor_texto)
        # Si el marcador quedó dividido entre runs, unir y reemplazar
        if marcador in "".join(r.text for r in parrafo.runs):
            texto_completo = parrafo.text
            if marcador in texto_completo:
                texto_nuevo = texto_completo.replace(marcador, valor_texto)
                if parrafo.runs:
                    for j in range(len(parrafo.runs) - 1, 0, -1):
                        parrafo.runs[j].text = ""
                    parrafo.runs[0].text = texto_nuevo


def reemplazar_en_documento(doc: Document, reemplazos: dict) -> None:
    """Reemplaza marcadores en todo el documento (párrafos, tablas, encabezados, pies)."""
    for parrafo in iterar_parrafos_docx(doc):
        reemplazar_en_parrafo(parrafo, reemplazos)
