import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión CRM", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)
    conn_marketing = st.connection("gsheets_marketing", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- LISTA MAESTRA ---
LISTA_EQUIPOS = [
    "SonoEye P1", "SonoEye P2", "SonoEye P3", "SonoEye P5", "SonoEye P6", 
    "ECO1", "ECO2", "ECO3 EXP", "ECO5", "ECO6", 
    "EBit20", "EBit30", "EBit50", "EBit60", 
    "SonoAir20", "SonoAir30", "SonoAir60", "SonoAir70", 
    "SonoBook6", "SonoBook7", "SonoBook8", "SonoBook9", 
    "QBit3", "QBit5", "QBit7", "QBit9", 
    "CBit4", "CBit6", "CBit8", "CBit9", "CBit10", 
    "SonoPort8", "XBit80", "Xbit90", "SonoMax7", "SonoMax9", 
    "Otro / Particular"
]

# --- ESTADO DE SESIÓN ---
if 'logeado' not in st.session_state:
    st.session_state['logeado'] = False
    st.session_state['usuario'] = ""
    st.session_state['rol'] = ""

if 'serie_key' not in st.session_state:
    st.session_state['serie_key'] = 0

# --- LÓGICA DE LOGIN ---
def iniciar_sesion(usuario, password):
    df_usuarios = conn_servicio.read(worksheet="Usuarios", ttl=0).dropna(how='all')
    df_usuarios['Usuario'] = df_usuarios['Usuario'].astype(str).str.strip()
    df_usuarios['Password'] = df_usuarios['Password'].astype(str).str.strip()
    
    usuario_valido = df_usuarios[(df_usuarios['Usuario'] == usuario.strip()) & 
                                 (df_usuarios['Password'] == str(password).strip())]
    
    if not usuario_valido.empty:
        st.session_state['logeado'] = True
        st.session_state['usuario'] = usuario.strip()
        st.session_state['rol'] = str(usuario_valido.iloc[0]['Rol']).strip()
        st.rerun()
    else:
        st.error("Usuario o contraseña incorrectos.")

if not st.session_state['logeado']:
    st.title("🔐 Acceso al Sistema CRM")
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            iniciar_sesion(u, p)
    st.stop()

# --- FUNCIONES ---
def limpiar_serie(valor):
    val_str = str(valor).strip()
    return val_str[:-2] if val_str.endswith('.0') else val_str

def eliminar_registro(conexion, df, id_a_borrar):
    df_nuevo = df[df['ID'] != id_a_borrar].copy()
    conexion.update(data=df_nuevo)
    st.cache_data.clear()

# --- MENÚ ---
MENU_SERV = "🔧 Servicio Técnico"
MENU_MKT = "📈 Marketing"
MENU_USR = "⚙️ Panel de Usuarios"

opciones = [MENU_SERV, MENU_MKT]
if st.session_state['rol'] == 'Admin': opciones.append(MENU_USR)
division = st.sidebar.radio("División:", opciones)

# --- MARKETING ---
if division == MENU_MKT:
    st.header("Gestión de Préstamos")
    df_marketing = conn_marketing.read(ttl=0)
    
    hoy = date.today()
    
    # Formulario Registro
    with st.expander("➕ Registrar Préstamo"):
        with st.form("nvo_mkt", clear_on_submit=True):
            kol = st.text_input("KOL")
            equipo_sel = st.selectbox("Equipo", LISTA_EQUIPOS)
            num_serie = st.text_input("Número de Serie")
            f_inicio = st.date_input("Inicio")
            f_fin = st.date_input("Devolución Física")
            dias_lic = st.number_input("Días de Licencia Inicial", value=12)
            
            if st.form_submit_button("Guardar"):
                venc_lic = f_inicio + timedelta(days=dias_lic)
                nuevo_id = int(df_marketing['ID'].max() + 1) if not df_marketing.empty else 1
                nuevo = pd.DataFrame([{"ID": nuevo_id, "KOL": kol, "Equipo": equipo_sel, "Numero de serie": num_serie, 
                                     "Dias de licencia": str((venc_lic - hoy).days), "Vencimiento Licencia": str(venc_lic),
                                     "Fecha de inicio": str(f_inicio), "Fecha de finalizacion": str(f_fin), "Estado": "Activo"}])
                conn_marketing.update(data=pd.concat([df_marketing, nuevo], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

    # Tabla y Gestión
    if not df_marketing.empty:
        st.dataframe(df_marketing, use_container_width=True)
        id_sel = st.selectbox("Selecciona ID para Gestión:", df_marketing['ID'].unique())
        
        col1, col2 = st.columns(2)
        with col1:
            dias_sumar = st.number_input("Días extra", value=30)
            if st.button("🔑 Sumar a Licencia"):
                idx = df_marketing.index[df_marketing['ID'] == id_sel].tolist()[0]
                venc_act = datetime.strptime(str(df_marketing.at[idx, 'Vencimiento Licencia']), '%Y-%m-%d').date()
                nueva_venc = venc_act + timedelta(days=dias_sumar)
                df_marketing.at[idx, 'Vencimiento Licencia'] = str(nueva_venc)
                df_marketing.at[idx, 'Dias de licencia'] = str((nueva_venc - hoy).days)
                conn_marketing.update(data=df_marketing)
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            if st.button("✅ Finalizar"):
                idx = df_marketing.index[df_marketing['ID'] == id_sel].tolist()[0]
                df_marketing.at[idx, 'Estado'] = 'Finalizado'
                conn_marketing.update(data=df_marketing)
                st.cache_data.clear()
                st.rerun()
