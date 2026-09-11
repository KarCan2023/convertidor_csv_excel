"""Pruebas de la limpieza de caracteres.

Ejecutar con: python test_text_cleaning.py  (o con pytest, si esta instalado)
"""

import io

import pandas as pd

from text_cleaning import (
    clean_dataframe_encoding,
    clean_encoding,
    read_csv_with_encoding,
)

# Casos danados -> esperado
CORRUPTOS = [
    ("Â¡Quiero redimir mi cupÃ³n del raspa y gana!",
     "¡Quiero redimir mi cupón del raspa y gana!"),
    ("JosÃ©", "José"),
    ("niÃ±o", "niño"),
    ("informaciÃ³n", "información"),
    ("Â¿CÃ³mo estÃ¡s?", "¿Cómo estás?"),
    ("comillas â€œrarasâ€", "comillas “raras”"),
    ("noâ€™s", "no’s"),
    ("feliz ðŸ˜Š", "feliz \U0001f60a"),
]

# Texto ya correcto que no debe cambiar
CORRECTOS = [
    "¡Hola!", "José", "niño", "información",
    "Bogotá", "Medellín", "¿Cómo estás?",
    "Señor Ángel", "café 100% — €10", "2024-01-15",
    "1.234,56", "", "Año 2025 ©", "¿Qué tal? \U0001f60a",
]


def test_corrige_texto_danado():
    for danado, esperado in CORRUPTOS:
        assert clean_encoding(danado) == esperado, (danado, clean_encoding(danado))


def test_no_toca_texto_correcto():
    for texto in CORRECTOS:
        assert clean_encoding(texto) == texto, texto


def test_valores_no_texto():
    import math
    assert clean_encoding(None) is None
    assert clean_encoding(123) == 123
    assert clean_encoding(3.14) == 3.14
    assert math.isnan(clean_encoding(float("nan")))
    fecha = pd.Timestamp("2024-01-15")
    assert clean_encoding(fecha) is fecha


def test_doble_codificacion():
    original = "información"
    doble = original.encode("utf-8").decode("latin-1").encode("utf-8").decode("latin-1")
    assert clean_encoding(doble) == original


def test_dataframe_solo_columnas_de_texto():
    df = pd.DataFrame({
        "nombre": ["JosÃ©", "Bogotá", None],
        "cantidad": [1, 2, 3],
        "precio": [10.5, 20.25, 30.0],
        "fecha": pd.to_datetime(["2024-01-15", "2024-02-20", "2024-03-25"]),
        "Â¿CÃ³mo estÃ¡s?": ["si", "no", "tal vez"],
    })

    limpio, resumen = clean_dataframe_encoding(df)

    assert limpio["nombre"].tolist()[:2] == ["José", "Bogotá"]
    assert limpio["nombre"].isna().iloc[2]
    assert limpio["cantidad"].tolist() == [1, 2, 3]
    assert limpio["precio"].tolist() == [10.5, 20.25, 30.0]
    assert limpio["fecha"].equals(df["fecha"])
    assert "¿Cómo estás?" in limpio.columns
    assert resumen["celdas_corregidas"] == 1
    assert resumen["encabezados_corregidos"] == 1
    assert resumen["columnas_analizadas"] == 2
    # El DataFrame original no se modifica
    assert df["nombre"].iloc[0] == "JosÃ©"


def test_lectura_csv_multiples_codificaciones():
    contenido = "nombre,ciudad\nJosé,Bogotá\n"
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        buffer = io.BytesIO(contenido.encode(encoding))
        df, usada = read_csv_with_encoding(buffer)
        assert df["nombre"].iloc[0] == "José", (encoding, usada)
        assert list(df.columns) == ["nombre", "ciudad"], (encoding, usada)


def test_csv_con_mojibake_se_limpia():
    # El sistema de origen ya guardo el texto danado y lo exporto en UTF-8.
    danado = "José".encode("utf-8").decode("latin-1")
    contenido = f"nombre,ciudad\n{danado},Bogotá\n"
    buffer = io.BytesIO(contenido.encode("utf-8"))

    df, encoding = read_csv_with_encoding(buffer)
    assert encoding == "utf-8-sig"
    assert df["nombre"].iloc[0] == danado  # sin limpiar sigue danado

    limpio, resumen = clean_dataframe_encoding(df)
    assert limpio["nombre"].iloc[0] == "José"
    assert limpio["ciudad"].iloc[0] == "Bogotá"
    assert resumen["celdas_corregidas"] == 1


if __name__ == "__main__":
    pruebas = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"\n{len(pruebas)} pruebas pasaron")
