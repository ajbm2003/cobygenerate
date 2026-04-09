"""
dashboard.py — Procesamiento de informes extrajudiciales
=========================================================
Genera los datos para el informe mensual a partir de:
  - Excel de gestiones diarias CRM
  - Excel de liquidaciones / pagos realizados
"""

import pandas as pd

MESES_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def procesar_informe_extrajudicial(gestiones_path: str, liquidaciones_path: str) -> dict:
    gestiones = _procesar_gestiones(gestiones_path)
    liquidaciones = _procesar_liquidaciones(liquidaciones_path)
    return {
        "periodo": gestiones["periodo"],
        "gestiones": gestiones,
        "liquidaciones": liquidaciones,
    }


def _procesar_gestiones(path: str) -> dict:
    df = pd.read_excel(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]

    # Determinar mes/año del período
    fechas = pd.to_datetime(df.get("Fecha", pd.Series(dtype=str)), errors="coerce").dropna()
    if len(fechas) > 0:
        mes_num = int(fechas.dt.month.mode()[0])
        anio = int(fechas.dt.year.mode()[0])
        periodo = f"{MESES_ES.get(mes_num, '')} {anio}"
    else:
        periodo = ""

    # Columna de agrupación: Sub-Respuesta
    col = _detectar_columna(df, ["Sub-Respuesta", "sub-respuesta", "Respuesta", "respuesta"])
    serie = df[col].replace("", "SIN DATO").fillna("SIN DATO")
    conteos = serie.value_counts()
    total = int(conteos.sum())

    tabla = [
        {
            "etiqueta": str(label),
            "cantidad": int(count),
            "porcentaje": round(float(count) / total * 100, 2),
        }
        for label, count in conteos.items()
    ]

    return {
        "periodo": periodo,
        "titulo": f"GESTIÓN EXTRAJUDICIAL {periodo}",
        "tabla": tabla,
        "total": total,
        "labels": [r["etiqueta"] for r in tabla],
        "values": [r["cantidad"] for r in tabla],
    }


def _procesar_liquidaciones(path: str) -> dict:
    df = pd.read_excel(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]

    col_fecha = _detectar_columna(df, ["FECHA LIQUIDACION", "Fecha Liquidacion", "FECHA"])
    col_honorarios = _detectar_columna(df, ["HONORARIOS", "Honorarios", "COMISION", "COMISIÓN"])
    col_cedula = _detectar_columna(df, ["CEDULA/RUC", "CEDULA", "RUC", "Identificacion"])

    df["_fecha_dt"] = pd.to_datetime(df[col_fecha], errors="coerce")
    df["_honorarios"] = pd.to_numeric(df[col_honorarios], errors="coerce").fillna(0)

    # Formato de fecha: día/mes/año sin ceros a la izquierda
    df["_fecha_str"] = df["_fecha_dt"].dt.strftime("%-d/%-m/%Y")

    df_sorted = df.sort_values("_fecha_dt")
    grouped = (
        df_sorted
        .groupby("_fecha_str", sort=False)
        .agg(comision=("_honorarios", "sum"), num_clientes=(col_cedula, "count"))
        .reset_index()
    )
    grouped["comision"] = grouped["comision"].round(2)

    total_comision = round(float(grouped["comision"].sum()), 2)
    total_clientes = int(grouped["num_clientes"].sum())

    tabla = [
        {
            "fecha": row["_fecha_str"],
            "comision": float(row["comision"]),
            "num_clientes": int(row["num_clientes"]),
        }
        for _, row in grouped.iterrows()
    ]

    return {
        "titulo": "PAGOS REALIZADOS",
        "tabla": tabla,
        "total_comision": total_comision,
        "total_clientes": total_clientes,
        "fechas": [r["fecha"] for r in tabla],
        "comisiones": [r["comision"] for r in tabla],
        "num_clientes": [r["num_clientes"] for r in tabla],
    }


def procesar_correos(path: str, fecha_inicio: str | None, fecha_fin: str | None) -> dict:
    """
    Lee el CSV de gestiones por correo electrónico (CPanel/Cobypat),
    filtra por rango de fechas y devuelve métricas de entrega y lectura.
    """
    # El CSV tiene BOM doble y encoding mixto; se normaliza por posición de columna
    for enc in ("latin-1", "cp1252", "utf-8"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("No se pudo leer el CSV de correos. Verifique el archivo.")

    # Renombrar columnas por posición (el archivo tiene codificación de nombres inconsistente)
    nombres = ["Mail Cliente", "Message-ID", "IP de envio", "Nombre Cliente",
               "RUC", "PIC", "Adeudado", "Resultado Entrega", "Enviado", "Entregado", "Leido"]
    if len(df.columns) == len(nombres):
        df.columns = nombres
    else:
        # Fallback: renombrar solo las que existen por posición
        df.columns = nombres[:len(df.columns)]

    # Parsear fecha de envío
    df["_enviado_dt"] = pd.to_datetime(df["Enviado"], errors="coerce")

    # Filtrar por rango de fechas
    if fecha_inicio:
        df = df[df["_enviado_dt"] >= pd.Timestamp(fecha_inicio)]
    if fecha_fin:
        df = df[df["_enviado_dt"] <= pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

    if df.empty:
        raise ValueError("No hay registros en el rango de fechas seleccionado.")

    total = len(df)

    entregados = int((df["Resultado Entrega"].str.strip() == "Aceptado").sum())
    no_entregados = total - entregados

    leidos = int(df["Leido"].replace("", None).notna().sum())
    no_leidos = total - leidos

    # Etiquetas de período
    fechas_validas = df["_enviado_dt"].dropna()
    f_min = fechas_validas.min().strftime("%-d/%-m/%Y") if len(fechas_validas) else "-"
    f_max = fechas_validas.max().strftime("%-d/%-m/%Y") if len(fechas_validas) else "-"

    tabla = [
        {"concepto": "Total enviados",    "cantidad": total,         "porcentaje": 100.0},
        {"concepto": "Entregados",         "cantidad": entregados,    "porcentaje": round(entregados / total * 100, 2)},
        {"concepto": "No entregados",      "cantidad": no_entregados, "porcentaje": round(no_entregados / total * 100, 2)},
        {"concepto": "Leídos",             "cantidad": leidos,        "porcentaje": round(leidos / total * 100, 2)},
        {"concepto": "No leídos",          "cantidad": no_leidos,     "porcentaje": round(no_leidos / total * 100, 2)},
    ]

    return {
        "titulo": "GESTIONES POR CORREO ELECTRÓNICO",
        "periodo_correos": f"{f_min} al {f_max}",
        "tabla": tabla,
        "total": total,
        # Para la gráfica de dona
        "labels": ["Entregados", "No entregados", "Leídos", "No leídos"],
        "values": [entregados, no_entregados, leidos, no_leidos],
    }


def _detectar_columna(df: pd.DataFrame, candidatos: list) -> str:
    for nombre in candidatos:
        if nombre in df.columns:
            return nombre
    raise ValueError(
        f"No se encontró ninguna de las columnas esperadas: {candidatos}. "
        f"Columnas disponibles: {list(df.columns)}"
    )
