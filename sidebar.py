import streamlit as st
from utils import tipos_contratos
from auth.main_auth import login_panel, cookie_manager, cookie_name, login_panel_guest
from feedback.main import main_feedback

from streamlit_extras.switch_page_button import switch_page

if "clicked" not in st.session_state:
    st.session_state.clicked = False

def click_button():
    st.session_state.clicked = True


def draw_sidebar():
    print("Starting sidebar..")
    with st.sidebar:
        # Navegacion
        st.title("Tipo de búsqueda")

        radio = st.radio(
            "Buscar:",
            ("Por persona", "Por empresa", "Por entidad estatal")
        )

        # Set sidebar
        st.title("Filtros")
        # Filtro por tipo de contrato
        st.subheader("Tipo de contrato")
        tipo_contrato = st.sidebar.multiselect(
            "Seleccione un tipo de contrato",
            tipos_contratos,
            default="Todos",
            key="tipo_contrato"
        )

        # Filtro por año
        # st.sidebar.header("Filtros")
        st.subheader("Año")
        prefilter = st.radio("Seleccione:", ("Todos", "Ciertos años"), index=0, key="prefilter")
        if prefilter == "Ciertos años":
            year_value= st.sidebar.slider(
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
        # BOTON CERRAR SESION
        if st.session_state["username"] != "guest" and st.session_state["username"] != "@gmail.com":
            print("Flujo de cerrar sesion..")
            st.session_state["activate_toast"] = False
            login_panel(cookie_manager, cookie_name)        

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
            
        # BOTON DE REGISTRO PARA EL GUEST
        # if st.session_state["username"] == "guest":
            # login_panel_guest(cookie_manager, cookie_name)
    return radio, tipo_contrato, year_value
