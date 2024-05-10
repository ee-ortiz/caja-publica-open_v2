"""Module for handling authentication, interactions with Firebase and JWT cookies.
This solution is refactored from the ‘streamlit_authenticator’ package . It leverages JSON
Web Token (JWT) cookies to maintain the user’s login state across browser sessions. For the
backend, It uses Google’s Firebase Admin Python SDK. This solution ensures that the content
of the page and user settings panel are only displayed if the user is authenticated. Similarly,
the login page can only be accessed if the user is not authenticated. Upon registration, the
user is sent a verification link to their e-mail address.
Important - to make this app run, put the following variables in your secrets.toml file:
COOKIE_KEY - a random string key for your passwordless reauthentication
FIREBASE_API_KEY - Key for your Firebase API (how to find it -
https://firebase.google.com/docs/projects/api-keys#find-api-keys
)
firebase_auth_token - Information extracted from Firebase login token JSON (how to get one -
https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments
)
"""

import math
import time
from contextlib import suppress
from datetime import datetime, timedelta
from functools import partial
from typing import Dict, Final, Optional, Sequence, Union



import extra_streamlit_components as stx
import firebase_admin
import jwt
import requests
import streamlit as st
from email_validator import EmailNotValidError, validate_email
from firebase_admin import auth
from streamlit_extras.switch_page_button import switch_page
# st.set_page_config(

#     layout="wide",
#     initial_sidebar_state="collapsed",
# )


@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()
# # cookie_manager, cookie_name = stx.CookieManager(), "login_cookie"
cookie_manager, cookie_name = get_manager(), "login_cookie"



import asyncio
async def write_cookie(cookie_manager, cookie_name, exp_date, key="newkey", suffix=""):

    print("Running aysnc function...")
    encoded = token_encode(exp_date)
    print("Encoded: ", encoded)
    cookie_manager.set(
        cookie_name,
        encoded,
        expires_at=exp_date,
        key=key
    )

    time.sleep(2)
    print("Done async function")

TITLE: Final = "Example app"

POST_REQUEST_URL_BASE: Final = "https://identitytoolkit.googleapis.com/v1/accounts:"
post_request = partial(
    requests.post,
    headers={"content-type": "application/json; charset=UTF-8"},
    timeout=10,
)
success = partial(st.success, icon="✅")
error = partial(st.error, icon="🚨")


def pretty_title(title: str) -> None:
    """Make a centered title, and give it a red line. Adapted from
    'streamlit_extras.colored_headers' package.
    Parameters:
    -----------
    title : str
        The title of your page.
    """
    st.markdown(
        f"<h2 style='text-align: center'>{title}</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<hr style="background-color: #ff4b4b; margin-top: 0;'
            ' margin-bottom: 0; height: 3px; border: none; border-radius: 3px;">'
        ),
        unsafe_allow_html=True,
    )


def parse_error_message(response: requests.Response) -> str:
    """
    Parses an error message from a requests.Response object and makes it look better.
    Parameters:
        response (requests.Response): The response object to parse.
    Returns:
        str: Prettified error message.
    Raises:
        KeyError: If the 'error' key is not present in the response JSON.
    """
    return (
        response.json()["error"]["message"]
        .casefold()
        .replace("_", " ")
        .replace("email", "e-mail")
    )


def authenticate_user(
    email: str, password: str, require_email_verification: bool = True
) -> Optional[Dict[str, Union[str, bool, int]]]:
    """
    Authenticates a user with the given email and password using the Firebase Authentication
    REST API.
    Parameters:
        email (str): The email address of the user to authenticate.
        password (str): The password of the user to authenticate.
        require_email_verification (bool): Specify whether a user has to be e-mail verified to
        be authenticated
    Returns:
        dict or None: A dictionary containing the authenticated user's ID token, refresh token,
        and other information, if authentication was successful. Otherwise, None.
    Raises:
        requests.exceptions.RequestException: If there was an error while authenticating the user.
    """

    url = f"{POST_REQUEST_URL_BASE}signInWithPassword?key={st.secrets['FIREBASE_API_KEY']}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
        "emailVerified": require_email_verification,
    }
    response = post_request(url, json=payload)
    if response.status_code != 200:
        error(f"La autenticación falló: {parse_error_message(response)}")
        return None
    response = response.json()
    if require_email_verification and "idToken" not in response:
        error("E-mail o contraseña incorrectos.")
        return None
    return response

import random
import string

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    print("Random string of length", length, "is:", result_str)
    return result_str



