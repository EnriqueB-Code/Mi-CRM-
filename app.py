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
    st.error(f"Error de conexión. Verifica tus Secrets. Detalle: {e}")
    st.stop()

# ==========================================
# LISTA MAESTRA DE EQUIPOS
# ==========================================
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

# ==========================================
# SISTEMA DE LOGIN Y ESTADO
# ==========================================
if 'logeado' not in st.session_state:
    st.session_state['logeado'] = False
    st.session_state['usuario'] = ""
    st.session_state['rol'] = ""

if 'serie_key' not in st.session_state:
    st.session_state['serie_key'] = 0

def iniciar_sesion(usuario, password):
    try:
        df_usuarios = conn_servicio.read(worksheet="Usuarios", ttl=0).dropna(how='all')
    except Exception:
        st.error("⚠️ No se encontró la pestaña 'Usuarios' en tu Excel de Servicio Técnico.")
        return
        
    df_usuarios['Usuario'] = df_usuarios['Usuario'].astype(str).str.strip()
    df_usuarios['Password'] = df_usuarios['Password'].astype(str).str.strip()
    df_usuarios['Password'] = df_usuarios['Password'].apply(lambda x: x[:-2] if x.endswith('.0') else x)
    
    user_limpio = str(usuario).strip()
    pass_limpia = str(password).strip()

    usuario_valido = df_usuarios[(df_usuarios['Usuario'] == user_limpio) & 
                                 (df_usuarios['Password'] == pass_limpia)]
    
    if not usuario_valido.empty:
        st.session_state['logeado'] = True
        st.session_state['usuario'] = user_limpio
        st.session_state['rol'] = str(usuario_valido.iloc[0]['Rol']).strip()
        st.rerun()
    else:
        st.error("❌ Usuario o contraseña incorrectos.")

if not st.session_state['logeado']:
    st.title("🔐 Acceso al Sistema CRM")
    with st.form("login_form"):
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            iniciar_sesion(user_input, pass_input)
    st.stop()

# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================
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

def limpiar_serie(valor):
    val_str = str(valor).strip()
    return val_str[:-2] if val_str.endswith('.0') else val_str

def limpiar_decimales(valor):
    try:
        return str(int(float(valor)))
    except (ValueError, TypeError):
        return str(valor).strip()

def eliminar_registro_gsheets(conexion, df_original, id_a_borrar):
    df_nuevo = df_original[df_original['ID'] != id_a_borrar].copy()
    diferencia = len(df_original) - len(df_nuevo)
    if diferencia > 0:
        filas_vacias = pd.DataFrame([[""] * len(df_original.columns)] * diferencia, columns=df_original.columns)
        df_escritura = pd.concat([df_nuevo, filas_vacias], ignore_index=True)
        conexion.update(data=df_escritura)
    else:
        conexion.update(data=df_nuevo)

# Nombres estables de menú
MENU_SERV = "🔧 Servicio Técnico"
MENU_MKT = "📈 Marketing"
MENU_USR = "⚙️ Panel de Usuarios"

