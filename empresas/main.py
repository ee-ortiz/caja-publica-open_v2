import os
import streamlit as st
from utils import query_athena
from empresas.empresas_utils import draw_empresas
from empresas.grafo import get_graph
import difflib

def main_empresas(tipo_contrato, year_slider):
    """
    Lógica principal cuando se selecciona 'Por empresa'.
    Permite buscar por NIT o por nombre de empresa.
    - Si se busca por nombre, se utiliza búsqueda fuzzy para escoger la mejor coincidencia.
    """
    os.environ['RADIO'] = "Por empresa"

    # Permite seleccionar el tipo de búsqueda
    busqueda_tipo = st.radio("Buscar por", options=["NIT", "Nombre"])

    if busqueda_tipo == "NIT":
        entrada = st.text_input("Ingrese un NIT", value="")
        # Limpieza del input
        entrada = entrada.replace(".", "").replace(",", "").replace("-", "")
        entrada = entrada[:9]  # Se conservan los primeros 9 dígitos
    else:
        entrada = st.text_input("Ingrese el nombre de la empresa", value="").strip()

    st.write(f"Búsqueda por {busqueda_tipo}: {entrada}")

    # Si no se ingresa valor, detenemos la ejecución
    if entrada == "":
        st.stop()

    # Se arma la consulta según el modo de búsqueda
    if busqueda_tipo == "NIT":
        query = f"""
        SELECT *
        FROM personas_juridicas
        WHERE nit_empresa = '{entrada}'
        """
    else:
        query = f"""
        SELECT *
        FROM personas_juridicas
        WHERE lower(nombre_empresa) LIKE '%{entrada.lower()}%'
        """

    with st.spinner('Buscando...'):
        original_df = query_athena(query)

    if original_df.empty:
        st.error("No se encontraron resultados para el criterio de búsqueda.")
        st.stop()

    # Para búsqueda por nombre se selecciona la mejor coincidencia (búsqueda fuzzy)
    if busqueda_tipo == "Nombre":
        best_ratio = 0
        best_row = None
        for idx, row in original_df.iterrows():
            ratio = difflib.SequenceMatcher(None, entrada.lower(), row["nombre_empresa"].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_row = row
        if best_row is None:
            st.error("No se encontró una coincidencia cercana.")
            st.stop()
        # Se conserva solo la fila con la mejor coincidencia
        original_df = best_row.to_frame().T
        # Se actualiza la variable de búsqueda para obtener el grafo
        entrada = best_row["nit_empresa"]

    st.dataframe(original_df)
    draw_empresas(original_df)
    get_graph(entrada)
