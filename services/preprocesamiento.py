"""
preprocesamiento.py — Preprocesamiento de datos antes de generar documentos.
Incluye conversión de valores numéricos a letras.
"""

import re
from datetime import datetime

import pandas as pd


_PATRON_FECHA_LARGA_ES = re.compile(
    r"^\s*(\d{1,2})\s+de\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ]+)\s+de\s+(\d{4})\s*$",
    re.IGNORECASE,
)

_MESES_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_CORTE_JULIO_2018 = datetime(2018, 7, 1)


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

    return f"{texto} CON {decimal:02d}/100 DÓLARES DE LOS ESTADOS UNIDOS DE AMÉRICA"


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
        ("coactivado", "coactivada"),
        ("Coactivado", "Coactivada"),
        ("COACTIVADO", "COACTIVADA"),
        ("Deudor", "Deudora"),
    ]


def _parsear_fecha_larga_es(texto_fecha: str) -> datetime | None:
    """Parsea fechas tipo '21 de diciembre de 2020' y retorna datetime."""
    texto = str(texto_fecha).strip()
    if not texto:
        return None

    match = _PATRON_FECHA_LARGA_ES.match(texto)
    if not match:
        return None

    dia = int(match.group(1))
    mes_texto = match.group(2).lower()
    anio = int(match.group(3))
    mes = _MESES_ES.get(mes_texto)
    if not mes:
        return None

    try:
        return datetime(anio, mes, dia)
    except ValueError:
        return None


def obtener_reemplazos_auto_de_pago(auto_de_pago: str) -> list[tuple[str, str]]:
    """Devuelve reemplazos para plantillas según fecha de AUTO DE PAGO.

    Si la fecha es anterior a julio de 2018, aplica:
    - Proceso/proceso/PROCESO -> Juicio/juicio/JUICIO
    - JEFE/Jefe/jefe -> JUEZ/Juez/juez
    - JEFATURA/Jefatura/jefatura -> JUZGADO/Juzgado/juzgado

    Si no se puede parsear o es julio 2018 en adelante, no aplica cambios.
    """
    fecha_auto = _parsear_fecha_larga_es(auto_de_pago)
    if not fecha_auto or fecha_auto >= _CORTE_JULIO_2018:
        return []

    reemplazos_base = [
        ("Proceso", "Juicio"),
        ("proceso", "juicio"),
        ("PROCESO", "JUICIO"),
        ("JEFE", "JUEZ NACIONAL"),
        ("Jefe", "Juez"),
        ("jefe", "juez"),
    ]

    # Mantener JEFATURA al final por requerimiento de negocio.
    reemplazos_finales = [
        ("JEFATURA", "JUZGADO"),
        ("Jefatura", "Juzgado"),
        ("jefatura", "juzgado"),
    ]

    return reemplazos_base + reemplazos_finales
