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

    # El período detectado en gestiones filtra también las liquidaciones
    mes_num = gestiones.get("_mes_num")
    anio    = gestiones.get("_anio")
    liquidaciones = _procesar_liquidaciones(liquidaciones_path, mes_num, anio)

    # Quitar las claves internas antes de devolver
    gestiones.pop("_mes_num", None)
    gestiones.pop("_anio", None)

    return {
        "periodo": gestiones["periodo"],
        "gestiones": gestiones,
        "liquidaciones": liquidaciones,
    }


# ── Gestiones ─────────────────────────────────────────────────

def _procesar_gestiones(path: str) -> dict:
    df = pd.read_excel(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]

    # Parsear fecha y detectar período dominante
    df["_fecha_dt"] = pd.to_datetime(df.get("Fecha", pd.Series(dtype=str)), errors="coerce")
    fechas_validas = df["_fecha_dt"].dropna()

    if len(fechas_validas) > 0:
        mes_num = int(fechas_validas.dt.month.mode()[0])
        anio    = int(fechas_validas.dt.year.mode()[0])
        periodo = f"{MESES_ES.get(mes_num, '')} {anio}"

        # Filtrar solo filas del mes/año del período
        mask = (df["_fecha_dt"].dt.month == mes_num) & (df["_fecha_dt"].dt.year == anio)
        df = df[mask].copy()
    else:
        mes_num = None
        anio    = None
        periodo = ""

    # Sub-Respuesta → tabla + gráfica de pie
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
        "_mes_num": mes_num,
        "_anio": anio,
        "titulo": f"GESTIÓN EXTRAJUDICIAL {periodo}",
        "tabla": tabla,
        "total": total,
        "labels": [r["etiqueta"] for r in tabla],
        "values": [r["cantidad"] for r in tabla],
        "resumen": _procesar_resumen_gestiones(df, periodo),
    }


def _procesar_resumen_gestiones(df: pd.DataFrame, periodo: str) -> dict:
    """Tablas de resumen: por agente y pivot Módulo × Sub-Respuesta."""
    if df.empty:
        return {"titulo": f"GESTIONES EXTRAJUDICIAL {periodo}", "tabla_agente": [], "total": 0, "grupos": []}

    total = len(df)

    # ── Tabla 1: por agente ──
    col_agente = _detectar_columna(df, ["Agente", "AGENTE", "agente"])
    por_agente = df[col_agente].value_counts()
    tabla_agente = [
        {
            "agente": str(label),
            "gestiones": int(count),
            "porcentaje": round(float(count) / total * 100, 2),
        }
        for label, count in por_agente.items()
    ]

    # ── Tabla 2: pivot Nombre Modulo × Sub-Respuesta ──
    col_modulo = _detectar_columna(df, ["Nombre Modulo", "Nombre_Modulo", "NOMBRE MODULO", "Canal de Gestión"])
    col_sub    = _detectar_columna(df, ["Sub-Respuesta", "sub-respuesta", "Respuesta"])

    df = df.copy()
    df["_modulo"] = df[col_modulo].replace("", "SIN MÓDULO").fillna("SIN MÓDULO")
    df["_sub"]    = df[col_sub].replace("", "SIN DATO").fillna("SIN DATO")

    pivot = df.groupby(["_modulo", "_sub"]).size().reset_index(name="count")

    grupos = []
    for modulo, grp in pivot.groupby("_modulo"):
        filas = [
            {"sub": str(row["_sub"]), "count": int(row["count"])}
            for _, row in grp.sort_values("count", ascending=False).iterrows()
        ]
        subtotal = sum(f["count"] for f in filas)
        grupos.append({"modulo": str(modulo), "subtotal": subtotal, "filas": filas})

    grupos.sort(key=lambda g: g["subtotal"], reverse=True)

    return {
        "titulo": f"GESTIONES EXTRAJUDICIAL {periodo}",
        "tabla_agente": tabla_agente,
        "total": total,
        "grupos": grupos,
    }


# ── Liquidaciones ─────────────────────────────────────────────

