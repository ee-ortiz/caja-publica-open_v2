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

def get_all_cookies():
    """
    WARNING: Usa una característica no soportada de Streamlit
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
    - Pide la cédula vía text_input.
    - Verifica si excedió el número de búsquedas como invitado.
    - Realiza el query a Athena y dibuja los resultados.
    """
    # Fijamos variable de entorno (para debug o logs)
    os.environ['RADIO'] = "Por persona"

    # Input para la cédula
    cedula = st.text_input("Cédula", value="")
    cedula = cedula.replace(".", "").replace(",", "")
    print("CEDULA: ", cedula)
    print("SEARCH COUNTER: ", st.session_state.search_counter)

    N = 5  # Límite de búsquedas gratis

    print("st.session_state username: ", st.session_state["username"])
    print("Session state: ", st.session_state)

    # Si excede N búsquedas y es invitado -> poner cookie de "rate limit"
    if st.session_state.search_counter > N and st.session_state["username"] == "guest":
        print(f"SEARCH COUNTER MORE THAN {N}: ", st.session_state.search_counter)
        print("Calling async for rate limit cookie")

        exp_date = datetime.now() + timedelta(days=30)
        # La nueva firma de write_cookie(cookie_name, name, username, exp_date)
        # Podemos usar "RateLimit" de name y username, ya que no es un usuario real,
        # sólo para marcar la cookie RL.
        asyncio.run(write_cookie(RL_COOKIE_NAME, "RateLimit", "RateLimit", exp_date))

        # Forzamos logout y reiniciamos estado
        st.session_state["logout"] = True
        st.session_state["name"] = None
        st.session_state["username"] = None
        st.session_state["authentication_status"] = None
        st.session_state["search_counter"] = 0

        print("Leaving main_personas")
        # Nota: el redireccionamiento al login se hace en app.py,
        #       cuando detecta RL en la cookie o si no es válido.
        return None

    # Si la cédula está vacía, paramos
    if cedula == "":
        print("Cedula is empty")
        st.stop()
        return None
    
    print("SELECCIONAMOS PERSONAS")

    # Construimos query
    query = f"""
    SELECT
        *
    FROM
        personas_naturales
    WHERE
        documento_persona = '{cedula}'
    """

    original_df = query_athena(query)

    print("TIPO CONTRATO: ", st.session_state.tipo_contrato)
    print("YEAR VALUE: ", st.session_state.year_value)

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

    # Dibuja resultados
    draw_personas(original_df)

    # Renderiza grafo (opcional)
    get_graph(cedula)

    # Incrementa el contador de búsquedas
    st.session_state.search_counter += 1

    return None
