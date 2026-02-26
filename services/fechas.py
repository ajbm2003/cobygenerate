"""
fechas.py — Procesamiento de CSV de fechas de correo (CPanel)
"""

import pandas as pd

# Mapeo de abreviaciones de meses: español → inglés (para parseo)
MESES_ES_EN = {
    "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
    "sept": "Sep", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
}

# Mapeo de abreviaciones → nombre completo en español
MESES_COMPLETOS = {
    "ene": "enero", "feb": "febrero", "mar": "marzo", "abr": "abril",
    "may": "mayo", "jun": "junio", "jul": "julio", "ago": "agosto",
    "sept": "septiembre", "sep": "septiembre", "oct": "octubre",
    "nov": "noviembre", "dic": "diciembre",
}

REMITENTE_DEFAULT = "cobranzaypatrocinio@cobypat.com"


def procesar_csv_fechas(csv_path: str, remitente: str = REMITENTE_DEFAULT) -> dict:
    """
    Lee el CSV de CPanel, filtra por remitente y las 2 fechas más recientes.

    Returns:
        dict: email_destinatario → [lista de fechas]
    """
    df_csv = pd.read_csv(csv_path)

    # Parsear fechas (meses en español → inglés)
    fecha_en = df_csv["Fecha Envío CPanel"].copy()
    for es, en in MESES_ES_EN.items():
        fecha_en = fecha_en.str.replace(f" {es} ", f" {en} ", case=False, regex=False)
    df_csv["_fecha_dt"] = pd.to_datetime(fecha_en, format="%d %b %Y %H:%M:%S")

    # Filtrar por remitente
    df_filtrado = df_csv[df_csv["Remitente"] == remitente].copy()

    # Tomar las 2 fechas (días) más recientes
    if not df_filtrado.empty:
        fechas_unicas = sorted(df_filtrado["_fecha_dt"].dt.date.unique(), reverse=True)[:2]
        df_filtrado = df_filtrado[df_filtrado["_fecha_dt"].dt.date.isin(fechas_unicas)]

    # Diccionario: Destinatario → [fechas]
    return (
        df_filtrado[df_filtrado["Destinatario"] != remitente]
        .groupby("Destinatario")["Fecha Envío CPanel"]
        .apply(list)
        .to_dict()
    )


def expandir_mes(texto_fecha: str) -> str:
    """
    Reemplaza abreviación del mes por nombre completo en español.
    Ej: '11 feb 2026 10:30:45' → '11 de febrero de 2026 10:30:45'
    """
    texto = str(texto_fecha).strip()
    for abrev, completo in MESES_COMPLETOS.items():
        if f" {abrev} " in texto.lower():
            partes = texto.split()
            for i, p in enumerate(partes):
                if p.lower() == abrev:
                    partes[i] = f"de {completo} de"
                    break
            return " ".join(partes)
    return texto


def formatear_fechas_notificacion(fecha_notificacion: str) -> str:
    """
    Divide FECHA_NOTIFICACION por ',' y devuelve texto con las 2 últimas
    fechas formateadas con meses en nombre completo.
    Solo toma las dos últimas fechas encontradas, sin importar cuántas haya.
    """
    if not fecha_notificacion or pd.isna(fecha_notificacion) or str(fecha_notificacion).strip() == "":
        return ""

    partes = [expandir_mes(f.strip()) for f in str(fecha_notificacion).split(",") if f.strip()]

    # Eliminar duplicados conservando el orden de aparición
    vistos = set()
    unicas = []
    for p in partes:
        clave = p.strip().lower()
        if clave not in vistos:
            vistos.add(clave)
            unicas.append(p)
    partes = unicas

    # Tomar solo las 2 últimas fechas diferentes
    partes = partes[-2:] if len(partes) > 2 else partes

    if len(partes) == 0:
        return ""
    if len(partes) == 1:
        return partes[0]
    return " y ".join(partes)
