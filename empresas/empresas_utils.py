import numpy as np
import streamlit as st
import pandas as pd
from utils import preprocess_data, get_keywords


def draw_empresas(original_df: pd.DataFrame):

    # if df is empty
    if original_df.empty:
        st.error("No se encontraron resultados")
        st.stop()
        return None

    original_df = preprocess_data(original_df)

    # Drop duplicates in id_unico
    original_df = original_df.drop_duplicates(subset=['id_unico'])

    keywords = get_keywords(original_df)

    nombre_empresa = original_df['nombre_empresa'].iloc[0].title()

    # Get total of valor_contrato and pago_por_mes
    total_valor_contrato = original_df['valor_contrato_millones'].sum()
    avg_pago_por_mes = original_df['pago_por_mes'].mean()
    total_contratos = original_df['id_unico'].count()

    # st.dataframe(original_df['id_unico'].value_counts().reset_index().rename(columns={'index': 'id_unico', 'id_unico': 'cantidad_contratos'}))

    # Reset index

    st.header(nombre_empresa)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de contratos", total_contratos)
    col2.metric("Valor total de contratos", f"${int(total_valor_contrato)} millones")
    col3.metric("Promedio de pago por mes", f"${avg_pago_por_mes:.1f} millones" if avg_pago_por_mes > 0 else "N/A")

    st.divider()

    # Areas of expertise
    st.header("Áreas de experiencia")
    # Write a tag for each keyword
    list_of_tags = [f"<span style='      display: inline-block; background-color: #e0e0e0; padding: 5px 10px; border-radius: 5px; margin-bottom: 5px; margin-top: 2px; margin-right: 5px;'>{  tag  }</span>" for tag in keywords]
    # Join the list of tags into a string
    list_of_tags = " ".join(list_of_tags)

    # Now, we can use the markdown component to show the list of tags
    st.markdown(list_of_tags, unsafe_allow_html=True)

    st.divider()
    # st.header("Contratos según tipo de relación")


    # # Show results
    # st.dataframe(df, use_container_width=True)
    st.header("Historial de contratos")

    # Show results
    st.dataframe(original_df)