"""
documentos.py — Reemplazo de marcadores en documentos Word (.docx)
"""

from docx import Document


def _formatear_valor1(valor) -> str:
    """Convierte VALOR1 a número con 2 decimales. Si falta o es inválido, usa 40.00."""
    if valor is None:
        return "40.00"

    texto = str(valor).strip()
    if texto == "":
        return "40.00"

    # Soportar entradas comunes: "40", "40.5", "40,5", "1,234.56", "1234,56"
    normalizado = texto.replace(" ", "")
    if "," in normalizado and "." in normalizado:
        # Si tiene ambos separadores, asumir comas de miles
        normalizado = normalizado.replace(",", "")
    elif "," in normalizado:
        # Si solo tiene coma, tratarla como separador decimal
        normalizado = normalizado.replace(",", ".")

    try:
        numero = float(normalizado)
    except (TypeError, ValueError):
        return "40.00"

    return f"{numero:.2f}"


def reemplazar_en_parrafo(parrafo, reemplazos: dict) -> None:
    """Reemplaza marcadores [CAMPO] en un párrafo conservando el formato."""
    for marcador, valor in reemplazos.items():
        marcador_normalizado = str(marcador).strip().strip("[]").upper()
        valor_texto = _formatear_valor1(valor) if marcador_normalizado == "VALOR1" else str(valor)

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
