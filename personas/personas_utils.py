import numpy as np
import streamlit as st
import pandas as pd
from utils import get_keywords, preprocess_data

cols_to_show = [
    'nombre_entidad', 'objeto_contratar', 'tipo_contrato', 'modalidad_contratacion', 'nit_empresa', 'nombre_empresa',
    'fecha_firma_contrato', 'valor_contrato_millones', 'pago_por_mes',
]

beautiful_columns = [
    'Nombre de la entidad', 'Objeto a contratar', 'Tipo de contrato', 'Modalidad de contratación', 'NIT de la empresa',
    'Nombre de la empresa',
    'Fecha de la firma del contrato', 'Valor del contrato (millones)', 'Pago por mes'
]

cols_to_show_contratista = [
    'nombre_entidad', 'objeto_contratar', 'tipo_contrato', 'modalidad_contratacion',
    'fecha_firma_contrato', 'valor_contrato_millones', 'pago_por_mes',
]

beautiful_columns_contratista = [
    'Nombre de la entidad', 'Objeto a contratar', 'Tipo de contrato', 'Modalidad de contratación',
    'Fecha de la firma del contrato', 'Valor del contrato (millones)', 'Pago por mes'
]

info_labels = {
    "Todos": "Todos los contratos.",
    "Contratista": "Contratos donde la persona fue contratada como persona natural.",
    "Representante legal": "Contratos en los que participó la empresa donde esta persona es o fue representante legal.",
    "Representante de empresa en consorcio": "Contratos en los que participó la empresa donde esta persona es o fue representante legal. En este caso, la empresa fue miembro de un consorcio.",
    "Miembro de consorcio": "Contratos donde esta persona participó como miembro de un consorcio, como persona natural."
                                                
}

def show_contratos(df: pd.DataFrame):

    variable = 'tipo_relacion'

    all_types = df[variable].unique()
    all_types = list(all_types)

    # Add "Todos" to the list
    all_types.append("Todos")
    # st.write(all_types)

    # Create one tab for each tipo_contrato
    tab = st.tabs(all_types)
    for i, tipo_contrato in enumerate(all_types):
        with tab[i]:
            st.info(info_labels[tipo_contrato])
            if tipo_contrato == "Todos":
                df_to_show = df[cols_to_show]
                df_to_show.columns = beautiful_columns
                st.dataframe(df_to_show)

            elif tipo_contrato == "Contratista":
                df_to_show = df[df[variable] == tipo_contrato][cols_to_show_contratista]
                df_to_show.columns = beautiful_columns_contratista
                st.dataframe(df_to_show)
            else:
                df_to_show = df[df[variable] == tipo_contrato][cols_to_show]
                df_to_show.columns = beautiful_columns
                st.dataframe(df_to_show)


    # Insert divider
    st.divider()



    

def draw_personas(original_df: pd.DataFrame):

    # if df is empty
    if original_df.empty:
        st.error("No se encontraron resultados")
        st.stop()
        return None

    original_df = preprocess_data(original_df)

    keywords = get_keywords(original_df)

    nombre_persona = original_df['nombre_persona'].iloc[0].title()
    # st.dataframe(original_df)
    # st.write(original_df.dtypes)
    # Group by nombre_persona, documento_persona, tipo_relacion, nombre_empresa, nit_empresa
    # And get count and sum of valor_contrato and average of pago_por_mes
    df = original_df.groupby(['tipo_relacion', 'nombre_empresa', 'nit_empresa', 'tipo_contrato']).agg(
        {
            'nombre_persona': ['count'],
            'valor_contrato_millones': ['mean'],
            'pago_por_mes': ['mean']
        }
    )

    # Rename columns
    df.columns = ['cantidad_contratos', 'valor_total_contratos', 'pago_promedio_por_mes']

    # Get total of valor_contrato and pago_por_mes
    total_valor_contrato = original_df['valor_contrato_millones'].sum()
    avg_pago_por_mes = original_df['pago_por_mes'].mean()
    total_contratos = original_df['id_unico'].count()

    # Reset index

    st.header(nombre_persona)

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
    st.header("Historial de contratos por relación")

    # Show results
    # st.dataframe(original_df[cols_to_show])
    show_contratos(original_df)