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
    Divide FECHA_NOTIFICACION por ',', agrupa por día, toma los 2 días
    más recientes y de cada día escoge solo la última hora.
    Devuelve texto con meses en nombre completo.
    """
    if not fecha_notificacion or pd.isna(fecha_notificacion) or str(fecha_notificacion).strip() == "":
        return ""

    raw_partes = [f.strip() for f in str(fecha_notificacion).split(",") if f.strip()]

    if not raw_partes:
        return ""

    # Parsear cada fecha a datetime para poder agrupar por día y ordenar por hora
    fechas_dt = []
    for raw in raw_partes:
        texto = raw
        for es, en in MESES_ES_EN.items():
            texto = texto.replace(f" {es} ", f" {en} ").replace(f" {es.title()} ", f" {en} ")
        try:
            dt = pd.to_datetime(texto, format="%d %b %Y %H:%M:%S")
            fechas_dt.append((dt, raw))
        except Exception:
            # Si no se puede parsear, mantener el texto original
            fechas_dt.append((pd.NaT, raw))

    # Filtrar las que se pudieron parsear
    validas = [(dt, raw) for dt, raw in fechas_dt if pd.notna(dt)]
    no_validas = [raw for dt, raw in fechas_dt if pd.isna(dt)]

    if not validas:
        # Si ninguna se pudo parsear, devolver las últimas 2 como texto
        partes = [expandir_mes(p) for p in raw_partes[-2:]]
        return " y ".join(partes) if len(partes) > 1 else partes[0]

    # Agrupar por día y quedarse con la última hora de cada día
    from collections import defaultdict
    por_dia = defaultdict(list)
    for dt, raw in validas:
        por_dia[dt.date()].append((dt, raw))

    # De cada día, tomar solo la entrada con la hora más tardía
    mejores = []
    for dia in sorted(por_dia.keys()):
        mejor = max(por_dia[dia], key=lambda x: x[0])
        mejores.append(mejor)

    # Tomar solo los 2 días más recientes
    mejores = mejores[-2:]

    # Expandir meses a nombre completo
    partes = [expandir_mes(raw) for _, raw in mejores]

    if len(partes) == 0:
        return ""
    if len(partes) == 1:
        return partes[0]
    return " y ".join(partes)
