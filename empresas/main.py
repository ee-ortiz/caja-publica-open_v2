import os
import streamlit as st
from utils import query_athena
from empresas.empresas_utils import draw_empresas
from empresas.grafo import get_graph

def main_empresas(tipo_contrato, year_slider):
    """
    Lógica principal cuando se selecciona 'Por empresa'.
    - Pide el NIT (sólo 9 dígitos).
    - Consulta personas_juridicas.
    - Muestra dataframe.
    - Llama a draw_empresas() y al grafo de la empresa.
    """
    # Current radio en la variable de entorno (opcional para debug)
    os.environ['RADIO'] = "Por empresa"

    # Input NIT
    nit = st.text_input("Ingrese un NIT", value="")
    nit = nit.replace(".", "").replace(",", "").replace("-", "")
    nit = nit[:9]  # Mantiene primeros 9 dígitos

    print("SELECCIONAMOS EMPRESAS")
    print("nit: ", nit)

    # Si NIT vacío, paramos
    if nit == "":
        st.stop()

    query = f"""
    SELECT
        *
    FROM
        personas_juridicas
    WHERE
        nit_empresa = '{nit}'
    """

    with st.spinner('Buscando...'):
        original_df = query_athena(query)

    st.dataframe(original_df)

    # Dibuja la tabla con tu lógica custom
    draw_empresas(original_df)

    # Llama al grafo
    get_graph(nit)
