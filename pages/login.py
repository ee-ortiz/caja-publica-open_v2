import streamlit as st
from datetime import datetime, timedelta
from streamlit_extras.switch_page_button import switch_page

from auth.main_auth import (
    cookie_is_valid_v2,
    not_logged_in,
    cookie_manager,
    COOKIE_NAME,
    RL_COOKIE_NAME,
    login_form,
    register_user_form,
    write_cookie
)

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
)

def get_all_cookies():
    """
    WARNING: Usa una característica no soportada de Streamlit.
    Retorna un dict con los cookies.
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

# Estado inicial
if "logout" not in st.session_state:
    st.session_state["logout"] = False
if "requestForLogin" not in st.session_state:
    st.session_state["requestForLogin"] = False
if "search_counter" not in st.session_state:
    st.session_state["search_counter"] = 0
if 'clicked' not in st.session_state:
    st.session_state.clicked_new = False
if 'username' not in st.session_state:
    st.session_state["username"] = "guest"
if 'authentication_status' not in st.session_state:
    st.session_state["authentication_status"] = None
if 'requestForRegister' not in st.session_state:
    st.session_state["requestForRegister"] = False
if 'activate_toast' not in st.session_state:
    st.session_state["activate_toast"] = False
if 'loged_in_firebase' not in st.session_state:
    st.session_state["loged_in_firebase"] = False

def login_function():
    """
    Lógica principal de la página login.
    - Si hay cookie válida, redirige a 'app'.
    - Si hay rate limit, muestra aviso para registrarse.
    - Si no, muestra tabs para login y registro.
    """
    # Forzamos lectura actual de cookies
    get_all_cookies()

    valid_cookie = cookie_is_valid_v2(COOKIE_NAME)
    rl_existe = cookie_is_valid_v2(RL_COOKIE_NAME)  # Para ver si se superó el rate-limit

    # Caso: el usuario se logueó con Firebase en otro punto
    if st.session_state["loged_in_firebase"]:
        switch_page("app")

    # Caso: cookie principal válida
    if valid_cookie:
        switch_page("app")
    else:
        # No hay cookie válida
        if rl_existe:
            # Hay rate-limit: forzamos registro o mostramos aviso
            st.warning("Has excedido el límite de búsquedas. Regístrate para continuar.")
            register_user_form()
        else:
            # Muestra formularios de login y registro
            tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
            with tab1:
                login_form()
            with tab2:
                register_user_form()

if __name__ == "__main__":
    login_function()