def forgot_password_form(preauthorized: Union[str, Sequence[str], None]) -> None:
    """Creates a Streamlit widget to reset a user's password. Authentication uses
    the Firebase Authentication REST API.
    Parameters:
        preauthorized (Union[str, Sequence[str], None]): An optional domain or a list of
        domains which are authorized to register.
    """

    with st.form(f"forgot_password"):
        email = st.text_input("E-mail", key=f"forgot_password")
        if not st.form_submit_button("Recuperar contraseña"):
            return None
    if "@" not in email and isinstance(preauthorized, str):
        email = f"{email}@{preauthorized}"

    url = f"{POST_REQUEST_URL_BASE}sendOobCode?key={st.secrets['FIREBASE_API_KEY']}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    response = post_request(url, json=payload)
    if response.status_code == 200:
        return success(f"Password reset link has been sent to {email}")
    return error(f"Error sending password reset email: {parse_error_message(response)}")



def register_user_form(preauthorized: Union[str, Sequence[str], None]) -> None:
    """Creates a Streamlit widget for user registration.
    Password strength is validated using entropy bits (the power of the password alphabet).
    Upon registration, a validation link is sent to the user's email address.
    Parameters:
        preauthorized (Union[str, Sequence[str], None]): An optional domain or a list of
        domains which are authorized to register.
    """
    print("Starting register_user_form")
    st.session_state["requestForRegister"] = True
    with st.form(key=f"register_form"):
        email, name, password, confirm_password, register_button = (
            st.text_input("E-mail"),
            st.text_input("Nombre"),
            st.text_input("Contraseña", type="password"),
            st.text_input("Confirmar contraseña", type="password"),
            st.form_submit_button(label="Enviar"),
        )
    if not register_button:
        print("Register button is False")
        return None
    # Below are some checks to ensure proper and secure registration
    if password != confirm_password:
        return error("Las contraseñas no coinciden. Por favor, inténtalo de nuevo.")
    if not name:
        return error("Por favor, introduce tu nombre.")
    if "@" not in email and isinstance(preauthorized, str):
        email = f"{email}@{preauthorized}"
    if preauthorized and not email.endswith(preauthorized):
        return error("Domain not allowed")
    try:
        validate_email(email, check_deliverability=True)
    except EmailNotValidError as e:
        return error(e)

    # Need a password that has minimum 66 entropy bits (the power of its alphabet)
    # I multiply this number by 1.5 to display password strength with st.progress
    # For an explanation, read this -
    # https://en.wikipedia.org/wiki/Password_strength#Entropy_as_a_measure_of_password_strength
    alphabet_chars = len(set(password))
    strength = int(len(password) * math.log2(alphabet_chars) * 3)
    if strength < 100:
        st.progress(strength)
        return st.warning(
            "La contraseña es débil. Por favor, elige una contraseña más segura incluyendo números y caracteres especiales.", icon="⚠️"
        )
    
    # Catch EmailAlreadyExistsError when creating a new user
    try:
        auth.create_user(
            email=email, password=password, display_name=name, email_verified=False
        )
    except auth.EmailAlreadyExistsError:
        return error("El correo electrónico ya está registrado.")
    # Having registered the user, send them a verification e-mail
    token = authenticate_user(email, password, require_email_verification=False)[
        "idToken"
    ]
    url = f"{POST_REQUEST_URL_BASE}sendOobCode?key={st.secrets['FIREBASE_API_KEY']}"
    payload = {"requestType": "VERIFY_EMAIL", "idToken": token}
    response = post_request(url, json=payload)
    if response.status_code != 200:
        return error(f"Error sending verification email: {parse_error_message(response)}")
    # success(
    #     "Your account has been created successfully. To complete the registration process, "
    #     "please verify your email address by clicking on the link we have sent to your inbox."
    # )
    success(
        "Tu cuenta ha sido creada exitosamente. Para completar el proceso de registro, "
        "verifica tu dirección de correo electrónico haciendo clic en el enlace que te hemos enviado."
    )
    return st.balloons()


def update_password_form() -> None:
    """Creates a Streamlit widget to update a user's password."""

    # Get the email and password from the user
    new_password = st.text_input("New password", key="new_password")
    # Attempt to log the user in
    if not st.button("Update password"):
        return None
    user = auth.get_user_by_email(st.session_state["username"])
    auth.update_user(user.uid, password=new_password)
    return success("Successfully updated user password.")


