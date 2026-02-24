"""
documentos.py — Reemplazo de marcadores en documentos Word (.docx)
"""

from docx import Document


def reemplazar_en_parrafo(parrafo, reemplazos: dict) -> None:
    """Reemplaza marcadores [CAMPO] en un párrafo conservando el formato."""
    for marcador, valor in reemplazos.items():
        if marcador not in parrafo.text:
            continue
        # Intentar reemplazar en cada run individual
        for run in parrafo.runs:
            if marcador in run.text:
                run.text = run.text.replace(marcador, str(valor))
        # Si el marcador quedó dividido entre runs, unir y reemplazar
        if marcador in "".join(r.text for r in parrafo.runs):
            texto_completo = parrafo.text
            if marcador in texto_completo:
                texto_nuevo = texto_completo.replace(marcador, str(valor))
                if parrafo.runs:
                    for j in range(len(parrafo.runs) - 1, 0, -1):
                        parrafo.runs[j].text = ""
                    parrafo.runs[0].text = texto_nuevo


def reemplazar_en_documento(doc: Document, reemplazos: dict) -> None:
    """Reemplaza marcadores en todo el documento (párrafos, tablas, encabezados, pies)."""
    for parrafo in doc.paragraphs:
        reemplazar_en_parrafo(parrafo, reemplazos)

    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for parrafo in celda.paragraphs:
                    reemplazar_en_parrafo(parrafo, reemplazos)

    for section in doc.sections:
        for parrafo in section.header.paragraphs:
            reemplazar_en_parrafo(parrafo, reemplazos)
        for parrafo in section.footer.paragraphs:
            reemplazar_en_parrafo(parrafo, reemplazos)
