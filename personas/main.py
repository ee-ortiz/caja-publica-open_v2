import os
import streamlit as st
from .grafo import get_graph
from utils import *
from personas.personas_utils import draw_personas

# Ajustamos imports para no usar cookie_is_valid sino cookie_is_valid_v2,
# y en caso de que no se use, lo removemos directamente.
from auth.main_auth import write_cookie, RL_COOKIE_NAME  # login_panel ya no se usa aquí
import asyncio
from datetime import datetime, timedelta

from streamlit_extras.switch_page_button import switch_page
import difflib  # Para hacer la búsqueda fuzzy

def get_all_cookies():
    """
    WARNING: Usa una característica no soportada de Streamlit.
    Retorna las cookies como un dict de pares clave/valor.
    """
    from urllib.parse import unquote
    headers = st.context.headers
    if headers is None:
        return {}
    if 'Cookie' not in headers:
        return {}
    cookie_string = headers['Cookie']
    cookie_kv_pairs = cookie_string.split(';')
    cookie_dict = {}
    for kv in cookie_kv_pairs:
        k_and_v = kv.split('=')
        k = k_and_v[0].strip()
        v = k_and_v[1].strip()
        cookie_dict[k] = unquote(v)
    return cookie_dict

def main_personas(tipo_contrato, cookie_manager, year_slider):
    """
    Lógica principal cuando se selecciona "Por persona".
    - Permite buscar por cédula o por nombre.
    - Si se busca por nombre, realiza una búsqueda fuzzy para seleccionar
      la coincidencia más cercana.
    - Verifica límites de búsquedas, realiza el query a Athena y dibuja los resultados.
    """
    os.environ['RADIO'] = "Por persona"

    # Selección del tipo de búsqueda: Cédula o Nombre
    busqueda_tipo = st.radio("Buscar por", options=["Cédula", "Nombre"])

    # Input según el tipo de búsqueda
    if busqueda_tipo == "Cédula":
        identificador = st.text_input("Cédula", value="").replace(".", "").replace(",", "")
    else:
        identificador = st.text_input("Nombre", value="").strip()

    st.write(f"**Busqueda por {busqueda_tipo}:** {identificador}")
    st.write("SEARCH COUNTER:", st.session_state.search_counter)

    N = 5  # Límite de búsquedas gratis
    if st.session_state.search_counter > N and st.session_state["username"] == "guest":
        exp_date = datetime.now() + timedelta(days=30)
        asyncio.run(write_cookie(RL_COOKIE_NAME, "RateLimit", "RateLimit", exp_date))
        st.session_state["logout"] = True
        st.session_state["name"] = None
        st.session_state["username"] = None
        st.session_state["authentication_status"] = None
        st.session_state["search_counter"] = 0
        return None

    # Si no se ingresa valor, detenemos la ejecución
    if identificador == "":
        st.stop()
        return None

    # Construimos la consulta según el tipo de búsqueda
    if busqueda_tipo == "Cédula":
        query = f"""
        SELECT *
        FROM personas_naturales
        WHERE documento_persona = '{identificador}'
        """
    else:  # Búsqueda por Nombre
        query = f"""
        SELECT *
        FROM personas_naturales
        WHERE lower(nombre_persona) LIKE '%{identificador.lower()}%'
        """

    original_df = query_athena(query)

    if original_df.empty:
        st.error("No se encontraron resultados para el criterio de búsqueda.")
        st.stop()
        return None

    # Si se buscó por nombre, seleccionamos la coincidencia más cercana
    if busqueda_tipo == "Nombre":
        best_ratio = 0
        best_row = None
        for idx, row in original_df.iterrows():
            ratio = difflib.SequenceMatcher(None, identificador.lower(), row["nombre_persona"].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_row = row
        if best_row is None:
            st.error("No se encontró una coincidencia cercana.")
            st.stop()
            return None
        # Se utiliza solo la fila con la mejor coincidencia
        original_df = best_row.to_frame().T
        # Se actualiza el identificador a la cédula del resultado
        identificador = best_row["documento_persona"]

    # Filtro por tipo de contrato
    if st.session_state.tipo_contrato != ["Todos"]:
        original_df = original_df[original_df['tipo_contrato'].isin(tipo_contrato)]

    # Filtro por año
    if st.session_state.prefilter != "Todos":
        original_df = original_df[
            original_df['fecha_firma_contrato'].dt.year.between(
                int(st.session_state.year_value[0]),
                int(st.session_state.year_value[1]),
                inclusive='both'
            )
        ]

    # Muestra resultados y grafo
    draw_personas(original_df)
    get_graph(identificador)

    # Incrementa el contador de búsquedas
    st.session_state.search_counter += 1

    return None