def update_display_name_form(
    cookie_manager: stx.CookieManager, cookie_name: str, cookie_expiry_days: int = 30
) -> None:
    """Creates a Streamlit widget to update a user's display name.
    Parameters
    ----------
     - cookie_manager : stx.CookieManager
        A JWT cookie manager instance for Streamlit
    - cookie_name : str
        The name of the reauthentication cookie.
    - cookie_expiry_days: (optional) str
        An integer representing the number of days until the cookie expires
    """

    # Get the email and password from the user
    new_name = st.text_input("New name", key="new name")
    # Attempt to log the user in
    if not st.button("Update name"):
        return None
    user = auth.get_user_by_email(st.session_state["username"])
    auth.update_user(user.uid, display_name=new_name)
    st.session_state["name"] = new_name
    # Update the cookie as well
    exp_date = datetime.utcnow() + timedelta(days=cookie_expiry_days)
    # cookie_manager.set(
    #     cookie_name,
    #     token_encode(exp_date),
    #     expires_at=exp_date,
    # )

    print("Calling async")
    asyncio.run(write_cookie(cookie_manager, cookie_name, exp_date, "updateWrite"))
    print("Just after async")
    return success("Successfully updated user display name.")


def token_encode(exp_date: datetime) -> str:
    """Encodes a JSON Web Token (JWT) containing user session data for passwordless
    reauthentication.
    Parameters
    ----------
    exp_date : datetime
        The expiration date of the JWT.
    Returns
    -------
    str
        The encoded JWT cookie string for reauthentication.
    Notes
    -----
    The JWT contains the user's name, username, and the expiration date of the JWT in
    timestamp format. The `st.secrets["COOKIE_KEY"]` value is used to sign the JWT with
    the HS256 algorithm.
    """
    return jwt.encode(
        {
            "name": st.session_state["name"],
            "username": st.session_state["username"],
            "exp_date": exp_date.timestamp(),
        },
        st.secrets["COOKIE_KEY"],
        algorithm="HS256",
    )


def cookie_is_valid(cookie_manager: stx.CookieManager, cookie_name: str) -> bool:
    """Check if the reauthentication cookie is valid and, if it is, update the session state.
    Parameters
    ----------
     - cookie_manager : stx.CookieManager
        A JWT cookie manager instance for Streamlit
    - cookie_name : str
        The name of the reauthentication cookie.
    - cookie_expiry_days: (optional) str
        An integer representing the number of days until the cookie expires
    Returns
    -------
    bool
        True if the cookie is valid and the session state is updated successfully; False otherwise.
    Notes
    -----
    This function checks if the specified reauthentication cookie is present in the cookies stored by
    the cookie manager, and if it is valid. If the cookie is valid, this function updates the session
    state of the Streamlit app and authenticates the user.
    """
    # print("Starting cookie_is_valid")
    token = cookie_manager.get(cookie_name)
    # print("TOKEN: ", token)
    if token is None:
        return False
    with suppress(Exception):
        token = jwt.decode(token, st.secrets["COOKIE_KEY"], algorithms=["HS256"])
    if (
        token
        and not st.session_state["logout"]
        and token["exp_date"] > datetime.utcnow().timestamp()
        and {"name", "username"}.issubset(set(token))
    ):
        st.session_state["name"] = token["name"]
        st.session_state["username"] = token["username"]
        st.session_state["authentication_status"] = True
        return True
    return False

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

def cookie_is_valid_v2(cookie_name: str) -> bool:

    # print("Starting cookie_is_valid")
    token = get_all_cookies().get(cookie_name, None)
    # print("TOKEN: ", token)
    if token is None:
        print("Token is None")
        return False
    with suppress(Exception):
        token = jwt.decode(token, st.secrets["COOKIE_KEY"], algorithms=["HS256"])
    if (
        token
        and not st.session_state["logout"]
        and token["exp_date"] > datetime.utcnow().timestamp()
        and {"name", "username"}.issubset(set(token))
    ):
        st.session_state["name"] = token["name"]
        st.session_state["username"] = token["username"]
        st.session_state["authentication_status"] = True
        return True
    return False


