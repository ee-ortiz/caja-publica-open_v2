# auth/main_auth.py

import os
import json
import jwt
import requests
import asyncio
import streamlit as st
import extra_streamlit_components as stx

from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, auth

# ----------------------------------------------------------------------
# CONSTANTES Y CONFIGURACIÓN
# ----------------------------------------------------------------------

FIREBASE_CREDENTIALS_PATH = "caja-publica-firebase-adminsdk-fbsvc-1827f76da3.json"
COOKIE_NAME = "login_cookie"           # Nombre principal de cookie (para login)
RL_COOKIE_NAME = "rl"                  # Nombre de cookie para "rate limit"
COOKIE_KEY = "my_secret_key"           # Clave usada para firmar el JWT
POST_REQUEST_URL_BASE = "https://identitytoolkit.googleapis.com/v1/accounts:"
COOKIE_EXPIRY_DAYS = 30

# ----------------------------------------------------------------------
# INICIALIZACIÓN DE FIREBASE (SOLO UNA VEZ)
# ----------------------------------------------------------------------

try:
    with open(FIREBASE_CREDENTIALS_PATH, "r") as f:
        firebase_creds = json.load(f)
except Exception as e:
    st.error(f"Error cargando credenciales de Firebase: {e}")
    st.stop()

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
        print("Firebase inicializado correctamente.")
    except Exception as e:
        st.error(f"Error al inicializar Firebase: {e}")
        st.stop()

# ----------------------------------------------------------------------
# MANEJO DE COOKIES
# ----------------------------------------------------------------------

@st.cache_resource
def get_manager():
    """
    Retorna un único CookieManager en toda la aplicación.
    """
    return stx.CookieManager()

cookie_manager = get_manager()

def token_encode(name: str, username: str, exp_date: datetime) -> str:
    """
    Genera un JWT con la información necesaria.
    """
    payload = {
        "name": name,
        "username": username,
        "exp_date": exp_date.timestamp()
    }
    return jwt.encode(payload, COOKIE_KEY, algorithm="HS256")

async def write_cookie(
    cookie_name: str, 
    name: str, 
    username: str,
    exp_date: datetime
) -> None:
    """
    Guarda un token JWT en la cookie `cookie_name` con fecha de expiración `exp_date`.
    """
    encoded = token_encode(name, username, exp_date)
    cookie_manager.set(
        cookie_name,
        encoded,
        expires_at=exp_date,
    )
    # Pequeño sleep para “simular” asincronía en Streamlit
    await asyncio.sleep(0.05)

def cookie_is_valid_v2(cookie_name: str) -> bool:
    """
    Verifica si la cookie con nombre `cookie_name` contiene un JWT válido
    (que no esté expirado y cuya decodificación sea correcta).
    Retorna True o False.
    """
    token = cookie_manager.get(cookie_name)
    if not token:
        return False
    try:
        decoded = jwt.decode(token, COOKIE_KEY, algorithms=["HS256"])
        exp_ts = decoded.get("exp_date", 0)
        if datetime.now().timestamp() > exp_ts:
            # Token expirado: se elimina
            cookie_manager.delete(cookie_name)
            return False
        # Si no está expirado
        return True
    except:
        cookie_manager.delete(cookie_name)
        return False

def not_logged_in(cookie_name: str, preauthorized: str = None) -> bool:
    """
    Retorna True si la cookie `cookie_name` no existe o es inválida.
    Si se pasa `preauthorized`, se podría forzar que el correo (decoded["username"])
    termine en dicho dominio. Si no cumple, también se considera "not logged in".
    """
    token = cookie_manager.get(cookie_name)
    if not token:
        return True

    try:
        decoded = jwt.decode(token, COOKIE_KEY, algorithms=["HS256"])
        user_email = decoded.get("username", "")
        
        # Revisa expiración
        exp_ts = decoded.get("exp_date", 0)
        if datetime.now().timestamp() > exp_ts:
            cookie_manager.delete(cookie_name)
            return True

        # Si hay "preauthorized", check dominio
        if preauthorized and not user_email.endswith(preauthorized):
            return True

        return False
    except:
        cookie_manager.delete(cookie_name)
        return True

