"""
cruces.py — Cruces de datos entre dos archivos Excel/CSV por el campo JUICIO
"""

import pandas as pd


def cruzar_archivos(df1: pd.DataFrame, df2: pd.DataFrame) -> dict:
    """
    Cruza dos DataFrames por el campo JUICIO y devuelve:
    - Las coincidencias encontradas
    - Las columnas disponibles de ambos DataFrames
    
    Args:
        df1: Primer DataFrame
        df2: Segundo DataFrame
    
    Returns:
        dict con claves:
        - 'coincidencias': DataFrame con los registros que coinciden en JUICIO
        - 'columnas_df1': Lista de columnas del primer archivo
        - 'columnas_df2': Lista de columnas del segundo archivo
        - 'total_coincidencias': Número de registros que coinciden
    """
    
    if "JUICIO" not in df1.columns or "JUICIO" not in df2.columns:
        raise ValueError("Ambos archivos deben tener la columna 'JUICIO'")
    
    # Normalizar columnas JUICIO (eliminar espacios, convertir a string)
    df1["JUICIO_NORMALIZADO"] = df1["JUICIO"].astype(str).str.strip().str.upper()
    df2["JUICIO_NORMALIZADO"] = df2["JUICIO"].astype(str).str.strip().str.upper()
    
    # Encontrar coincidencias
    juicios_comunes = set(df1["JUICIO_NORMALIZADO"]) & set(df2["JUICIO_NORMALIZADO"])
    
    df1_coincidencias = df1[df1["JUICIO_NORMALIZADO"].isin(juicios_comunes)].copy()
    df2_coincidencias = df2[df2["JUICIO_NORMALIZADO"].isin(juicios_comunes)].copy()
    
    # Cruzar por JUICIO (inner join)
    coincidencias = pd.merge(
        df1_coincidencias,
        df2_coincidencias,
        left_on="JUICIO_NORMALIZADO",
        right_on="JUICIO_NORMALIZADO",
        how="inner",
        suffixes=("_archivo1", "_archivo2")
    )
    
    # Remover la columna temporal de normalización si está en coincidencias
    coincidencias = coincidencias.drop(columns=["JUICIO_NORMALIZADO"], errors="ignore")
    
    # Obtener columnas del resultado
    columnas_resultado = list(coincidencias.columns)
    
    return {
        "coincidencias": coincidencias,
        "columnas": columnas_resultado,
        "total_coincidencias": len(coincidencias),
    }


def filtrar_columnas_resultado(df: pd.DataFrame, columnas_seleccionadas: list) -> pd.DataFrame:
    """Filtra el DataFrame para mostrar solo las columnas solicitadas."""
    # Validar que las columnas existan
    columnas_validas = [col for col in columnas_seleccionadas if col in df.columns]
    
    if not columnas_validas:
        raise ValueError("Ninguna de las columnas seleccionadas existe en los datos")
    
    return df[columnas_validas]