# ==========================================
# MENÚ PRINCIPAL LATERAL
# ==========================================
st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['usuario']}")
st.sidebar.markdown(f"🛡️ **Rol:** {st.session_state['rol']}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['logeado'] = False
    st.rerun()

st.sidebar.markdown("---")
opciones_menu = [MENU_SERV, MENU_MKT]

if st.session_state['rol'] == 'Admin':
    opciones_menu.append(MENU_USR)

division = st.sidebar.radio("Selecciona la División:", opciones_menu)
st.title("Panel de Control Sincronizado")

# ==========================================
# DIVISIÓN: SERVICIO TÉCNICO
# ==========================================
if division == MENU_SERV:
    st.header("Gestión de Servicio")
    cols_servicio = ["ID", "Cliente", "Caso reportado", "Modelo", "Numero de serie", "Seguimiento con fabrica", "Solucion del problema", "Fecha de reporte", "Fecha de cierre", "Estatus"]
    
    df_servicio = conn_servicio.read(ttl=0)
    df_servicio = preparar_df(df_servicio, cols_servicio).fillna("")
    
    if not df_servicio.empty:
        df_servicio['Numero de serie'] = df_servicio['Numero de serie'].apply(limpiar_serie)

    hoy = date.today()
    hubo_cambios = False
    if not df_servicio.empty:
        for index, row in df_servicio.iterrows():
            if str(row['Estatus']) != 'Finalizado' and str(row['Fecha de reporte']).strip() != "":
                try:
                    fecha_rep = datetime.strptime(str(row['Fecha de reporte']), '%Y-%m-%d').date()
                    dias_pasados = (hoy - fecha_rep).days
                    seguimiento = str(row['Seguimiento con fabrica']).strip()
                    
                    if dias_pasados >= 3 and seguimiento == "":
                        st.error(f"🚨 **ALERTA:** El caso ID {row['ID']} (Serie: {row['Numero de serie']}) lleva {dias_pasados} días sin seguimiento.")
                        if str(row['Estatus']) != 'Sin Seguimiento (Alerta)':
                            df_servicio.at[index, 'Estatus'] = 'Sin Seguimiento (Alerta)'
                            hubo_cambios = True
                    elif seguimiento != "" and str(row['Estatus']) == 'Sin Seguimiento (Alerta)':
                        df_servicio.at[index, 'Estatus'] = 'Activo'
                        hubo_cambios = True
                except ValueError: 
                    pass
        if hubo_cambios: 
            conn_servicio.update(data=df_servicio)

    with st.expander("➕ Registrar o Actualizar Caso", expanded=True):
        num_serie = st.text_input("🔍 Ingresa el Número de Serie:", key=f"buscador_serie_{st.session_state['serie_key']}")
        
        if num_serie:
            num_serie_str = str(num_serie).strip()
            coincidencias = df_servicio[df_servicio['Numero de serie'] == num_serie_str]
            
            if not coincidencias.empty:
                st.warning(f"⚠️ El equipo '{num_serie_str}' ya tiene reportes.")
                id_actualizar = st.selectbox("ID del caso para agregar seguimiento:", coincidencias['ID'].unique())
                nuevo_seguimiento = st.text_area("Agregar reporte:")
                
                if st.button("📝 Guardar Seguimiento"):
                    idx = df_servicio.index[df_servicio['ID'] == id_actualizar].tolist()[0]
                    seg_actual = str(df_servicio.at[idx, 'Seguimiento con fabrica'])
                    texto_final = f"{seg_actual}\n[{hoy}] {nuevo_seguimiento}".strip() if seg_actual else f"[{hoy}] {nuevo_seguimiento}"
                    df_servicio.at[idx, 'Seguimiento con fabrica'] = texto_final
                    df_servicio.at[idx, 'Estatus'] = 'Activo'
                    conn_servicio.update(data=df_servicio)
                    
                    st.session_state['serie_key'] += 1 
                    st.success("Seguimiento guardado exitosamente.")
                    st.rerun()
                st.markdown("---")
            
            with st.form("nuevo_caso", clear_on_submit=True):
                cliente = st.text_input("Cliente")
                modelo_seleccionado = st.selectbox("Modelo del Equipo", LISTA_EQUIPOS)
                modelo_otro = st.text_input("Especifica el modelo (Solo si elegiste 'Otro / Particular')")
                
                caso = st.text_area("Caso Reportado")
                nuevo_seg_fabrica = st.text_area("Seguimiento con Fábrica (Opcional)")
                nueva_solucion = st.text_area("Solución del Problema (Opcional)")
                fecha_reporte = st.date_input("Fecha de Reporte")
                
                if st.form_submit_button("Guardar Nuevo Caso"):
                    if modelo_seleccionado == "Otro / Particular" and modelo_otro.strip() != "":
                        modelo_final = modelo_otro.strip()
                    else:
                        modelo_final = modelo_seleccionado

                    nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                    nuevo_registro = pd.DataFrame([{
                        "ID": nuevo_id, 
                        "Cliente": cliente, 
                        "Caso reportado": caso, 
                        "Modelo": modelo_final, 
                        "Numero de serie": num_serie_str, 
                        "Seguimiento con fabrica": nuevo_seg_fabrica, 
                        "Solucion del problema": nueva_solucion, 
                        "Fecha de reporte": str(fecha_reporte), 
                        "Fecha de cierre": "", 
                        "Estatus": "Activo"
                    }])
                    conn_servicio.update(data=pd.concat([df_servicio, nuevo_registro], ignore_index=True))
                    
                    st.session_state['serie_key'] += 1 
                    st.success("Caso registrado con éxito.")
                    st.rerun()

    st.subheader("Casos Registrados")
    if not df_servicio.empty:
        st.dataframe(df_servicio.style.apply(color_filas, axis=1), use_container_width=True)
        st.write("### ⚙️ Gestionar Casos")
        
        col_sel, col_fin, col_del = st.columns([2, 1, 1])
        with col_sel:
            id_gestion = st.selectbox("Selecciona ID:", df_servicio['ID'].unique(), key="gest_serv")
        with col_fin:
            st.write(""); st.write("")
            if st.button("✅ Finalizar Caso"):
                idx = df_servicio.index[df_servicio['ID'] == id_gestion].tolist()[0]
                df_servicio.at[idx, 'Estatus'] = 'Finalizado'
                df_servicio.at[idx, 'Fecha de cierre'] = str(hoy)
                conn_servicio.update(data=df_servicio)
                st.success("Caso finalizado con éxito.")
                st.rerun()
                
        if st.session_state['rol'] == 'Admin':
            with col_del:
                st.write(""); st.write("")
                if st.button("🗑️ Borrar Caso"):
                    eliminar_registro_gsheets(conn_servicio, df_servicio, id_gestion)
                    st.success("Caso eliminado permanentemente de la nube.")
                    st.rerun()
    else:
        st.info("No hay casos registrados actualmente.")

# ==========================================
# DIVISIÓN: MARKETING
# ==========================================
elif division == MENU_MKT:
    st.header("Gestión de Préstamos")
    cols_mkt = ["ID", "KOL", "Lugar de prestamo", "Equipo", "Numero de serie", "Dias de licencia", "Vencimiento Licencia", "Fecha de inicio", "Fecha de finalizacion", "Estado"]
    
    df_marketing = conn_marketing.read(ttl=0)
    df_marketing = preparar_df(df_marketing, cols_mkt).fillna("")

    if not df_marketing.empty:
        if 'Numero de serie' in df_marketing.columns:
            df_marketing['Numero de serie'] = df_marketing['Numero de serie'].apply(limpiar_serie)
        if 'Dias de licencia' in df_marketing.columns:
            df_marketing['Dias de licencia'] = df_marketing['Dias de licencia'].apply(limpiar_decimales)

    hoy = date.today()
    hubo_cambios_mkt = False
    
    if not df_marketing.empty:
        for index, row in df_marketing.iterrows():
            if str(row['Estado']) != 'Finalizado':
                
                # 1. Verificar la fecha en que deben devolver el equipo físicamente
                if str(row['Fecha de finalizacion']).strip() != "":
                    try:
                        fecha_retorno = datetime.strptime(str(row['Fecha de finalizacion']), '%Y-%m-%d').date()
                        dias_retorno = (fecha_retorno - hoy).days
                        if 0 <= dias_retorno <= 5: 
                            st.warning(f"📦 **DEVOLUCIÓN PRÓXIMA:** El equipo '{row['Equipo']}' prestado a '{row['KOL']}' debe devolverse en {dias_retorno} días.")
                        elif dias_retorno < 0: 
                            st.error(f"❌ **DEVOLUCIÓN VENCIDA:** El préstamo de '{row['KOL']}' debió devolverse hace {abs(dias_retorno)} días.")
                    except ValueError: 
                        pass

                # 2. Verificar los días restantes de la Licencia (Software)
                if str(row['Vencimiento Licencia']).strip() != "":
                    try:
                        venc_licencia = datetime.strptime(str(row['Vencimiento Licencia']), '%Y-%m-%d').date()
                        dias_lic_restantes = (venc_licencia - hoy).days
                        
                        if str(row['Dias de licencia']) != str(dias_lic_restantes):
                            df_marketing.at[index, 'Dias de licencia'] = str(dias_lic_restantes)
                            hubo_cambios_mkt = True

                        if 0 <= dias_lic_restantes <= 5: 
                            st.warning(f"🔑 **LICENCIA POR VENCER:** La contraseña del equipo '{row['Equipo']}' de '{row['KOL']}' caduca en {dias_lic_restantes} días.")
                        elif dias_lic_restantes < 0: 
                            st.error(f"🚫 **LICENCIA CADUCADA:** La contraseña de '{row['Equipo']}' de '{row['KOL']}' se venció hace {abs(dias_lic_restantes)} días.")
                    except ValueError: 
                        pass
                
                elif str(row['Dias de licencia']).strip() != "":
                    try:
                        dias_estimados = int(float(row['Dias de licencia']))
                        fecha_estimada = hoy + timedelta(days=dias_estimados)
                        df_marketing.at[index, 'Vencimiento Licencia'] = str(fecha_estimada)
                        hubo_cambios_mkt = True
                    except:
                        pass
                    
        if hubo_cambios_mkt:
            conn_marketing.update(data=df_marketing)

    with st.expander("➕ Registrar Préstamo", expanded=True):
        with st.form("nuevo_prestamo", clear_on_submit=True):
            kol = st.text_input("Nombre KOL")
            lugar = st.text_input("Lugar Préstamo")
            
            equipo_seleccionado = st.selectbox("Equipo a Préstamo", LISTA_EQUIPOS)
            equipo_otro = st.text_input("Especifica el equipo (Solo si elegiste 'Otro / Particular')")
            num_serie_mkt = st.text_input("Número de Serie del Equipo")
            
            # Fechas y Días separados
            col1, col2, col3 = st.columns(3)
            with col1: 
                f_inicio = st.date_input("Fecha de Inicio")
            with col2: 
                f_fin = st.date_input("Fecha de Devolución FÍSICA")
            with col3:
                dias_otorgados = st.number_input("Días de Licencia (Contraseña)", min_value=1, step=1, value=1)
            
            if st.form_submit_button("Guardar Préstamo"):
                if f_fin < f_inicio: 
                    st.error("La fecha de devolución no puede ser menor a la fecha de inicio.")
                else:
                    if equipo_seleccionado == "Otro / Particular" and equipo_otro.strip() != "":
                        equipo_final = equipo_otro.strip()
                    else:
                        equipo_final = equipo_seleccionado

                    vencimiento_licencia = f_inicio + timedelta(days=dias_otorgados)

                    nuevo_id = int(df_marketing['ID'].max() + 1) if not df_marketing.empty else 1
                    nuevo_reg = pd.DataFrame([{
                        "ID": nuevo_id, 
                        "KOL": kol, 
                        "Lugar de prestamo": lugar, 
                        "Equipo": equipo_final, 
                        "Numero de serie": str(num_serie_mkt).strip(), 
                        "Dias de licencia": str((vencimiento_licencia - hoy).days), 
                        "Vencimiento Licencia": str(vencimiento_licencia),
                        "Fecha de inicio": str(f_inicio), 
                        "Fecha de finalizacion": str(f_fin), 
                        "Estado": "Activo"
                    }])
                    conn_marketing.update(data=pd.concat([df_marketing, nuevo_reg], ignore_index=True))
                    st.success("Préstamo registrado exitosamente.")
                    st.rerun()

    st.subheader("Equipos en Préstamo")
    if not df_marketing.empty:
        columnas_visibles = [c for c in df_marketing.columns if c != "Vencimiento Licencia"]
        st.dataframe(df_marketing[columnas_visibles].style.apply(color_filas, axis=1), use_container_width=True)
        
        st.write("### ⚙️ Gestionar Préstamos y Licencias")
        
        # CAMBIO: Ajustamos a 5 columnas para dar espacio al nuevo botón
        col_sel_m, col_renovar_lic, col_renovar_dev, col_fin_m, col_del_m = st.columns([1.5, 1.5, 1.5, 1, 1])
        
        with col_sel_m:
            id_mkt = st.selectbox("Selecciona ID:", df_marketing['ID'].unique(), key="gest_mkt")
            
        with col_renovar_lic:
            # Formulario para LICENCIA
            with st.form("form_renovar_licencia", clear_on_submit=True):
                dias_extra = st.number_input("Días de contraseña extra", min_value=1, step=1, value=1)
                
                if st.form_submit_button("🔑 Sumar Días a Licencia"):
                    idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                    
                    try:
                        venc_actual = datetime.strptime(str(df_marketing.at[idx, 'Vencimiento Licencia']), '%Y-%m-%d').date()
                    except:
                        venc_actual = hoy
                        
                    nuevo_venc = venc_actual + timedelta(days=dias_extra)
                    df_marketing.at[idx, 'Vencimiento Licencia'] = str(nuevo_venc)
                    df_marketing.at[idx, 'Dias de licencia'] = str((nuevo_venc - hoy).days)
                    
                    conn_marketing.update(data=df_marketing)
                    st.success(f"Se han agregado {dias_extra} días a la licencia.")
                    st.rerun()

        with col_renovar_dev:
            # NUEVO: Formulario para DEVOLUCIÓN FÍSICA
            with st.form("form_renovar_devolucion", clear_on_submit=True):
                dias_extra_dev = st.number_input("Días de préstamo extra", min_value=1, step=1, value=1)
                
                if st.form_submit_button("📦 Sumar Días a Devolución"):
                    idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                    
                    try:
                        fecha_dev_actual = datetime.strptime(str(df_marketing.at[idx, 'Fecha de finalizacion']), '%Y-%m-%d').date()
                    except:
                        fecha_dev_actual = hoy
                        
                    nueva_fecha_dev = fecha_dev_actual + timedelta(days=dias_extra_dev)
                    df_marketing.at[idx, 'Fecha de finalizacion'] = str(nueva_fecha_dev)
                    
                    conn_marketing.update(data=df_marketing)
                    st.success(f"Se han agregado {dias_extra_dev} días a la fecha de devolución.")
                    st.rerun()
                
        with col_fin_m:
            st.write(""); st.write("")
            if st.button("✅ Finalizar Préstamo"):
                idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                df_marketing.at[idx, 'Estado'] = 'Finalizado'
                conn_marketing.update(data=df_marketing)
                st.success("Préstamo finalizado con éxito.")
                st.rerun()
                
        if st.session_state['rol'] == 'Admin':
            with col_del_m:
                st.write(""); st.write("")
                if st.button("🗑️ Borrar Préstamo"):
                    eliminar_registro_gsheets(conn_marketing, df_marketing, id_mkt)
                    st.success("Préstamo eliminado permanentemente de la nube.")
                    st.rerun()
    else:
        st.info("No hay préstamos registrados actualmente.")

# ==========================================
# DIVISIÓN: PANEL DE USUARIOS (SOLO ADMIN)
# ==========================================
elif division == MENU_USR:
    st.header("Gestión de Usuarios del Sistema")
    st.info("Solo los administradores tienen acceso a este panel.")
    
    try:
        df_usuarios = conn_servicio.read(worksheet="Usuarios", ttl=0).dropna(how='all')
        st.dataframe(df_usuarios, use_container_width=True)
        
        with st.expander("➕ Crear Nuevo Usuario", expanded=True):
            with st.form("nuevo_usuario", clear_on_submit=True):
                nuevo_user = st.text_input("Nombre de Usuario")
                nuevo_pass = st.text_input("Contraseña")
                nuevo_rol = st.selectbox("Rol", ["Usuario", "Admin"])
                
                if st.form_submit_button("Crear Usuario"):
                    if nuevo_user and nuevo_pass:
                        fila_user = pd.DataFrame([{"Usuario": str(nuevo_user).strip(), "Password": str(nuevo_pass).strip(), "Rol": str(nuevo_rol).strip()}])
                        conn_servicio.update(worksheet="Usuarios", data=pd.concat([df_usuarios, fila_user], ignore_index=True))
                        st.success(f"Usuario '{nuevo_user}' creado con éxito.")
                        st.rerun()
                    else:
                        st.error("Por favor, llena todos los campos.")
    except Exception as e:
        st.error("No se pudo cargar la pestaña de Usuarios. Asegúrate de que exista en tu archivo de Excel de Servicio.")
