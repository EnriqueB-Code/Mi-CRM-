import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime, timedelta

# Configuración inicial
st.set_page_config(page_title="CRM Enrique", layout="wide")

# Conexiones
conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)
conn_marketing = st.connection("gsheets_marketing", type=GSheetsConnection)

# --- LOGIN SIMPLIFICADO ---
if 'logeado' not in st.session_state:
    st.session_state.update({'logeado': False, 'usuario': "", 'rol': ""})

def verificar_login(user_in, pass_in):
    try:
        # Forzamos la lectura fresca de usuarios
        df = conn_servicio.read(worksheet="Usuarios", ttl=0).dropna(how='all')
        user_row = df[(df['Usuario'].astype(str).str.strip() == user_in.strip()) & 
                      (df['Password'].astype(str).str.strip() == str(pass_in).strip())]
        
        if not user_row.empty:
            st.session_state.update({'logeado': True, 'usuario': user_in, 'rol': str(user_row.iloc[0]['Rol']).strip()})
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

if not st.session_state.logeado:
    st.title("🔐 Acceso")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            verificar_login(u, p)
    st.stop()

# --- SI YA PASÓ EL LOGIN, CARGAR LA APP ---
st.sidebar.markdown(f"👤 {st.session_state.usuario} | 🛡️ {st.session_state.rol}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logeado = False
    st.rerun()

# --- AQUÍ VA EL RESTO DE TU APP ---
# He simplificado la estructura para evitar errores de conexión
st.write("Bienvenido al sistema.")
# (Aquí puedes pegar la parte de la lógica de tablas que teníamos antes, 
# pero asegúrate de no duplicar las conexiones o el st.set_page_config)