# ----------------------------------------------------------------------
# REGISTRO Y AUTENTICACIÓN CON FIREBASE
# ----------------------------------------------------------------------

def register_user(email: str, name: str, password: str):
    """
    Registra un nuevo usuario en Firebase.
    Retorna el user_id si todo va bien, None si falla.
    """
    try:
        user = auth.create_user(
            email=email, 
            password=password, 
            display_name=name, 
            email_verified=False
        )
        st.success(f"Usuario {name} registrado con éxito. Verifica tu correo.")
        return user.uid
    except auth.EmailAlreadyExistsError:
        st.error("El correo electrónico ya está registrado.")
    except Exception as e:
        st.error(f"Error al registrar usuario: {e}")

    return None

def authenticate_user(email: str, password: str):
    """
    Autentica un usuario en Firebase usando la REST API de Firebase Auth.
    Retorna el JSON (con `idToken`, `localId`, etc.) o None si falla.
    """
    url = f"{POST_REQUEST_URL_BASE}signInWithPassword?key={firebase_creds['private_key_id']}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        st.error("Autenticación fallida. Verifica usuario y contraseña.")
        return None
    return response.json()

# ----------------------------------------------------------------------
# FORMULARIOS DE LOGIN Y REGISTRO
# ----------------------------------------------------------------------

def login_form():
    """
    Formulario para que el usuario introduzca email y password y 
    se autentique con Firebase. Si es correcto, setea la cookie interna 
    con un JWT propio (no el token de Firebase).
    """
    st.subheader("Iniciar Sesión")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        user_data = authenticate_user(email, password)
        if user_data:
            # Autenticación ok
            # Guardamos un JWT propio en la cookie
            # (Puedes usar también user_data["idToken"] si lo deseas directamente)
            exp_date = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)

            # Guardamos datos en session_state por si se requieren
            st.session_state["name"] = user_data.get("displayName", email)
            st.session_state["username"] = email
            st.session_state["authentication_status"] = True

            # Escribimos cookie asíncronamente
            asyncio.run(
                write_cookie(
                    COOKIE_NAME, 
                    st.session_state["name"],
                    st.session_state["username"],
                    exp_date
                )
            )
            st.success(f"Bienvenido, {st.session_state['name']}!")
            st.experimental_rerun()  # Forzamos un refresco

def register_user_form():
    """
    Formulario de registro de usuario.
    """
    st.subheader("Registrarse")
    with st.form("register_form"):
        email = st.text_input("E-mail")
        name = st.text_input("Nombre")
        password = st.text_input("Contraseña", type="password")
        confirm_password = st.text_input("Confirmar contraseña", type="password")
        submit = st.form_submit_button("Registrarme")

    if submit:
        if password != confirm_password:
            st.error("Las contraseñas no coinciden.")
            return

        user_id = register_user(email, name, password)
        if user_id:
            st.success("Registro exitoso. Revisa tu correo para verificar tu cuenta.")

# ----------------------------------------------------------------------
# PANELES / UTILS PARA MOSTRAR EN LA SIDEBAR O DONDE SE REQUIERA
# ----------------------------------------------------------------------

def login_panel(cookie_name: str = COOKIE_NAME):
    """
    Panel que muestra un botón para cerrar sesión (si el usuario 
    no es invitado).
    """
    if st.button("Cerrar sesión"):
        cookie_manager.delete(cookie_name)
        st.session_state["logout"] = True
        st.session_state["name"] = None
        st.session_state["username"] = None
        st.session_state["authentication_status"] = None
        st.success("Sesión cerrada.")
        st.experimental_rerun()
