import streamlit as st
from utils import tipos_contratos
from auth.main_auth import login_panel, cookie_manager, COOKIE_NAME
from feedback.main import main_feedback
from streamlit_extras.switch_page_button import switch_page

if "clicked" not in st.session_state:
    st.session_state.clicked = False

def click_button():
    """
    Marca en session_state que se hizo clic en "Regístrate"
    para manejar la lógica en la página actual.
    """
    st.session_state.clicked = True

def draw_sidebar():
    """
    Dibuja la barra lateral:
    - Selección de tipo de búsqueda (persona, empresa, entidad)
    - Filtros de tipo de contrato y año
    - Sección de feedback
    - Botón Cerrar sesión (si no es 'guest')
    - Botón Regístrate (si es invitado o @gmail.com)
    """
    print("Starting sidebar..")
    with st.sidebar:
        # Navegación principal
        st.title("Tipo de búsqueda")
        radio = st.radio(
            "Buscar:",
            ("Por persona", "Por empresa", "Por entidad estatal")
        )

        # Filtros
        st.title("Filtros")
        st.subheader("Tipo de contrato")
        tipo_contrato = st.multiselect(
            "Seleccione un tipo de contrato",
            tipos_contratos,
            default="Todos",
            key="tipo_contrato"
        )

        st.subheader("Año")
        prefilter = st.radio("Seleccione:", ("Todos", "Ciertos años"), index=0, key="prefilter")
        if prefilter == "Ciertos años":
            year_value = st.slider(
                "Seleccione un rango de años:",
                2005, 2023, (2020, 2024),
                key="year_value"
            )
        else:
            year_value = "Todos"

        st.divider()
        st.header("Feedback")
        with st.expander("Danos tu opinión"):
            main_feedback()

        st.divider()
        print("USERNAME: ", st.session_state["username"])

        # Botón de cerrar sesión (sólo si NO es guest)
        if st.session_state["username"] != "guest" and st.session_state["username"] != "@gmail.com":
            print("Flujo de cerrar sesion..")
            st.session_state["activate_toast"] = False
            # Llamamos al panel de login, que internamente incluye "Cerrar sesión"
            login_panel(cookie_name=COOKIE_NAME)

        # Botón de registro (sólo si es guest o @gmail.com)
        if st.session_state["username"] == "guest" or st.session_state["username"] == "@gmail.com":
            registrarse = st.button("Regístrate", on_click=click_button)
            if st.session_state.clicked:
                print("RUNNING THIS!")
                st.session_state["guestWantsRegistration"] = True
                switch_page("login")
                st.session_state["requestForLogin"] = True
                st.session_state.clicked = False
            if registrarse:
                print("now here!")
                switch_page("login")

    return radio, tipo_contrato, year_value
