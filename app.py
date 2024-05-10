import streamlit as st
st.set_page_config(
        layout="wide",
        initial_sidebar_state="expanded"
    )

import logging
from sidebar import draw_sidebar
from utils import *
from personas.main import main_personas
from empresas.main import main_empresas
from entidades.main import main_entidades

from auth.main_auth import cookie_is_valid, not_logged_in, login_panel, get_manager, write_cookie, login_form, register_user_form, forgot_password_form, error, cookie_manager, cookie_name, cookie_is_valid_v2
import firebase_admin
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import asyncio
import time
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
def click_button():
    st.session_state.clicked_new = True
    st.session_state["requestForLogin"] = True


def app():
    radio, tipo_contrato, year_slider = draw_sidebar()

    # Set title
    container_titulo = st.container()
    container_titulo.title("Buscador")        
    
    if radio == "Por persona":
        main_personas(tipo_contrato, cookie_manager, year_slider)
        print("Finished main_personas")
        return None

    elif radio == "Por empresa":
        main_empresas(tipo_contrato, year_slider)

    elif radio == "Por entidad estatal":
        main_entidades(tipo_contrato, year_slider)

    print("Leaving app")
    return None

def run():

    print("\n\n", "#"*100)
    print("RUN FUNCTION STARTED.")

    # cookie_manager.get_all()
    # time.sleep(0.01)
    # print("Session state: ", st.session_state)

    if "logout" not in st.session_state:
        st.session_state["logout"] = False

    if "requestForLogin" not in st.session_state:
        st.session_state["requestForLogin"] = False

    if "search_counter" not in st.session_state:
        st.session_state["search_counter"] = 0

    if 'clicked_new' not in st.session_state:
        st.session_state.clicked_new = False

    if 'username' not in st.session_state:
        st.session_state["username"] = "guest"

    if 'authentication_status' not in st.session_state:
        st.session_state["authentication_status"] = None

    if "clicked" not in st.session_state:
        st.session_state.clicked = False

    if "activate_toast" not in st.session_state:
        st.session_state.activate_toast = True

    if 'loged_in_firebase' not in st.session_state:
        st.session_state["loged_in_firebase"] = False

    if 'guestWantsRegistration' not in st.session_state:
        st.session_state["guestWantsRegistration"] = False

    # Set session state before importing other modules
    if "year_value" not in st.session_state:
        st.session_state.year_value = (2000, 2023)
        st.session_state.tipo_contrato = ["Todos"]
        st.session_state.prefilter = "Todos"

    # IMPORTANTE: ANTES DE SIDEBAR
    # A VECES ES ENCESARIO TRAER LAS COOKIES ASI PARA QUE SE ACTUALICE INTERNAMENTE
    # PERO ESTO HACE QUE LA PAGINA SE CARGUE DOS VECES!
    # st.write(get_all_cookies())
    get_all_cookies()
    # cookies = cookie_manager.get_all()
    # st.write(cookies)
    # st.cache_resource.clear()
    


    # cookie_valid = cookie_is_valid(cookie_manager, cookie_name)
    cookie_valid = cookie_is_valid_v2(cookie_name)
    # rl_existe_v1 = cookie_manager.get("rl")
    # rl_existe_v2 = get_all_cookies()["rl"]

    # if rl_existe_v1 and rl_existe_v2:
    #     rl_existe = True
    # else:
    #     rl_existe = False

    rl_existe = get_all_cookies().get("rl", None)

    # FOR DEBUGGING: IT HAS TO BE HERE!
    # st.write(st.session_state)

    # radio, tipo_contrato, year_slider = draw_sidebar()

    if not firebase_admin._apps:
        cred = firebase_admin.credentials.Certificate(
            st.secrets["FIREBASE_AUTH_TOKEN"]
        )
        firebase_admin.initialize_app(cred)



    
    print("START")
    print("TIME: ", datetime.now())
    # print("RL EXISTE V1: ", rl_existe_v1)
    # print("RL EXISTE v2: ", rl_existe_v2)
    print("RL EXISTE: ", rl_existe)
    print("COOKIE VALID: ", cookie_valid)
    print("COOKIE VALID v2: ", cookie_valid)

    if st.session_state["loged_in_firebase"]:
        print("LOGGED IN FIREBASE")
        st.session_state["loged_in_firebase"] = False
        return app()
    

    # st.write(st.session_state)
    # USERNAME guest es necesario para que cuando le de en cerrar sesion, funcione:

    if not cookie_valid and st.session_state["logout"] == True and st.session_state["authentication_status"] == None:
        print("User was logged in and just logged out")
        switch_page("login")
        st.stop()
        return None
        

    if rl_existe and not cookie_valid and st.session_state["logout"] == False and st.session_state["authentication_status"] != True:
        print("Showing user warning...")
        st.session_state["activate_toast"] = True
        switch_page("login")
        st.stop()
        return None

    if not cookie_valid and not rl_existe and st.session_state["requestForLogin"] == False and st.session_state["authentication_status"] != True and st.session_state["username"] == "guest":
        print("GUEST")
            
        print("Creating cookie for guest user")
        exp_date = datetime.now() + timedelta(days=1)
        st.session_state["name"] = "Guest"
        st.session_state["username"] = "guest"
        st.session_state["authentication_status"] = None
        st.session_state["logout"] = False
        # return app(radio, tipo_contrato, year_slider, cookie_valid)
        return app()


    # Not logged in, returns login page
    if not cookie_valid and not_logged_in(
        cookie_manager, cookie_name, preauthorized="gmail.com"
    ):
        print("Not logged in, returns login page")
        # Not logged in, returns login page
        return None
    


    print("None of the cases.")
    # return app(radio, tipo_contrato, year_slider, cookie_valid)
    return app()

if __name__ == "__main__":
    run()