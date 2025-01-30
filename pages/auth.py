import streamlit as st
import asyncio
from datetime import datetime, timedelta

from auth.main_auth import (
    cookie_is_valid_v2,
    not_logged_in,
    login_panel,
    cookie_manager,
    COOKIE_NAME,
    RL_COOKIE_NAME,
    write_cookie
)

def auth_function():
    """
    Ejemplo de página que muestra un flujo de verificación.
    Aquí podrías manejar la creación de un usuario invitado o
    la detección de rate-limit, etc.
    """
    # Si la cookie de rate-limit (RL) es válida, mostrar un mensaje
    if cookie_is_valid_v2(RL_COOKIE_NAME):
        st.title("Rate limit")
        st.write("Has excedido el límite de búsquedas. Por favor, regístrate para continuar.")
        return

    # Si la cookie principal no es válida, no está logueado
    if not cookie_is_valid_v2(COOKIE_NAME):
        st.write("No estás logueado. Se creará usuario invitado.")
        exp_date = datetime.now() + timedelta(days=1)
        st.session_state["name"] = "Guest"
        st.session_state["username"] = "guest"
        st.session_state["authentication_status"] = True
        st.session_state["logout"] = False

        asyncio.run(write_cookie(COOKIE_NAME, "Guest", "guest", exp_date))
        st.success("Sesión invitado iniciada.")
    else:
        st.write("Ya estás logueado con cookie válida.")
        login_panel(cookie_name=COOKIE_NAME)

if __name__ == "__main__":
    auth_function()
