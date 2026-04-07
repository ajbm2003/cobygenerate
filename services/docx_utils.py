"""
docx_utils.py — Utilidades compartidas para documentos Word (.docx).
"""

from collections.abc import Iterator


def iterar_parrafos_docx(doc) -> Iterator:
    """Itera todos los párrafos del documento, incluyendo tablas, encabezados y pies."""
    for parrafo in doc.paragraphs:
        yield parrafo

    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for parrafo in celda.paragraphs:
                    yield parrafo

    for section in doc.sections:
        for parrafo in section.header.paragraphs:
            yield parrafo
        for parrafo in section.footer.paragraphs:
            yield parrafo
