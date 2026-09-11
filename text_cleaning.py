"""Utilidades para corregir texto mal codificado (mojibake) en DataFrames.

El caso tipico: un archivo guardado en UTF-8 que fue leido como Latin-1 /
Windows-1252, produciendo cadenas como "JosÃ©" en lugar de "José".
La correccion se hace re-codificando la cadena a bytes y volviendola a
decodificar como UTF-8, nunca con un diccionario manual de reemplazos.
"""

import re
from itertools import groupby

import pandas as pd

# Codificaciones mas comunes en archivos CSV, en orden de intento.
# latin-1 va al final porque nunca falla (acepta cualquier byte).
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

# Maximo de pasadas para texto doblemente codificado.
_MAX_PASSES = 3

# Primer byte de una secuencia UTF-8 (0xC2-0xF4) visto como caracter latin-1.
_LEAD_CHARS = "\u00c2-\u00f4"

# Bytes de continuacion UTF-8 (0x80-0xBF) vistos como latin-1, mas los
# caracteres a los que Windows-1252 mapea el rango 0x80-0x9F (EUR, comillas
# tipograficas, etc.).
_CONT_CHARS = (
    "\u0080-\u00bf"
    "\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc"
    "\u2013\u2014\u2018\u2019\u201a\u201c\u201d\u201e\u2020\u2021"
    "\u2022\u2026\u2030\u2039\u203a\u20ac\u2122"
)

# Senal de corrupcion: caracter "cabecera" seguido de uno de continuacion.
_MOJIBAKE_RE = re.compile("[" + _LEAD_CHARS + "][" + _CONT_CHARS + "]")

# Controles C0/C1 que no deberian aparecer en texto legible (se permiten
# tabulacion y saltos de linea).
_CONTROL_RE = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]"
)

# Caracter de reemplazo: senal de que la decodificacion fallo.
_REPLACEMENT_CHAR = "\ufffd"


def _char_to_bytes(char):
    """Devuelve el byte original del caracter, o None si no es representable."""
    for codec in ("cp1252", "latin-1"):
        try:
            return char.encode(codec)
        except UnicodeEncodeError:
            continue
    return None


def _is_improvement(original, candidate):
    """Valida que la conversion realmente mejore el texto antes de aceptarla."""
    if candidate == original:
        return False
    if _REPLACEMENT_CHAR in candidate or _CONTROL_RE.search(candidate):
        return False
    return len(_MOJIBAKE_RE.findall(candidate)) < len(_MOJIBAKE_RE.findall(original))


def _fix_segment(segment):
    """Aplica la correccion de encoding sobre un tramo representable en bytes."""
    current = segment
    for _ in range(_MAX_PASSES):
        if not _MOJIBAKE_RE.search(current):
            break
        raw = bytearray()
        for char in current:
            raw.extend(_char_to_bytes(char))
        try:
            candidate = raw.decode("utf-8")
        except UnicodeDecodeError:
            break
        if not _is_improvement(current, candidate):
            break
        current = candidate
    return current


def clean_encoding(text):
    """Corrige texto mal decodificado; devuelve el valor intacto si no aplica.

    Solo actua sobre cadenas que muestran senales de corrupcion y unicamente
    si la re-decodificacion produce un resultado valido y mejor. Numeros,
    fechas, None y NaN se devuelven tal cual.
    """
    if not isinstance(text, str) or not text:
        return text
    if not _MOJIBAKE_RE.search(text):
        return text

    # Los caracteres no representables en cp1252/latin-1 (emojis ya correctos,
    # CJK, etc.) actuan como separadores: cada tramo se corrige por su cuenta.
    partes = []
    for representable, grupo in groupby(text, key=lambda c: _char_to_bytes(c) is not None):
        tramo = "".join(grupo)
        partes.append(_fix_segment(tramo) if representable else tramo)
    return "".join(partes)


def clean_dataframe_encoding(df):
    """Aplica clean_encoding a las columnas de texto y a los encabezados.

    Devuelve (df_limpio, resumen) donde resumen incluye columnas analizadas,
    celdas corregidas y encabezados corregidos.
    """
    cleaned = df.copy()

    text_columns = [
        col for col in cleaned.columns
        if pd.api.types.is_object_dtype(cleaned[col])
        or pd.api.types.is_string_dtype(cleaned[col])
    ]

    fixed_cells = 0
    for col in text_columns:
        original = cleaned[col]
        updated = original.map(clean_encoding)
        fixed_cells += sum(
            1 for antes, despues in zip(original, updated)
            if isinstance(antes, str) and antes != despues
        )
        cleaned[col] = updated

    new_columns = [
        clean_encoding(col) if isinstance(col, str) else col for col in cleaned.columns
    ]
    fixed_headers = sum(
        1 for antes, despues in zip(cleaned.columns, new_columns) if antes != despues
    )
    cleaned.columns = new_columns

    return cleaned, {
        "columnas_analizadas": len(text_columns),
        "celdas_corregidas": fixed_cells,
        "encabezados_corregidos": fixed_headers,
    }


def read_csv_with_encoding(uploaded_file):
    """Lee un CSV probando las codificaciones mas comunes.

    Devuelve (DataFrame, codificacion usada). Mantiene la deteccion automatica
    de separador que ya usaba la aplicacion.
    """
    last_error = None
    for encoding in CSV_ENCODINGS:
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding=encoding)
            return df, encoding
        except UnicodeDecodeError as error:
            last_error = error
    raise last_error