def login_form(
    cookie_manager: stx.CookieManager,
    cookie_name: str,
    preauthorized: Union[str, Sequence[str], None],
    cookie_expiry_days: int = 30,
) -> None:
    """Creates a login widget using Firebase REST API and a cookie manager.
    Parameters
    ----------
     - cookie_manager : stx.CookieManager
        A JWT cookie manager instance for Streamlit
    - cookie_name : str
        The name of the reauthentication cookie.
    - cookie_expiry_days: (optional) str
        An integer representing the number of days until the cookie expires
    Notes
    -----
    If the user has already been authenticated, this function does nothing. Otherwise, it displays
    a login form which prompts the user to enter their email and password. If the login credentials
    are valid and the user's email address has been verified, the user is authenticated and a
    reauthentication cookie is created with the specified expiration date.
    """
    print("Starting login_form")
    print("Authentication status before login: ", st.session_state["authentication_status"])
    if st.session_state["authentication_status"]:
        return None
    with st.form("Login"):
        email = st.text_input("E-mail")
        if "@" not in email and isinstance(preauthorized, str):
            email = f"{email}@{preauthorized}"
        st.session_state["username"] = email
        password = st.text_input("Contraseña", type="password")
        if not st.form_submit_button("Entrar"):
            return None

    # Authenticate the user with Firebase REST API
    login_response = authenticate_user(email, password)
    if not login_response:
        return None

    decoded_token = auth.verify_id_token(login_response["idToken"])
    user = auth.get_user(decoded_token["uid"])
    if not user.email_verified:
        # return error("Please verify your e-mail address.")
        return error("Por favor, verifica tu dirección de correo electrónico.")
    # At last, authenticate the user
    st.session_state["name"] = user.display_name
    st.session_state["username"] = user.email
    st.session_state["authentication_status"] = True
    st.session_state["logout"] = False
    st.session_state["loged_in_firebase"] = True
    exp_date = datetime.utcnow() + timedelta(days=cookie_expiry_days)
    # cookie_manager.set(
    #     cookie_name,
    #     token_encode(exp_date),
    #     expires_at=exp_date,
    # )

    print("Calling async")
    asyncio.run(write_cookie(cookie_manager, cookie_name, exp_date, "loginWrite"))
    print("Just after async")

    return None


def login_panel(
    cookie_manager: stx.CookieManager, cookie_name: str, cookie_expiry_days: int = 30
) -> None:
    """Creates a side panel for logged-in users, preventing the login menu from
    appearing.
    Parameters
    ----------
     - cookie_manager : stx.CookieManager
        A JWT cookie manager instance for Streamlit
    - cookie_name : str
        The name of the reauthentication cookie.
    - cookie_expiry_days: (optional) str
        An integer representing the number of days until the cookie expires
    Notes
    -----
    If the user is logged in, this function displays two tabs for resetting the user's password
    and updating their display name.
    If the user clicks the "Logout" button, the reauthentication cookie and user-related information
    from the session state is deleted, and the user is logged out.
    """


    if st.button("Cerrar sesión"):
        print("Eliminado cookie para cerrar sesion.")

        cookie_manager.delete(cookie_name)
        st.session_state["logout"] = True
        st.session_state["name"] = None
        st.session_state["username"] = None
        st.session_state["authentication_status"] = None

        return None
    # st.write(f"Welcome, *{st.session_state['name']}*!")
    # user_tab1, user_tab2 = st.tabs(["Reset password", "Update user details"])
    # with user_tab1:
    #     update_password_form()
    # with user_tab2:
    #     update_display_name_form(cookie_manager, cookie_name, cookie_expiry_days)
    return None


def login_panel_guest(
    cookie_manager: stx.CookieManager, cookie_name: str, cookie_expiry_days: int = 30
) -> None:
    """Creates a side panel for logged-in users, preventing the login menu from
    appearing.
    Parameters
    ----------
     - cookie_manager : stx.CookieManager
        A JWT cookie manager instance for Streamlit
    - cookie_name : str
        The name of the reauthentication cookie.
    - cookie_expiry_days: (optional) str
        An integer representing the number of days until the cookie expires
    Notes
    -----
    If the user is logged in, this function displays two tabs for resetting the user's password
    and updating their display name.
    If the user clicks the "Logout" button, the reauthentication cookie and user-related information
    from the session state is deleted, and the user is logged out.
    """



    if st.button("Registro guest"):
        # cookie_manager.delete(cookie_name)
        st.session_state["logout"] = True
        st.session_state["name"] = None
        st.session_state["username"] = None
        st.session_state["authentication_status"] = None
        st.session_state["requestForLogin"] = True
        st.markdown('''
    <a href="javascript:document.getElementsByClassName('st-emotion-cache-ztfqz8 ef3psqc5')[1].click();">
        <img src="https://i.ibb.co/yP2wjhW/jaka-02.png" alt="Logo JAKA" style="width:50px;height:50px;"/>
    </a>
    ''', unsafe_allow_html=True)
        return None
    # st.write(f"Welcome, *{st.session_state['name']}*!")
    # user_tab1, user_tab2 = st.tabs(["Reset password", "Update user details"])
    # with user_tab1:
    #     update_password_form()
    # with user_tab2:
    #     update_display_name_form(cookie_manager, cookie_name, cookie_expiry_days)
    return None


