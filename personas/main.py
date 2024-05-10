import os
import streamlit as st
from .grafo import get_graph
from utils import *
from personas.personas_utils import draw_personas
from auth.main_auth import cookie_is_valid, not_logged_in, login_panel, write_cookie
import asyncio
from datetime import datetime, timedelta

from streamlit_extras.switch_page_button import switch_page

def get_all_cookies():
    '''
    WARNING: This uses unsupported feature of Streamlit
    Returns the cookies as a dictionary of kv pairs
    '''
    from streamlit.web.server.websocket_headers import _get_websocket_headers 
    # https://github.com/streamlit/streamlit/pull/5457
    from urllib.parse import unquote

    headers = _get_websocket_headers()
    if headers is None:
        return {}
    
    if 'Cookie' not in headers:
        return {}
    
    cookie_string = headers['Cookie']
    # A sample cookie string: "K1=V1; K2=V2; K3=V3"
    cookie_kv_pairs = cookie_string.split(';')

    cookie_dict = {}
    for kv in cookie_kv_pairs:
        k_and_v = kv.split('=')
        k = k_and_v[0].strip()
        v = k_and_v[1].strip()
        cookie_dict[k] = unquote(v) #e.g. Convert name%40company.com to name@company.com
    return cookie_dict

def main_personas(tipo_contrato, cookie_manager, year_slider):


    # Current radio in environment variable:
    os.environ['RADIO'] = "Por persona"

    # Input box for cedula
    cedula = st.text_input("Cédula", value="")
    cedula = cedula.replace(".", "").replace(",", "")
    print("CEDULA: ", cedula)
    print("SEARCH COUNTER: ", st.session_state.search_counter)
    # If search counter is greater than 5, check if user is logged in
    N = 5


    print("st.session_state username: ", st.session_state["username"])
    print("Session state: ", st.session_state)

    if st.session_state.search_counter > N and st.session_state["username"] == "guest":
        print(f"SEARCH COUNTER MORE THAN {N}: ", st.session_state.search_counter)
        # if not cookie_is_valid(cookie_manager, cookie_name):
        # cookie_manager.delete("login_cookie") # this makes it return to the login page
        print("Calling async for rate limit cookie")
        exp_date = datetime.now() + timedelta(days=30)
        asyncio.run(write_cookie(cookie_manager, "rl", exp_date, "rlWrite"))
        st.session_state["logout"] = True   
        st.session_state["name"] = None
        st.session_state["username"] = None
        st.session_state["authentication_status"] = None
        st.session_state["search_counter"] = 0
        print("Leaving main_personas")
        # st.warning("Has excedido el límite de búsquedas. Por favor, regístrate para seguir utilizando la aplicación.")
        # switch_page("login")
        return None


            

    # If cedula is empty, stop
    if cedula == "":
        print("Cedula is empty")
        st.stop()
        return None

    query = f"""
    SELECT
        *
    FROM
        personas_naturales
    WHERE
        documento_persona = '{cedula}'
    """

    
    original_df = query_postgres(query)

    print("TIPO CONTRATO: ", st.session_state.tipo_contrato)
    print("YEAR VALUE: ", st.session_state.year_value)

    # Filter by tipo_contrato according to sidebar
    if st.session_state.tipo_contrato != ["Todos"]:
        original_df = original_df[original_df['tipo_contrato'].isin(tipo_contrato)]

    # Filter by year according to sidebar
    if st.session_state.prefilter != "Todos":
        original_df = original_df[original_df['fecha_firma_contrato'].dt.year.between(int(st.session_state.year_value[0]), int(st.session_state.year_value[1]), inclusive='both')]

    # st.dataframe(original_df)

    # Replace empty by NaN in valor_contrato and pago_por_mes
    draw_result = draw_personas(original_df)

    graph_result = get_graph(cedula)

    # Increase search counter
    st.session_state.search_counter += 1

    # st.header("Grafo")
    # HtmlFile = open('streamlit_edges.html', 'r', encoding='utf-8')
    # source_code = HtmlFile.read()
    # components.html(source_code, height = 900,width=1000)

    return None
