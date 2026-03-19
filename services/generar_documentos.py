"""
generar_documentos.py — Genera documentos Word reemplazando marcadores [COLUMNA]
con los valores de cada fila de un DataFrame.
"""

import os
from typing import List

import pandas as pd
from docx import Document


# ============================================================
# Conversión de números a letras
# ============================================================

def numero_a_letras(n) -> str:
    """Convierte un número a su representación en letras (español).
    Ej: 1145682.60 → 'UN MILLÓN CIENTO CUARENTA Y CINCO MIL SEISCIENTOS OCHENTA Y DOS CON 60/100 DÓLARES'
    """
    unidades = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
    especiales = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE"]
    decenas = ["", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
               "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
                "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    def convertir_menor_100(n):
        if n < 10:
            return unidades[n]
        elif 10 <= n < 16:
            return especiales[n - 10]
        elif 16 <= n < 20:
            return "DIECI" + unidades[n - 10]
        elif 20 <= n < 30:
            if n == 20:
                return "VEINTE"
            return "VEINTI" + unidades[n - 20]
        else:
            d = n // 10
            r = n % 10
            if r == 0:
                return decenas[d]
            return decenas[d] + " Y " + unidades[r]

    def convertir_menor_1000(n):
        if n == 100:
            return "CIEN"
        c = n // 100
        r = n % 100
        if c == 0:
            return convertir_menor_100(r)
        if r == 0:
            return centenas[c]
        return centenas[c] + " " + convertir_menor_100(r)

    try:
        n = float(n)
    except (ValueError, TypeError):
        return ""

    entero = int(n)
    decimal = int(round((n - entero) * 100))

    texto = ""

    if entero >= 1000000:
        millones = entero // 1000000
        if millones == 1:
            texto += "UN MILLÓN "
        else:
            texto += convertir_menor_1000(millones) + " MILLONES "
        entero %= 1000000

    if entero >= 1000:
        miles = entero // 1000
        if miles == 1:
            texto += "MIL "
        else:
            texto += convertir_menor_1000(miles) + " MIL "
        entero %= 1000

    if entero > 0:
        texto += convertir_menor_1000(entero)

    texto = texto.strip()

    return f"{texto} CON {decimal:02d}/100 DÓLARES"


def preprocesar_datos_opis(df: pd.DataFrame) -> pd.DataFrame:
    """Si el DataFrame contiene columnas VALOR1 y/o VALOR2, agrega columnas
    con su representación en letras."""
    for col in ("VALOR1", "VALOR2"):
        col_letras = f"{col} LETRAS"
        if col in df.columns:
            df[col_letras] = df[col].apply(numero_a_letras)
    return df


def _formatear_valor1(valor) -> str:
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


def _valor_para_placeholder(key: str, value) -> str:
    """Obtiene el texto final a insertar para cada marcador."""
    if str(key).strip().upper() == "VALOR1":
        return _formatear_valor1(value)
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _replace_placeholder_in_paragraph(paragraph, key: str, value: str) -> None:
    """Reemplaza [key] en un párrafo, manejando marcadores divididos entre runs."""
    placeholder = f"[{key}]"

    while True:
        full_text = "".join(run.text for run in paragraph.runs)
        start = full_text.find(placeholder)
        if start == -1:
            break

        end = start + len(placeholder)

        # Construir mapa de posiciones de cada run
        run_map = []
        pos = 0
        for i, run in enumerate(paragraph.runs):
            length = len(run.text)
            run_map.append((i, pos, pos + length))
            pos += length

        affected_runs = [
            i for i, rstart, rend in run_map
            if not (rend <= start or rstart >= end)
        ]

        if not affected_runs:
            break

        first_run = paragraph.runs[affected_runs[0]]
        style = {
            "bold": first_run.bold,
            "italic": first_run.italic,
            "underline": first_run.underline,
        }

        for idx in affected_runs:
            paragraph.runs[idx].text = ""

        run = paragraph.runs[affected_runs[0]]
        run.text = str(value)
        run.bold = style["bold"]
        run.italic = style["italic"]
        run.underline = style["underline"]


def _process_paragraph(paragraph, variables: dict) -> None:
    """Reemplaza todos los marcadores en un párrafo."""
    for key, value in variables.items():
        _replace_placeholder_in_paragraph(paragraph, key, value)


def _process_tables(tables, variables: dict) -> None:
    """Reemplaza marcadores en todas las tablas del documento."""
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _process_paragraph(p, variables)


def _replace_literal_in_paragraph(paragraph, old_text: str, new_text: str) -> None:
    """Reemplaza solo una frase específica, incluso si está dividida entre runs."""
    if not paragraph.runs:
        return

    while True:
        full_text = "".join(run.text for run in paragraph.runs)
        start = full_text.find(old_text)
        if start == -1:
            break

        end = start + len(old_text)

        run_map = []
        pos = 0
        for i, run in enumerate(paragraph.runs):
            length = len(run.text)
            run_map.append((i, pos, pos + length))
            pos += length

        affected_runs = [
            i for i, rstart, rend in run_map
            if not (rend <= start or rstart >= end)
        ]
        if not affected_runs:
            break

        first_run_index = affected_runs[0]
        first_run_start = next(rstart for i, rstart, _ in run_map if i == first_run_index)
        last_run_index = affected_runs[-1]
        last_run_start = next(rstart for i, rstart, _ in run_map if i == last_run_index)

        prefix = paragraph.runs[first_run_index].text[: start - first_run_start]
        suffix = paragraph.runs[last_run_index].text[end - last_run_start :]

        first_run = paragraph.runs[first_run_index]
        style = {
            "bold": first_run.bold,
            "italic": first_run.italic,
            "underline": first_run.underline,
        }

        for idx in affected_runs:
            paragraph.runs[idx].text = ""

        run = paragraph.runs[first_run_index]
        run.text = prefix + new_text + suffix
        run.bold = style["bold"]
        run.italic = style["italic"]
        run.underline = style["underline"]


def _apply_literal_replacements(doc, replacements: list[tuple[str, str]]) -> None:
    """Aplica reemplazos de texto literal antes del procesamiento de marcadores."""
    if not replacements:
        return

    for old_text, new_text in replacements:
        for paragraph in doc.paragraphs:
            _replace_literal_in_paragraph(paragraph, old_text, new_text)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        _replace_literal_in_paragraph(paragraph, old_text, new_text)

        for section in doc.sections:
            for paragraph in section.header.paragraphs:
                _replace_literal_in_paragraph(paragraph, old_text, new_text)
            for paragraph in section.footer.paragraphs:
                _replace_literal_in_paragraph(paragraph, old_text, new_text)


def generar_documentos_desde_excel(
    df: pd.DataFrame,
    plantilla_path: str,
    output_dir: str,
    obtener_reemplazos_previos=None,
) -> List[str]:
    """
    Genera un documento Word por cada fila del DataFrame, reemplazando
    los marcadores [NOMBRE_COLUMNA] con el valor correspondiente.

    Retorna la lista de rutas de archivos generados.
    """
    archivos = []

    for i, row in df.iterrows():
        doc = Document(plantilla_path)
        variables = {k: _valor_para_placeholder(k, v) for k, v in row.to_dict().items()}

        for p in doc.paragraphs:
            _process_paragraph(p, variables)

        _process_tables(doc.tables, variables)

        # Procesar headers y footers
        for section in doc.sections:
            for p in section.header.paragraphs:
                _process_paragraph(p, variables)
            for p in section.footer.paragraphs:
                _process_paragraph(p, variables)

        # Aplicar reemplazos literales al final para no modificar
        # placeholders del tipo [proceso ] antes de resolverlos.
        if obtener_reemplazos_previos:
            _apply_literal_replacements(doc, obtener_reemplazos_previos(row))

        output_file = os.path.join(output_dir, f"documento_{i + 1}.docx")
        doc.save(output_file)
        archivos.append(output_file)

    return archivos
