import streamlit as st

import logging
from utils import *
from personas.main import main_personas
from empresas.main import main_empresas
from entidades.main import main_entidades

from sidebar import draw_sidebar

# Importa las funciones y constantes desde auth/main_auth.py
from auth.main_auth import (
    cookie_is_valid_v2,
    not_logged_in,
    login_panel,
    cookie_manager,
    COOKIE_NAME,
    RL_COOKIE_NAME,
    write_cookie
)

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)

col1, col2 = st.columns([1, 3])  # Primera columna más pequeña, segunda más grande

with col1:
    st.image("assets/logo.png", width=175)


import firebase_admin
from firebase_admin import credentials
import json
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import asyncio
import time
from streamlit_extras.switch_page_button import switch_page
import os

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

def click_button():
    """
    Callback para marcar en session_state
    que se dio clic en "registrarse" cuando
    se está como invitado.
    """
    st.session_state.clicked_new = True
    st.session_state["requestForLogin"] = True

def app():
    """
    Función que dibuja la interfaz principal de la aplicación (barra lateral,
    lógica de cada búsqueda por persona, empresa o entidad).
    """
    radio, tipo_contrato, year_slider = draw_sidebar()
    container_titulo = st.container()
    container_titulo.title("Buscador")

    if radio == "Por persona":
        main_personas(tipo_contrato, cookie_manager, year_slider)
        return

    elif radio == "Por empresa":
        main_empresas(tipo_contrato, year_slider)
        return

    elif radio == "Por entidad estatal":
        main_entidades(tipo_contrato, year_slider)
        return

def chatbot():
    """
    Función que dibuja la interfaz del chatbot.
    """
    st.title("Chatbot")
    st.write("¡Hola! Soy el chatbot de la Caja de la Verdad. ¿En qué puedo ayudarte?")
    st.write("Por favor, escribe tu mensaje en el cuadro de texto a continuación.")
    stx.chatbot("chatbot")

def run():
    """
    Punto de entrada principal. Controla la verificación de cookies,
    el estado invitado, el rate-limit, etc.
    """
    # Inicializa ciertas variables de sesión
    if "logout" not in st.session_state:
        st.session_state["logout"] = False
    if "requestForLogin" not in st.session_state:
        st.session_state["requestForLogin"] = False
    if "search_counter" not in st.session_state:
        st.session_state["search_counter"] = 0
    if "clicked_new" not in st.session_state:
        st.session_state.clicked_new = False
    if "username" not in st.session_state:
        st.session_state["username"] = "guest"
    if "authentication_status" not in st.session_state:
        st.session_state["authentication_status"] = None
    if "clicked" not in st.session_state:
        st.session_state.clicked = False
    if "activate_toast" not in st.session_state:
        st.session_state.activate_toast = True
    if "guestWantsRegistration" not in st.session_state:
        st.session_state["guestWantsRegistration"] = False
    if "loged_in_firebase" not in st.session_state:
        st.session_state["loged_in_firebase"] = False

    if "year_value" not in st.session_state:
        st.session_state.year_value = (2000, 2023)
        st.session_state.tipo_contrato = ["Todos"]
        st.session_state.prefilter = "Todos"

    # Forzamos la lectura manual de las cookies (si usas para debug)
    get_all_cookies()

    # Verificamos si la cookie principal es válida
    cookie_valid = cookie_is_valid_v2(COOKIE_NAME)
    # Verificamos si existe cookie de "rate limit"
    rl_existe = get_all_cookies().get(RL_COOKIE_NAME, None)

    # Caso especial: si "loged_in_firebase" está en True (flujo tuyo interno)
    if st.session_state["loged_in_firebase"]:
        st.session_state["loged_in_firebase"] = False
        return app()

    # Caso: el usuario se acaba de desloguear
    if (not cookie_valid) and (st.session_state["logout"] == True) and (st.session_state["authentication_status"] is None):
        switch_page("login")
        st.stop()
        return

    # Caso: hay rate-limit (RL) pero no cookie válida
    if rl_existe and (not cookie_valid) and (st.session_state["logout"] == False) and (st.session_state["authentication_status"] != True):
        st.session_state["activate_toast"] = True
        switch_page("login")
        st.stop()
        return

    # Caso: usuario invitado (sin cookie principal, sin RL)
    if (not cookie_valid) and (not rl_existe) and (st.session_state["requestForLogin"] == False) \
       and (st.session_state["authentication_status"] != True) and (st.session_state["username"] == "guest"):
        # Creamos cookie invitado "básica"
        exp_date = datetime.now() + timedelta(days=1)
        st.session_state["name"] = "Guest"
        st.session_state["username"] = "guest"
        st.session_state["authentication_status"] = None
        st.session_state["logout"] = False
        return app()

    # Caso: no está logueado, vamos a login
    if (not cookie_valid) and not_logged_in(COOKIE_NAME):
        switch_page("login")
        st.stop()
        return

    # Si llegamos aquí, significa que la cookie es válida
    return app()

if __name__ == "__main__":
    run()
