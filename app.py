import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="CRM Enrique", layout="wide")

try:
    conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)
    conn_marketing = st.connection("gsheets_marketing", type=GSheetsConnection)
except:
    st.error("Error de conexión.")
    st.stop()

# --- LISTA MAESTRA ---
LISTA_EQUIPOS = ["SonoEye P1", "SonoEye P2", "SonoEye P3", "SonoEye P5", "SonoEye P6", "ECO1", "ECO2", "ECO3 EXP", "ECO5", "ECO6", "EBit20", "EBit30", "EBit50", "EBit60", "SonoAir20","SonoAir30","SonoAir60","SonoAir70", "SonoBook6", "SonoBook7", "SonoBook8", "SonoBook9", "QBit3", "QBit5", "QBit7", "QBit9", "CBit4", "CBit6", "CBit8", "CBit9", "CBit10", "SonoPort8", "XBit80", "Xbit90", "SonoMax7", "SonoMax9", "Otro / Particular"]

# --- LOGIN ---
if 'logeado' not in st.session_state: st.session_state.update({'logeado': False, 'usuario': "", 'rol': "", 'serie_key': 0})

def login(u, p):
    df = conn_servicio.read(worksheet="Usuarios", ttl=0).dropna(how='all')
    user = df[(df['Usuario'].astype(str).str.strip() == u.strip()) & (df['Password'].astype(str).str.strip() == str(p).strip())]
    if not user.empty:
        st.session_state.update({'logeado': True, 'usuario': u.strip(), 'rol': str(user.iloc[0]['Rol']).strip()})
        st.rerun()
    else: st.error("❌ Credenciales incorrectas")

if not st.session_state.logeado:
    st.title("🔐 Acceso")
    with st.form("login"):
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"): login(u, p)
    st.stop()

# --- FUNCIONES ---
def limpiar_serie(v): return str(v).strip()[:-2] if str(v).strip().endswith('.0') else str(v).strip()

# --- MENÚ ---
MENU_SERV, MENU_MKT, MENU_USR = "🔧 Servicio", "📈 Marketing", "⚙️ Usuarios"
opciones = [MENU_SERV, MENU_MKT]
if st.session_state.rol == 'Admin': opciones.append(MENU_USR)
division = st.sidebar.radio("División:", opciones)

# --- SERVICIO ---
if division == MENU_SERV:
    st.header("Servicio Técnico")
    df = conn_servicio.read(ttl=0).fillna("")
    if not df.empty: df['Numero de serie'] = df['Numero de serie'].apply(limpiar_serie)
    
    with st.expander("➕ Nuevo Caso"):
        with st.form("nvo_caso", clear_on_submit=True):
            ns = st.text_input("Serie", key=f"s_{st.session_state.serie_key}")
            cl = st.text_input("Cliente"); mod = st.selectbox("Modelo", LISTA_EQUIPOS); mod_o = st.text_input("Otro modelo")
            caso = st.text_area("Caso"); f_rep = st.date_input("Fecha")
            if st.form_submit_button("Guardar"):
                nuevo = pd.DataFrame([{"ID": int(df['ID'].max()+1) if not df.empty else 1, "Cliente": cl, "Modelo": (mod_o if mod=="Otro / Particular" else mod), "Numero de serie": ns, "Caso reportado": caso, "Fecha de reporte": str(f_rep), "Estatus": "Activo"}])
                conn_servicio.update(data=pd.concat([df, nuevo], ignore_index=True))
                st.session_state.serie_key += 1; st.rerun()
    st.dataframe(df)

# --- MARKETING ---
elif division == MENU_MKT:
    st.header("Gestión de Préstamos")
    df = conn_marketing.read(ttl=0).fillna("")
    hoy = date.today()
    
    with st.expander("➕ Registrar Préstamo"):
        with st.form("nvo_mkt", clear_on_submit=True):
            kol = st.text_input("KOL"); eq = st.selectbox("Equipo", LISTA_EQUIPOS); eq_o = st.text_input("Otro equipo")
            ns = st.text_input("Serie"); f_ini = st.date_input("Inicio"); f_fin = st.date_input("Devolución Física")
            dias_lic = st.number_input("Días de Licencia Inicial", value=12)
            if st.form_submit_button("Guardar"):
                venc_lic = f_ini + timedelta(days=dias_lic)
                nuevo = pd.DataFrame([{"ID": int(df['ID'].max()+1) if not df.empty else 1, "KOL": kol, "Equipo": (eq_o if eq=="Otro / Particular" else eq), "Numero de serie": ns, "Dias de licencia": str((venc_lic - hoy).days), "Vencimiento Licencia": str(venc_lic), "Fecha de inicio": str(f_ini), "Fecha de finalizacion": str(f_fin), "Estado": "Activo"}])
                conn_marketing.update(data=pd.concat([df, nuevo], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    if not df.empty:
        st.dataframe(df)
        id_sel = st.selectbox("ID a Gestionar:", df['ID'].unique())
        if st.button("🔑 Sumar 30 días a Licencia"):
            idx = df.index[df['ID'] == id_sel].tolist()[0]
            venc_act = datetime.strptime(str(df.at[idx, 'Vencimiento Licencia']), '%Y-%m-%d').date()
            nueva_venc = venc_act + timedelta(days=30)
            df.at[idx, 'Vencimiento Licencia'] = str(nueva_venc)
            df.at[idx, 'Dias de licencia'] = str((nueva_venc - hoy).days)
            conn_marketing.update(data=df); st.cache_data.clear(); st.rerun()
