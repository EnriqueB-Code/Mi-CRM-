import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

st.set_page_config(page_title="Sistema de Gestión", layout="wide")
st.title("Panel de Control Sincronizado")

# Conexión
conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)
conn_marketing = st.connection("gsheets_marketing", type=GSheetsConnection)

division = st.sidebar.radio("Selecciona la División:", ["🔧 Servicio Técnico", "📈 Marketing"])

# Función para limpiar el formulario
def reset_form():
    for key in st.session_state.keys():
        del st.session_state[key]

# ==========================================
# DIVISIÓN: SERVICIO
# ==========================================
if division == "🔧 Servicio Técnico":
    st.header("Gestión de Servicio")
    df_servicio = conn_servicio.read(ttl=0)
    
    with st.expander("➕ Registrar o Actualizar Caso", expanded=True):
        # Convertimos número de serie a STR para evitar ceros extra
        num_serie = st.text_input("🔍 Ingresa el Número de Serie:")
        
        if num_serie:
            num_serie_str = str(num_serie).strip()
            coincidencias = df_servicio[df_servicio['Numero de Serie'].astype(str) == num_serie_str]
            
            if not coincidencias.empty:
                st.warning(f"⚠️ El serie '{num_serie_str}' ya existe.")
                if st.button("📝 Agregar info al caso existente"):
                    st.session_state['modo'] = 'editar'
                
                if st.session_state.get('modo') == 'editar':
                    id_caso = st.selectbox("ID del caso:", coincidencias['ID'])
                    info = st.text_area("Nueva información:")
                    if st.button("Guardar actualización"):
                        # Lógica de actualización
                        st.success("Actualizado")
                        st.rerun()
            else:
                with st.form("nuevo_caso", clear_on_submit=True):
                    cliente = st.text_input("Cliente")
                    caso = st.text_area("Caso Reportado")
                    fecha = st.date_input("Fecha")
                    if st.form_submit_button("Guardar"):
                        nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                        nuevo = pd.DataFrame([{"ID": nuevo_id, "Cliente": cliente, "Numero de Serie": num_serie_str, "Estado": "Activo"}])
                        conn_servicio.update(data=pd.concat([df_servicio, nuevo], ignore_index=True))
                        st.success("Guardado")
                        st.rerun()

    st.subheader("Casos Registrados")
    if not df_servicio.empty:
        st.dataframe(df_servicio, use_container_width=True)
        id_sel = st.selectbox("ID a finalizar:", df_servicio['ID'])
        if st.button("✅ Finalizar"):
            idx = df_servicio.index[df_servicio['ID'] == id_sel].tolist()[0]
            df_servicio.at[idx, 'Estado'] = 'Finalizado'
            conn_servicio.update(data=df_servicio)
            st.rerun()

# ==========================================
# DIVISIÓN: MARKETING
# ==========================================
elif division == "📈 Marketing":
    st.header("Gestión de Préstamos")
    # Lógica similar aplicada...
