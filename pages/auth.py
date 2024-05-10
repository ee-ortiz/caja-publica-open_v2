import streamlit as st
import firebase_admin
from auth.main_auth import cookie_is_valid, not_logged_in, login_panel, cookie_manager, cookie_name, write_cookie
import asyncio
from datetime import datetime, timedelta
from streamlit_extras.switch_page_button import switch_page

def auth_function():

    if cookie_is_valid(cookie_manager, "rl"):
        print("RATE LIMIT STEP")
        st.title("Rate limit")
        st.write("Has excedido el límite de búsquedas. Por favor, regístrate para seguir utilizando la aplicación.")

        
        return "break"



    elif not cookie_is_valid(cookie_manager, cookie_name):
        print("Not logged in.")
        # Create cookie for guest user

        if cookie_is_valid(cookie_manager, "rl") and st.session_state["logout"] == False and not_logged_in(
            cookie_manager, cookie_name, preauthorized="gmail.com"):

            print("There is rate limit.")
        
            print("FIRST")
            return None

        else:
            
            print("Creating cookie for guest user")
            exp_date = datetime.now() + timedelta(days=1)
            st.session_state["name"] = "Guest"
            st.session_state["username"] = "guest"
            st.session_state["authentication_status"] = True
            st.session_state["logout"] = False

            print("Calling async")
            asyncio.run(write_cookie(cookie_manager, "login_cookie", exp_date, "guestWrite"))
            
            print("LOGGED IN")
            return None
    