def _procesar_liquidaciones(path: str, mes_num: int | None, anio: int | None) -> dict:
    df = pd.read_excel(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]

    col_fecha      = _detectar_columna(df, ["FECHA LIQUIDACION", "Fecha Liquidacion", "FECHA"])
    col_honorarios = _detectar_columna(df, ["HONORARIOS", "Honorarios", "COMISION", "COMISIÓN"])
    col_cedula     = _detectar_columna(df, ["CEDULA/RUC", "CEDULA", "RUC", "Identificacion"])

    df["_fecha_dt"]   = pd.to_datetime(df[col_fecha], errors="coerce")
    df["_honorarios"] = pd.to_numeric(df[col_honorarios], errors="coerce").fillna(0)

    # Filtrar por el mismo mes/año del período de gestiones
    if mes_num and anio:
        mask = (df["_fecha_dt"].dt.month == mes_num) & (df["_fecha_dt"].dt.year == anio)
        df = df[mask].copy()

    df["_fecha_str"] = df["_fecha_dt"].dt.strftime("%-d/%-m/%Y")

    if df.empty:
        return {
            "titulo": "PAGOS REALIZADOS",
            "tabla": [],
            "total_comision": 0.0,
            "total_clientes": 0,
            "fechas": [],
            "comisiones": [],
            "num_clientes": [],
            "sin_datos": True,
        }

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


# ── Correos ───────────────────────────────────────────────────

def procesar_correos(path: str, fecha_inicio: str | None, fecha_fin: str | None) -> dict:
    """
    Lee el CSV de gestiones por correo electrónico (CPanel/Cobypat),
    filtra por rango de fechas y devuelve métricas de entrega y lectura.
    """
    for enc in ("latin-1", "cp1252", "utf-8"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("No se pudo leer el CSV de correos. Verifique el archivo.")

    # Renombrar columnas por posición (encoding de nombres inconsistente)
    nombres = ["Mail Cliente", "Message-ID", "IP de envio", "Nombre Cliente",
               "RUC", "PIC", "Adeudado", "Resultado Entrega", "Enviado", "Entregado", "Leido"]
    df.columns = nombres[:len(df.columns)]

    df["_enviado_dt"] = pd.to_datetime(df["Enviado"], errors="coerce")

    if fecha_inicio:
        df = df[df["_enviado_dt"] >= pd.Timestamp(fecha_inicio)]
    if fecha_fin:
        df = df[df["_enviado_dt"] <= pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

    if df.empty:
        raise ValueError("No hay registros en el rango de fechas seleccionado.")

    total       = len(df)
    entregados  = int((df["Resultado Entrega"].str.strip() == "Aceptado").sum())
    no_entregados = total - entregados
    leidos      = int(df["Leido"].replace("", None).notna().sum())
    no_leidos   = total - leidos

    fechas_validas = df["_enviado_dt"].dropna()
    f_min = fechas_validas.min().strftime("%-d/%-m/%Y") if len(fechas_validas) else "-"
    f_max = fechas_validas.max().strftime("%-d/%-m/%Y") if len(fechas_validas) else "-"

    tabla = [
        {"concepto": "Total enviados",  "cantidad": total,          "porcentaje": 100.0},
        {"concepto": "Entregados",       "cantidad": entregados,     "porcentaje": round(entregados / total * 100, 2)},
        {"concepto": "No entregados",    "cantidad": no_entregados,  "porcentaje": round(no_entregados / total * 100, 2)},
        {"concepto": "Leídos",           "cantidad": leidos,         "porcentaje": round(leidos / total * 100, 2)},
        {"concepto": "No leídos",        "cantidad": no_leidos,      "porcentaje": round(no_leidos / total * 100, 2)},
    ]

    return {
        "titulo": "GESTIONES POR CORREO ELECTRÓNICO",
        "periodo_correos": f"{f_min} al {f_max}",
        "tabla": tabla,
        "total": total,
        "labels": ["Entregados", "No entregados", "Leídos", "No leídos"],
        "values": [entregados, no_entregados, leidos, no_leidos],
    }


# ── Utilidades ────────────────────────────────────────────────

def _detectar_columna(df: pd.DataFrame, candidatos: list) -> str:
    for nombre in candidatos:
        if nombre in df.columns:
            return nombre
    raise ValueError(
        f"No se encontró ninguna de las columnas esperadas: {candidatos}. "
        f"Columnas disponibles: {list(df.columns)}"
    )
