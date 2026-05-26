import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

st.set_page_config(page_title="Sistema de Gestión", layout="wide")
st.title("Panel de Control en la Nube (Google Sheets)")

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn_servicio = st.connection("gsheets_servicio", type=GSheetsConnection)
    conn_marketing = st.connection("gsheets_marketing", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión. Asegúrate de configurar los Secrets en Streamlit Cloud. Detalle: {e}")
    st.stop()

# Menú lateral
division = st.sidebar.radio("Selecciona la División:", ["🔧 Servicio Técnico", "📈 Marketing"])

# Función para asegurar que existan las columnas clave y limpiar datos vacíos
def preparar_dataframe(df, columnas_requeridas):
    if df.empty:
        df = pd.DataFrame(columns=columnas_requeridas)
    else:
        # Eliminar filas completamente vacías si las hay
        df = df.dropna(how='all')
    
    if 'Estado' not in df.columns:
        df['Estado'] = 'Activo'
    
    # Asegurar que el ID sea numérico
    if not df.empty:
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce').fillna(0).astype(int)
    return df

# Función para colorear las filas de verde si están finalizadas
def color_filas(row):
    color = 'background-color: #d4edda; color: #155724;' if str(row.get('Estado')).strip() == 'Finalizado' else ''
    return [color] * len(row)

# ==========================================
# DIVISIÓN: SERVICIO
# ==========================================
if division == "🔧 Servicio Técnico":
    st.header("Gestión de Servicio")
    
    cols_servicio = ["ID", "Cliente", "Caso Reportado", "Fecha de Reporte", "Numero de Serie", "Seguimiento Fabrica", "Solucion", "Fecha de Cierre", "Estado"]
    df_servicio = conn_servicio.read(ttl=0)
    df_servicio = preparar_dataframe(df_servicio, cols_servicio)
    
    with st.expander("➕ Registrar o Actualizar Caso", expanded=True):
        num_serie = st.text_input("🔍 Ingresa el Número de Serie del Equipo:")
        
        if num_serie:
            # Buscar si ya existe este número de serie
            coincidencias = df_servicio[df_servicio['Numero de Serie'].astype(str) == str(num_serie)]
            
            if not isinstance(coincidencias, pd.DataFrame) or not coincidencias.empty:
                st.warning(f"⚠️ ¡Alerta! El número de serie '{num_serie}' ya cuenta con reportes previos.")
                accion = st.radio("¿Qué deseas hacer?", ["📝 Agregar información al reporte activo", "🆕 Crear un reporte nuevo completamente"])
                
                if accion == "📝 Agregar información al reporte activo":
                    id_caso = st.selectbox("Selecciona el ID del caso a actualizar:", coincidencias['ID'].unique())
                    info_adicional = st.text_area("Nueva información / Actualización para agregar:")
                    
                    if st.button("Actualizar Reporte"):
                        idx = df_servicio.index[df_servicio['ID'] == id_caso].tolist()[0]
                        seg_actual = str(df_servicio.at[idx, 'Seguimiento Fabrica'])
                        if seg_actual.lower() == 'nan': seg_actual = ""
                        
                        nuevo_texto = f"{seg_actual}\n[{date.today()}] Nuevo reporte: {info_adicional}".strip()
                        df_servicio.at[idx, 'Seguimiento Fabrica'] = nuevo_texto
                        
                        conn_servicio.update(data=df_servicio)
                        st.success("¡Reporte actualizado con éxito en Google Sheets!")
                        st.rerun()
                else:
                    # Crear nuevo reporte compartiendo el mismo número de serie
                    cliente = st.text_input("Cliente")
                    caso = st.text_area("Caso Reportado")
                    fecha_reporte = st.date_input("Fecha de Reporte")
                    seguimiento = st.text_area("Seguimiento con Fábrica")
                    solucion = st.text_area("Solución del Problema")
                    
                    if st.button("Guardar Nuevo Registro"):
                        nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                        nuevo_registro = pd.DataFrame([{
                            "ID": nuevo_id, "Cliente": cliente, "Caso Reportado": caso,
                            "Fecha de Reporte": str(fecha_reporte), "Numero de Serie": num_serie,
                            "Seguimiento Fabrica": seguimiento, "Solucion": solucion,
                            "Fecha de Cierre": "", "Estado": "Activo"
                        }])
                        df_actualizado = pd.concat([df_servicio, nuevo_registro], ignore_index=True)
                        conn_servicio.update(data=df_actualizado)
                        st.success("¡Nuevo caso registrado exitosamente!")
                        st.rerun()
            else:
                # Flujo normal si el número de serie es nuevo
                cliente = st.text_input("Cliente")
                caso = st.text_area("Caso Reportado")
                fecha_reporte = st.date_input("Fecha de Reporte")
                seguimiento = st.text_area("Seguimiento con Fábrica")
                solucion = st.text_area("Solución del Problema")
                
                if st.button("Guardar Registro"):
                    nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                    nuevo_registro = pd.DataFrame([{
                        "ID": nuevo_id, "Cliente": cliente, "Caso Reportado": caso,
                        "Fecha de Reporte": str(fecha_reporte), "Numero de Serie": num_serie,
                        "Seguimiento Fabrica": seguimiento, "Solucion": solucion,
                        "Fecha de Cierre": "", "Estado": "Activo"
                    }])
                    df_actualizado = pd.concat([df_servicio, nuevo_registro], ignore_index=True)
                    conn_servicio.update(data=df_actualizado)
                    st.success("¡Caso guardado correctamente!")
                    st.rerun()

    st.subheader("Casos Registrados")
    if not df_servicio.empty:
        # Mostrar tabla estilizada con colores
        st.dataframe(df_servicio.style.apply(color_filas, axis=1), use_container_width=True)
        
        st.markdown("---")
        st.write("### ⚙️ Gestión de Registros")
        id_seleccionado = st.selectbox("Selecciona el ID del registro a modificar:", df_servicio['ID'].unique(), key="sel_serv")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Marcar como Finalizado", key="fin_serv"):
                idx = df_servicio.index[df_servicio['ID'] == id_seleccionado].tolist()[0]
                df_servicio.at[idx, 'Estado'] = 'Finalizado'
                df_servicio.at[idx, 'Fecha de Cierre'] = str(date.today())
                conn_servicio.update(data=df_servicio)
                st.success(f"Registro {id_seleccionado} marcado como finalizado.")
                st.rerun()
        with col2:
            if st.button("🗑️ Eliminar Registro", key="del_serv"):
                df_servicio = df_servicio[df_servicio['ID'] != id_seleccionado]
                conn_servicio.update(data=df_servicio)
                st.success(f"Registro {id_seleccionado} eliminado permanentemente.")
                st.rerun()
    else:
        st.info("No hay casos registrados en la nube.")

# ==========================================
# DIVISIÓN: MARKETING
# ==========================================
elif division == "📈 Marketing":
    st.header("Gestión de Préstamos (KOL)")
    
    cols_marketing = ["ID", "KOL", "Lugar de Prestamo", "Equipo a Prestamo", "Fecha de Inicio", "Fecha de Finalizacion", "Dias de Uso", "Estado"]
    df_marketing = conn_marketing.read(ttl=0)
    df_marketing = preparar_dataframe(df_marketing, cols_marketing)
    
    with st.expander("➕ Registrar Nuevo Préstamo"):
        kol = st.text_input("Nombre del KOL")
        lugar = st.text_input("Lugar de Préstamo del Equipo")
        equipo = st.text_input("Equipo a Préstamo")
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha de Inicio")
        with col2:
            fecha_fin = st.date_input("Fecha de Finalización")
        
        if st.button("Guardar Préstamo"):
            dias_uso = (fecha_fin - fecha_inicio).days
            if dias_uso < 0:
                st.error("La fecha de finalización no puede ser menor a la de inicio.")
            else:
                nuevo_id = int(df_marketing['ID'].max() + 1) if not df_marketing.empty else 1
                nuevo_registro = pd.DataFrame([{
                    "ID": nuevo_id, "KOL": kol, "Lugar de Prestamo": lugar,
                    "Equipo a Prestamo": equipo, "Fecha de Inicio": str(fecha_inicio),
                    "Fecha de Finalizacion": str(fecha_fin), "Dias de Uso": dias_uso,
                    "Estado": "Activo"
                }])
                df_actualizado = pd.concat([df_marketing, nuevo_registro], ignore_index=True)
                conn_marketing.update(data=df_actualizado)
                st.success(f"¡Préstamo registrado en la nube! Días de uso: {dias_uso}")
                st.rerun()

    st.subheader("Equipos en Préstamo y Recordatorios")
    
    if not df_marketing.empty:
        hoy = date.today()
        for index, row in df_marketing.iterrows():
            if str(row.get('Estado')).strip() != 'Finalizado':
                if pd.isna(row.get('Fecha de Finalizacion')) or str(row.get('Fecha de Finalizacion')) == "":
                    continue
                try:
                    fecha_fin_dt = datetime.strptime(str(row['Fecha de Finalizacion']).strip(), '%Y-%m-%d').date()
                    dias_restantes = (fecha_fin_dt - hoy).days
                    
                    if 0 <= dias_restantes <= 5:
                        st.warning(f"⚠️ **RECORDATORIO:** El préstamo de '{row['Equipo a Prestamo']}' a '{row['KOL']}' vence en {dias_restantes} días.")
                    elif dias_restantes < 0:
                        st.error(f"❌ **VENCIDO:** El préstamo a '{row['KOL']}' terminó hace {abs(dias_restantes)} días.")
                except Exception:
                    pass
        
        st.dataframe(df_marketing.style.apply(color_filas, axis=1), use_container_width=True)
        
        st.markdown("---")
        st.write("### ⚙️ Gestión de Registros")
        id_mkt_seleccionado = st.selectbox("Selecciona el ID del préstamo a modificar:", df_marketing['ID'].unique(), key="sel_mkt")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Marcar como Finalizado", key="fin_mkt"):
                idx = df_marketing.index[df_marketing['ID'] == id_mkt_seleccionado].tolist()[0]
                df_marketing.at[idx, 'Estado'] = 'Finalizado'
                conn_marketing.update(data=df_marketing)
                st.success(f"Préstamo {id_mkt_seleccionado} finalizado con éxito.")
                st.rerun()
        with col2:
            if st.button("🗑️ Eliminar Registro", key="del_mkt"):
                df_marketing = df_marketing[df_marketing['ID'] != id_mkt_seleccionado]
                conn_marketing.update(data=df_marketing)
                st.success(f"Registro {id_mkt_seleccionado} eliminado permanentemente.")
                st.rerun()
    else:
        st.info("No hay préstamos registrados aún.")
