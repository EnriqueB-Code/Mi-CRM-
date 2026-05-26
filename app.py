import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración
st.set_page_config(page_title="Gestión", layout="wide")
conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)

# Inicializar estado para limpiar formularios
if 'form_key' not in st.session_state:
    st.session_state['form_key'] = 0

def incrementar_key():
    st.session_state['form_key'] += 1

st.title("Panel de Control")

# --- SECCIÓN SERVICIO ---
st.header("🔧 Servicio Técnico")
df_servicio = conn_servicio.read(ttl=0)

# Formulario de Registro
with st.container(border=True):
    st.subheader("Nuevo Registro")
    with st.form(key=f"form_{st.session_state['form_key']}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Cliente")
        serie = col2.text_input("Número de Serie") # Lo leerá como texto puro
        caso = st.text_area("Descripción del Caso")
        
        submit = st.form_submit_button("Guardar Caso")
        if submit:
            nueva_fila = pd.DataFrame([{"ID": len(df_servicio)+1, "Cliente": cliente, "Numero de Serie": str(serie), "Caso": caso, "Estado": "Activo"}])
            conn_servicio.update(data=pd.concat([df_servicio, nueva_fila], ignore_index=True))
            st.success("Guardado con éxito")
            incrementar_key() # Esto fuerza que el formulario se resetee
            st.rerun()

# --- SECCIÓN ELIMINACIÓN ---
st.subheader("Gestión de Registros")
if not df_servicio.empty:
    st.dataframe(df_servicio, use_container_width=True)
    
    # Selección para eliminar
    id_a_borrar = st.selectbox("Selecciona el ID para ELIMINAR:", df_servicio['ID'].tolist())
    
    if st.button("🗑️ Eliminar Registro Seleccionado"):
        df_nuevo = df_servicio[df_servicio['ID'] != id_a_borrar]
        conn_servicio.update(data=df_nuevo)
        st.warning(f"Registro {id_a_borrar} eliminado.")
        st.rerun()
else:
    st.info("No hay registros disponibles.")
