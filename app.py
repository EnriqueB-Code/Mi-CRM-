import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión", layout="wide")
st.title("Panel de Control Sincronizado")

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)
    conn_marketing = st.connection("gsheets_marketing", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión. Verifica tus Secrets. Detalle: {e}")
    st.stop()

# Menú lateral
division = st.sidebar.radio("Selecciona la División:", ["🔧 Servicio Técnico", "📈 Marketing"])

# Funciones de utilidad
def preparar_df(df, columnas):
    if df.empty:
        df = pd.DataFrame(columns=columnas)
    else:
        df = df.dropna(how='all')
    
    for col in columnas:
        if col not in df.columns:
            df[col] = ""
            
    if not df.empty and 'ID' in df.columns:
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce').fillna(0).astype(int)
    return df

def color_filas(row):
    estado = str(row.get('Estatus', row.get('Estado', ''))).strip()
    if estado == 'Finalizado':
        return ['background-color: #d4edda; color: #155724;'] * len(row)
    elif estado == 'Sin Seguimiento (Alerta)':
        return ['background-color: #f8d7da; color: #721c24;'] * len(row)
    return [''] * len(row)


# ==========================================
# DIVISIÓN: SERVICIO TÉCNICO
# ==========================================
if division == "🔧 Servicio Técnico":
    st.header("Gestión de Servicio")
    
    cols_servicio = ["ID", "Cliente", "Caso reportado", "Modelo", "Numero de serie", 
                     "Seguimiento con fabrica", "Solucion del problema", 
                     "Fecha de reporte", "Fecha de cierre", "Estatus"]
    
    df_servicio = conn_servicio.read(ttl=0)
    df_servicio = preparar_df(df_servicio, cols_servicio)
    df_servicio = df_servicio.fillna("")

    # 1. ALERTA DE 3 DÍAS SIN SEGUIMIENTO
    hoy = date.today()
    hubo_cambios_estado = False
    
    if not df_servicio.empty:
        for index, row in df_servicio.iterrows():
            if str(row['Estatus']) != 'Finalizado':
                try:
                    fecha_rep = datetime.strptime(str(row['Fecha de reporte']), '%Y-%m-%d').date()
                    dias_pasados = (hoy - fecha_rep).days
                    seguimiento = str(row['Seguimiento con fabrica']).strip()
                    
                    # Si pasaron >= 3 días y el seguimiento está vacío
                    if dias_pasados >= 3 and seguimiento == "":
                        st.error(f"🚨 **ALERTA DE SEGUIMIENTO:** El caso ID {row['ID']} (Serie: {row['Numero de serie']}) lleva {dias_pasados} días sin seguimiento.")
                        if str(row['Estatus']) != 'Sin Seguimiento (Alerta)':
                            df_servicio.at[index, 'Estatus'] = 'Sin Seguimiento (Alerta)'
                            hubo_cambios_estado = True
                    # Si ya tiene seguimiento y estaba en alerta, lo regresamos a Activo
                    elif seguimiento != "" and str(row['Estatus']) == 'Sin Seguimiento (Alerta)':
                        df_servicio.at[index, 'Estatus'] = 'Activo'
                        hubo_cambios_estado = True
                except ValueError:
                    pass # Ignorar si la fecha tiene formato incorrecto
        
        if hubo_cambios_estado:
            conn_servicio.update(data=df_servicio)

    # 2. FORMULARIO DE REGISTRO / ACTUALIZACIÓN
    with st.expander("➕ Registrar o Actualizar Caso", expanded=True):
        num_serie = st.text_input("🔍 Ingresa el Número de Serie del Equipo:")
        
        if num_serie:
            num_serie_str = str(num_serie).strip()
            coincidencias = df_servicio[df_servicio['Numero de serie'].astype(str) == num_serie_str]
            
            if not coincidencias.empty:
                st.warning(f"⚠️ El equipo con serie '{num_serie_str}' ya tiene reportes en el sistema.")
                
                # Menú para agregar seguimiento a caso existente
                id_actualizar = st.selectbox("Selecciona el ID del caso para agregar seguimiento:", coincidencias['ID'].unique())
                nuevo_seguimiento = st.text_area("Agregar reporte/seguimiento nuevo:")
                
                if st.button("📝 Guardar Seguimiento"):
                    idx = df_servicio.index[df_servicio['ID'] == id_actualizar].tolist()[0]
                    seg_actual = str(df_servicio.at[idx, 'Seguimiento con fabrica'])
                    texto_final = f"{seg_actual}\n[{hoy}] {nuevo_seguimiento}".strip() if seg_actual else f"[{hoy}] {nuevo_seguimiento}"
                    
                    df_servicio.at[idx, 'Seguimiento con fabrica'] = texto_final
                    df_servicio.at[idx, 'Estatus'] = 'Activo' # Quita la alerta si la tuviera
                    conn_servicio.update(data=df_servicio)
                    st.success("Seguimiento agregado exitosamente.")
                    st.rerun()
                    
                st.markdown("---")
                st.write("**O si prefieres, abre un caso completamente nuevo para este equipo:**")
            
            # Formulario para caso nuevo
            with st.form("nuevo_caso", clear_on_submit=True):
                cliente = st.text_input("Cliente")
                modelo = st.text_input("Modelo del Equipo")
                caso = st.text_area("Caso Reportado")
                fecha_reporte = st.date_input("Fecha de Reporte")
                
                if st.form_submit_button("Guardar Nuevo Caso"):
                    nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                    nuevo_registro = pd.DataFrame([{
                        "ID": nuevo_id, "Cliente": cliente, "Caso reportado": caso, 
                        "Modelo": modelo, "Numero de serie": num_serie_str,
                        "Seguimiento con fabrica": "", "Solucion del problema": "",
                        "Fecha de reporte": str(fecha_reporte), "Fecha de cierre": "", "Estatus": "Activo"
                    }])
                    df_actualizado = pd.concat([df_servicio, nuevo_registro], ignore_index=True)
                    conn_servicio.update(data=df_actualizado)
                    st.success("Caso registrado con éxito.")
                    st.rerun()

    # 3. TABLA Y GESTIÓN DE BOTONES
    st.subheader("Casos Registrados")
    if not df_servicio.empty:
        st.dataframe(df_servicio.style.apply(color_filas, axis=1), use_container_width=True)
        
        st.write("### ⚙️ Gestionar Casos Existentes")
        col_sel, col_fin, col_del = st.columns([2, 1, 1])
        with col_sel:
            id_gestion = st.selectbox("Selecciona ID:", df_servicio['ID'].unique(), key="gest_serv")
        with col_fin:
            st.write("") # Espaciador
            st.write("")
            if st.button("✅ Finalizar Caso"):
                idx = df_servicio.index[df_servicio['ID'] == id_gestion].tolist()[0]
                df_servicio.at[idx, 'Estatus'] = 'Finalizado'
                df_servicio.at[idx, 'Fecha de cierre'] = str(hoy)
                conn_servicio.update(data=df_servicio)
                st.success(f"Caso {id_gestion} finalizado.")
                st.rerun()
        with col_del:
            st.write("")
            st.write("")
            if st.button("🗑️ Borrar Caso"):
                df_servicio = df_servicio[df_servicio['ID'] != id_gestion]
                conn_servicio.update(data=df_servicio)
                st.success(f"Caso {id_gestion} eliminado.")
                st.rerun()
    else:
        st.info("No hay casos registrados.")


# ==========================================
# DIVISIÓN: MARKETING
# ==========================================
elif division == "📈 Marketing":
    st.header("Gestión de Préstamos (KOL)")
    
    cols_mkt = ["ID", "KOL", "Lugar de prestamo", "Equipo", "Dias de licencia", 
                "Fecha de inicio", "Fecha de finalizacion", "Estado"]
    
    df_marketing = conn_marketing.read(ttl=0)
    df_marketing = preparar_df(df_marketing, cols_mkt)
    df_marketing = df_marketing.fillna("")

    # 1. RECORDATORIOS DE 5 DÍAS
    hoy = date.today()
    if not df_marketing.empty:
        for index, row in df_marketing.iterrows():
            if str(row['Estado']) != 'Finalizado' and str(row['Fecha de finalizacion']) != "":
                try:
                    fecha_fin = datetime.strptime(str(row['Fecha de finalizacion']), '%Y-%m-%d').date()
                    dias_restantes = (fecha_fin - hoy).days
                    
                    if 0 <= dias_restantes <= 5:
                        st.warning(f"⚠️ **VENCIMIENTO PRÓXIMO:** La licencia del equipo '{row['Equipo']}' prestado a '{row['KOL']}' finaliza en {dias_restantes} días (Fecha: {row['Fecha de finalizacion']}).")
                    elif dias_restantes < 0:
                        st.error(f"❌ **VENCIDO:** El préstamo a '{row['KOL']}' expiró hace {abs(dias_restantes)} días.")
                except ValueError:
                    pass

    # 2. FORMULARIO DE REGISTRO
    with st.expander("➕ Registrar Nuevo Préstamo", expanded=True):
        with st.form("nuevo_prestamo", clear_on_submit=True):
            kol = st.text_input("Nombre del KOL")
            lugar = st.text_input("Lugar de Préstamo del Equipo")
            equipo = st.text_input("Equipo a Préstamo")
            
            c1, c2 = st.columns(2)
            with c1:
                f_inicio = st.date_input("Fecha de Inicio")
            with c2:
                f_fin = st.date_input("Fecha de Finalización")
            
            if st.form_submit_button("Guardar Préstamo"):
                dias_licencia = (f_fin - f_inicio).days
                if dias_licencia < 0:
                    st.error("Error: La fecha final no puede ser menor a la inicial.")
                else:
                    nuevo_id = int(df_marketing['ID'].max() + 1) if not df_marketing.empty else 1
                    nuevo_reg = pd.DataFrame([{
                        "ID": nuevo_id, "KOL": kol, "Lugar de prestamo": lugar, 
                        "Equipo": equipo, "Dias de licencia": dias_licencia,
                        "Fecha de inicio": str(f_inicio), "Fecha de finalizacion": str(f_fin), "Estado": "Activo"
                    }])
                    df_actualizado = pd.concat([df_marketing, nuevo_reg], ignore_index=True)
                    conn_marketing.update(data=df_actualizado)
                    st.success("Préstamo registrado exitosamente.")
                    st.rerun()

    # 3. TABLA Y GESTIÓN DE BOTONES
    st.subheader("Equipos en Préstamo Registrados")
    if not df_marketing.empty:
        st.dataframe(df_marketing.style.apply(color_filas, axis=1), use_container_width=True)
        
        st.write("### ⚙️ Gestionar Préstamos Existentes")
        col_sel_m, col_fin_m, col_del_m = st.columns([2, 1, 1])
        with col_sel_m:
            id_mkt = st.selectbox("Selecciona ID:", df_marketing['ID'].unique(), key="gest_mkt")
        with col_fin_m:
            st.write("")
            st.write("")
            if st.button("✅ Finalizar Préstamo"):
                idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                df_marketing.at[idx, 'Estado'] = 'Finalizado'
                conn_marketing.update(data=df_marketing)
                st.success(f"Préstamo {id_mkt} finalizado.")
                st.rerun()
        with col_del_m:
            st.write("")
            st.write("")
            if st.button("🗑️ Borrar Préstamo"):
                df_marketing = df_marketing[df_marketing['ID'] != id_mkt]
                conn_marketing.update(data=df_marketing)
                st.success(f"Préstamo {id_mkt} eliminado.")
                st.rerun()
    else:
        st.info("No hay préstamos registrados.")
