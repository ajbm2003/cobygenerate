"""
preprocesamiento.py — Preprocesamiento de datos antes de generar documentos.
Incluye conversión de valores numéricos a letras.
"""

import pandas as pd


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


def obtener_reemplazos_sexo(sexo: str) -> list[tuple[str, str]]:
    """Devuelve reemplazos de texto según el sexo de la fila.

    Si SEXO es F, convierte referencias masculinas a femeninas.
    Si es M o no viene valor, no aplica cambios.
    """
    sexo_normalizado = str(sexo).strip().upper()
    if sexo_normalizado not in {"F", "FEMENINO"}:
        return []

    return [
        ("el deudor", "la deudora"),
        ("El deudor", "La deudora"),
        ("EL DEUDOR", "LA DEUDORA"),
        ("el coactivado", "la coactivada"),
        ("El coactivado", "La coactivada"),
        ("EL COACTIVADO", "LA COACTIVADA"),
    ]
