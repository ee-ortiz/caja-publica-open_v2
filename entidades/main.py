import os
import streamlit as st
from utils import query_athena
import plotly.express as px
import difflib

def main_entidades(tipo_contrato, year_slider):
    """
    Lógica principal cuando se selecciona 'Por entidad estatal'.
    Permite buscar por NIT o por nombre de entidad.
    - Si se busca por nombre, se realiza una búsqueda fuzzy en los registros
      de personas_naturales para obtener el NIT de la entidad.
    """
    os.environ['RADIO'] = "Por entidad estatal"

    busqueda_tipo = st.radio("Buscar por", options=["NIT", "Nombre"])

    if busqueda_tipo == "NIT":
        entrada = st.text_input("Ingrese un NIT", value="")
        entrada = entrada.replace(".", "").replace(",", "").replace("-", "")
        entrada = entrada[:9]
    else:
        entrada = st.text_input("Ingrese el nombre de la entidad", value="").strip()

    st.write(f"Búsqueda por {busqueda_tipo}: {entrada}")

    if entrada == "":
        st.stop()

    # Si se busca por NIT se utiliza directamente ese valor; de lo contrario se busca la mejor coincidencia
    if busqueda_tipo == "NIT":
        nit = entrada
    else:
        query_entities = f"""
        SELECT DISTINCT nit_entidad, nombre_entidad
        FROM personas_naturales
        WHERE lower(nombre_entidad) LIKE '%{entrada.lower()}%'
        """
        df_entities = query_athena(query_entities)
        if df_entities.empty:
            st.error("No se encontraron resultados para el criterio de búsqueda.")
            st.stop()
        best_ratio = 0
        best_row = None
        for idx, row in df_entities.iterrows():
            ratio = difflib.SequenceMatcher(None, entrada.lower(), row["nombre_entidad"].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_row = row
        if best_row is None:
            st.error("No se encontró una coincidencia cercana.")
            st.stop()
        nit = best_row["nit_entidad"]
        st.write(f"Se seleccionó la entidad: {best_row['nombre_entidad']} (NIT: {nit})")

    query = f"""
    WITH personas_de_esta_entidad_v0 AS (
        SELECT *
        FROM personas_naturales
        WHERE nit_entidad = '{nit}'
    ),
    personas_de_esta_entidad AS (
        SELECT 
            documento_persona AS id,
            nombre_persona AS nombre,
            SUM(valor_contrato_millones) AS suma_contratos_millones,
            COUNT(id_unico) AS total_numero_contratos
        FROM personas_de_esta_entidad_v0
        GROUP BY documento_persona, nombre_persona
    ),
    personas_con_mas_plata AS (
        SELECT 
            *, 'naturales_mas_dinero' AS tipo
        FROM personas_de_esta_entidad
        ORDER BY suma_contratos_millones DESC
        LIMIT 10
    ),
    personas_con_mas_contratos AS (
        SELECT 
            *, 'naturales_mas_contratos' AS tipo
        FROM personas_de_esta_entidad
        ORDER BY total_numero_contratos DESC
        LIMIT 10
    ),
    juridicas_de_esta_entidad AS (
        SELECT
            nit_empresa AS id,
            nombre_empresa AS nombre,
            SUM(valor_contrato_millones) AS suma_contratos_millones,
            COUNT(id_unico) AS total_numero_contratos
        FROM personas_juridicas
        WHERE nit_entidad = '{nit}'
        GROUP BY nit_empresa, nombre_empresa
    ),
    juridicas_con_mas_plata AS (
        SELECT
            *, 'juridicas_mas_dinero' AS tipo
        FROM juridicas_de_esta_entidad
        ORDER BY suma_contratos_millones DESC
        LIMIT 10
    ),
    juridicas_con_mas_contratos AS (
        SELECT
            *, 'juridicas_mas_contratos' AS tipo
        FROM juridicas_de_esta_entidad
        ORDER BY total_numero_contratos DESC
        LIMIT 10
    ),
    personas_con_varios_roles AS (
        SELECT 
            documento_persona AS id, 
            nombre_persona AS nombre, 
            COUNT(DISTINCT tipo_relacion) AS suma_contratos_millones,
            -1 AS total_numero_contratos,
            'personas_con_varios_roles' AS tipo
        FROM personas_de_esta_entidad_v0
        GROUP BY documento_persona, nombre_persona
        HAVING COUNT(DISTINCT tipo_relacion) > 1
    )
    SELECT * FROM personas_con_mas_plata
    UNION ALL
    SELECT * FROM personas_con_mas_contratos
    UNION ALL
    SELECT * FROM juridicas_con_mas_plata
    UNION ALL
    SELECT * FROM juridicas_con_mas_contratos
    UNION ALL
    SELECT * FROM personas_con_varios_roles
    """

    with st.spinner('Buscando...'):
        df = query_athena(query)

    df["suma_contratos_millones"] = df["suma_contratos_millones"].astype(float)
    df["total_numero_contratos"] = df["total_numero_contratos"].astype(int)

    st.title("Análisis de personas")

    st.header("Personas que más plata han recibido")
    naturales_mas_dinero = df[df['tipo'] == 'naturales_mas_dinero'].sort_values(
        by='suma_contratos_millones',
        ascending=True
    )
    fig = px.bar(naturales_mas_dinero, x='suma_contratos_millones', y='nombre')
    st.plotly_chart(fig, use_container_width=True)
    expander = st.expander("Ver datos crudos en una tabla")
    expander.dataframe(naturales_mas_dinero.drop(columns=['tipo']))

    st.header("Personas con más contratos")
    naturales_mas_contratos = df[df['tipo'] == 'naturales_mas_contratos'].sort_values(
        by='total_numero_contratos',
        ascending=True
    )
    fig = px.bar(naturales_mas_contratos, x='total_numero_contratos', y='nombre')
    st.plotly_chart(fig, use_container_width=True)
    expander = st.expander("Ver datos crudos en una tabla")
    expander.dataframe(naturales_mas_contratos.drop(columns=['tipo']))

    st.title("Análisis de empresas")
    st.header("Empresas que más plata han recibido")
    juridicas_mas_dinero = df[df['tipo'] == 'juridicas_mas_dinero'].sort_values(
        by='suma_contratos_millones',
        ascending=True
    )
    fig = px.bar(juridicas_mas_dinero, x='suma_contratos_millones', y='nombre')
    st.plotly_chart(fig, use_container_width=True)
    expander = st.expander("Ver datos crudos en una tabla")
    expander.dataframe(juridicas_mas_dinero.drop(columns=['tipo']))

    st.header("Empresas con más contratos")
    juridicas_mas_contratos = df[df['tipo'] == 'juridicas_mas_contratos'].sort_values(
        by='total_numero_contratos',
        ascending=True
    )
    fig = px.bar(juridicas_mas_contratos, x='total_numero_contratos', y='nombre')
    st.plotly_chart(fig, use_container_width=True)
    expander = st.expander("Ver datos crudos en una tabla")
    expander.dataframe(juridicas_mas_contratos.drop(columns=['tipo']))

    st.title("Personas con varios roles")
    personas_con_varios_roles = df[df['tipo'] == 'personas_con_varios_roles']
    st.dataframe(personas_con_varios_roles)