def not_logged_in(
    cookie_manager, cookie_name, preauthorized: Union[str, Sequence[str], None] = None
) -> bool:
    """Creates a tab panel for unauthenticated, preventing the user control sidebar and
    the rest of the script from appearing until the user logs in.
    Parameters
    ----------
     - cookie_manager : stx.CookieManager
        A JWT cookie manager instance for Streamlit
    - cookie_name : str
        The name of the reauthentication cookie.
    - cookie_expiry_days: (optional) str
        An integer representing the number of days until the cookie expires
    Returns
    -------
    Authentication status boolean.
    Notes
    -----
    If the user is already authenticated, the login panel function is called to create a side
    panel for logged-in users. If the function call does not update the authentication status
    because the username/password does not exist in the Firebase database, the rest of the script
    does not get executed until the user logs in.
    """
    print("Starting not logged in.")
    early_return = True

    # In case of a first run, pre-populate missing session state arguments
    for key in {"name", "authentication_status", "username", "logout"}.difference(
        set(st.session_state)
    ):
        st.session_state[key] = None

    # col1, col2, col3 = st.columns([1, 1, 1])
    login_tabs = st.empty()
    col1, col2, col3 = login_tabs.columns([1, 1, 1])
    
    
    with col2:

        col11, col12, col13 = st.columns([1, 1, 1])
        with col12:
            # Insert image here, from local file
            st.image("auth/logo_publiqly_grande.jpg")
        
        login_tab1, login_tab2, login_tab3 = st.tabs(
            ["Ingresar", "Registrarse", "Olvidé mi contraseña"]
        )
        with login_tab1:
            login_form(cookie_manager, cookie_name, preauthorized)
        with login_tab2:
            register_user_form(preauthorized)
        with login_tab3:
            forgot_password_form(preauthorized)
            
        print("Session state: ", st.session_state)

        # Si el usuario esta en la interfaz y le da registrarse, no queremos que muestre esta advertencia!
        if st.session_state["activate_toast"] and st.session_state["guestWantsRegistration"] == False:
            # st.toast("Has excedido el límite de búsquedas. Por favor, regístrate para seguir utilizando la aplicación.")
            st.warning("Has excedido el límite de búsquedas. Por favor, regístrate para seguir utilizando la aplicación.")
            # time.sleep(2)
            

    auth_status = st.session_state["authentication_status"]
    if auth_status is False:
        error("Username/password is incorrect")
        return early_return
    if auth_status is None:
        return early_return
    
    st.session_state["activate_toast"] = False
    # Esto ayuda a que cuando este cargando no se dupliquen los componentes.
    col12.empty()
    col2.empty()
    login_tabs.empty()
    
    # A workaround for a bug in Streamlit -
    # https://playground.streamlit.app/?q=empty-doesnt-work
    # TLDR: element.empty() doesn't actually seem to work with a multi-element container
    # unless you add a sleep after it.
    time.sleep(0.01)
    print("Finished not_logged_in")
    return not early_return


def app() -> None:
    """This is a part of a Streamlit app which is only visible if the user is logged in."""
    st.subheader("Yay!!!")
    st.write("You are logged in!")
    st.write("Hello :sunglasses:")
    
def main() -> None:
    """Launches a Streamlit example interface.
    The interface supports authentication through Firebase REST API and JSON Web Token (JWT)
    cookies. To use the portal, the user must be registered, optionally only with a preauthorized
    e-mail domain. The Firebase REST API and JWT cookies are used for authentication. If the user
    is not logged in, no content other than the login form gets shown.
    """

    st.set_page_config(
        page_title=TITLE,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    # Hides 'Made with Streamlit'
    st.markdown(
        """
        <style>
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # noinspection PyProtectedMember
    if not firebase_admin._apps:
        cred = firebase_admin.credentials.Certificate(
            st.secrets["FIREBASE_AUTH_TOKEN"]
        )
        firebase_admin.initialize_app(cred)
    pretty_title(TITLE)
    cookie_manager, cookie_name = stx.CookieManager(), "login_cookie"

    if not cookie_is_valid(cookie_manager, cookie_name) and not_logged_in(
        cookie_manager, cookie_name, preauthorized="gmail.com"
    ):
        return None

    with st.sidebar:
        login_panel(cookie_manager, cookie_name)

    return app()


# Run the Streamlit app
if __name__ == "__main__":
    main()