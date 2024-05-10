from utils import *
import streamlit as st
from empresas.empresas_utils import draw_empresas
from empresas.grafo import get_graph


def main_empresas(tipo_contrato, year_slider):

    # Current radio in environment variable:
    os.environ['RADIO'] = "Por empresa"

    # Input box for cedula
    nit = st.text_input("Ingrese un NIT", value="")
    nit = nit.replace(".", "").replace(",", "")
    nit = nit.replace("-", "")

    # Keep only first 9 digits
    nit = nit[:9]

    print("nit: ", nit)

    # If cedula is empty, stop
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
        original_df = query_postgres(query)

    st.dataframe(original_df)

    # Replace empty by NaN in valor_contrato and pago_por_mes
    draw_empresas(original_df)

    get_graph(nit)
