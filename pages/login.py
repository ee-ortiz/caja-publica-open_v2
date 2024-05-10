import streamlit as st

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

from auth.main_auth import not_logged_in, cookie_manager, cookie_name, cookie_is_valid, cookie_is_valid_v2
from streamlit_extras.switch_page_button import switch_page
import time

from datetime import datetime, timedelta

import extra_streamlit_components as stx

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
    print("\n" + "!"*100)
    print("Starting login function")
    print(datetime.now())

    get_all_cookies()
    # cookies = cookie_manager.get_all()

    # valid_cookie = cookie_is_valid(cookie_manager, "login_cookie")
    time.sleep(0.05)
    valid_cookie = cookie_is_valid_v2(cookie_name)
    rl_existe = cookie_manager.get("rl")
    print("RL EXISTE: ", rl_existe)
    print("COOKIE VALID: ", valid_cookie)

    # st.write(st.session_state)

    if st.session_state["loged_in_firebase"]:
        print("LOGGED IN FIREBASE")
        switch_page("app") 

    if valid_cookie:
        print("VALID COOKIE")
        switch_page("app") # necesaria para cuando el usuario se logea, esto lo redirige a la pagina principal

    # Not logged in, returns login page
    elif not valid_cookie and not_logged_in(
        cookie_manager, cookie_name
    ):
        # if st.session_state["activate_toast"]:
        #     st.toast("Has excedido el límite de búsquedas. Por favor, regístrate para seguir utilizando la aplicación.")
        #     time.sleep(2)
        #     st.session_state["activate_toast"] = False
        print("Not logged in, returns login page")
        
        # Not logged in, returns login page
        return None

    
        print("Over here")

    elif not valid_cookie and not rl_existe and st.session_state["requestForLogin"] == False and st.session_state["authentication_status"]:
        print("GUEST")
            
        print("Creating cookie for guest user")
        exp_date = datetime.now() + timedelta(days=1)
        st.session_state["name"] = "Guest"
        st.session_state["username"] = "guest"
        st.session_state["authentication_status"] = False
        st.session_state["logout"] = False
        return True

    else:

        return True
    
if __name__ == "__main__":
    login_function()
