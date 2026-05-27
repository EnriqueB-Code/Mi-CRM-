import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

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
# SISTEMA DE LOGIN Y USUARIOS
# ==========================================
if 'logeado' not in st.session_state:
    st.session_state['logeado'] = False
    st.session_state['usuario'] = ""
    st.session_state['rol'] = ""

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
        num_serie = st.text_input("🔍 Ingresa el Número de Serie:")
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
                    st.success("Seguimiento guardado exitosamente.")
                    st.rerun()
                st.markdown("---")
            
            # FORMULARIO CON MENÚ DESPLEGABLE DE MODELOS
            with st.form("nuevo_caso", clear_on_submit=True):
                cliente = st.text_input("Cliente")
                
                # --- AQUÍ DEFINES TU LISTA DE MODELOS ---
                # Puedes agregar o quitar nombres dentro de los corchetes separados por comas
                modelos_disponibles = ["ECO 1","ECO 2", "ECO 3 EXP", "ECO 5", "ECO 6","SonoEye P1", "SonoEye P2", "SonoEye P3", "SonoEye P5", "SonoEye P6", "EBit20", "EBit30", "EBit50", "EBit60", "SonoBook 6", "SonoBook 7", "SonoBook 8", "SonoBook 9", "SonoAir 20", "SonoAir 30", "SonoAir 60", "SonoAir 70", "QBit 3", "QBit 5", "QBit 7", "QBit 9", "CBit 4", "CBit 6", "CBit 8", "CBit 9", "CBit 10", "SonoPort 8", "XBit 80", "XBit90", "SonoMax 7", "SonoMax 9", "Otro / Particular"]
                modelo = st.selectbox("Modelo del Equipo", modelos_disponibles)
                
                caso = st.text_area("Caso Reportado")
                nuevo_seg_fabrica = st.text_area("Seguimiento con Fábrica (Opcional)")
                nueva_solucion = st.text_area("Solución del Problema (Opcional)")
                fecha_reporte = st.date_input("Fecha de Reporte")
                
                if st.form_submit_button("Guardar Nuevo Caso"):
                    nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                    nuevo_registro = pd.DataFrame([{
                        "ID": nuevo_id, 
                        "Cliente": cliente, 
                        "Caso reportado": caso, 
                        "Modelo": modelo, 
                        "Numero de serie": num_serie_str, 
                        "Seguimiento con fabrica": nuevo_seg_fabrica, 
                        "Solucion del problema": nueva_solucion, 
                        "Fecha de reporte": str(fecha_reporte), 
                        "Fecha de cierre": "", 
                        "Estatus": "Activo"
                    }])
                    conn_servicio.update(data=pd.concat([df_servicio, nuevo_registro], ignore_index=True))
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
    cols_mkt = ["ID", "KOL", "Lugar de prestamo", "Equipo", "Dias de licencia", "Fecha de inicio", "Fecha de finalizacion", "Estado"]
    
    df_marketing = conn_marketing.read(ttl=0)
    df_marketing = preparar_df(df_marketing, cols_mkt).fillna("")

    hoy = date.today()
    if not df_marketing.empty:
        for index, row in df_marketing.iterrows():
            if str(row['Estado']) != 'Finalizado' and str(row['Fecha de finalizacion']).strip() != "":
                try:
                    fecha_fin = datetime.strptime(str(row['Fecha de finalizacion']), '%Y-%m-%d').date()
                    dias_restantes = (fecha_fin - hoy).days
                    if 0 <= dias_restantes <= 5: 
                        st.warning(f"⚠️ **VENCIMIENTO:** '{row['Equipo']}' con '{row['KOL']}' finaliza en {dias_restantes} días.")
                    elif dias_restantes < 0: 
                        st.error(f"❌ **VENCIDO:** Préstamo a '{row['KOL']}' expiró hace {abs(dias_restantes)} días.")
                except ValueError: 
                    pass

    with st.expander("➕ Registrar Préstamo", expanded=True):
        with st.form("nuevo_prestamo", clear_on_submit=True):
            kol = st.text_input("Nombre KOL")
            lugar = st.text_input("Lugar Préstamo")
            equipo = st.text_input("Equipo")
            c1, c2 = st.columns(2)
            with c1: f_inicio = st.date_input("Inicio")
            with c2: f_fin = st.date_input("Finalización")
            
            if st.form_submit_button("Guardar Préstamo"):
                dias_lic = (f_fin - f_inicio).days
                if dias_lic < 0: 
                    st.error("La fecha final no puede ser menor a la inicial.")
                else:
                    nuevo_id = int(df_marketing['ID'].max() + 1) if not df_marketing.empty else 1
                    nuevo_reg = pd.DataFrame([{"ID": nuevo_id, "KOL": kol, "Lugar de prestamo": lugar, "Equipo": equipo, "Dias de licencia": dias_lic, "Fecha de inicio": str(f_inicio), "Fecha de finalizacion": str(f_fin), "Estado": "Activo"}])
                    conn_marketing.update(data=pd.concat([df_marketing, nuevo_reg], ignore_index=True))
                    st.success("Préstamo registrado exitosamente.")
                    st.rerun()

    st.subheader("Equipos en Préstamo")
    if not df_marketing.empty:
        st.dataframe(df_marketing.style.apply(color_filas, axis=1), use_container_width=True)
        st.write("### ⚙️ Gestionar Préstamos")
        col_sel_m, col_fin_m, col_del_m = st.columns([2, 1, 1])
        with col_sel_m:
            id_mkt = st.selectbox("Selecciona ID:", df_marketing['ID'].unique(), key="gest_mkt")
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
