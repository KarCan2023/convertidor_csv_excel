import streamlit as st
import pandas as pd
import io

from text_cleaning import clean_dataframe_encoding, read_csv_with_encoding

st.set_page_config(page_title="CSV a Excel", page_icon="📄")

st.title("Conversor de CSV a Excel 📄➡️📊")

uploaded_file = st.file_uploader("Sube tu archivo CSV", type="csv")

if uploaded_file:
    try:
        # Intentar leer CSV con separador y codificación automáticos
        df, encoding_usado = read_csv_with_encoding(uploaded_file)
        st.success(f"CSV leído correctamente (codificación: {encoding_usado})")

        # Limpieza de caracteres
        st.subheader("Limpieza de caracteres")
        limpiar = st.checkbox(
            "Limpiar caracteres dañados",
            value=False,
            help="Corrige texto UTF-8 mal interpretado como Latin-1/Windows-1252 "
                 "(por ejemplo: JosÃ© ➡️ José).",
        )

        if limpiar:
            df, resumen = clean_dataframe_encoding(df)
            st.info(
                "🧹 Limpieza completada\n\n"
                f"- Columnas analizadas: {resumen['columnas_analizadas']}\n"
                f"- Celdas corregidas: {resumen['celdas_corregidas']}\n"
                f"- Encabezados corregidos: {resumen['encabezados_corregidos']}"
            )

        # Vista previa
        st.caption(
            "Vista previa (con limpieza aplicada)" if limpiar
            else "Vista previa (sin limpieza)"
        )
        st.dataframe(df.head(10))

        # Convertir a Excel
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        # Botón para descargar
        st.download_button(
            label="📥 Descargar Excel",
            data=output,
            file_name=uploaded_file.name.replace(".csv", ".xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Error al procesar el CSV: {e}")



st.markdown("---")


# 🟢 Módulo Excel a CSV
st.title("Conversor de Excel a CSV 📊➡️📄")
uploaded_excel = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"], key="excel")

if uploaded_excel:
    try:
        df_excel = pd.read_excel(uploaded_excel, engine='openpyxl')
        st.success("Excel leído correctamente")

        output_csv = io.BytesIO()
        output_csv.write(df_excel.to_csv(index=False).encode("utf-8"))
        output_csv.seek(0)

        st.download_button(
            label="📥 Descargar CSV",
            data=output_csv,
            file_name=uploaded_excel.name.replace(".xlsx", ".csv").replace(".xls", ".csv"),
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error al procesar el Excel: {e}")
