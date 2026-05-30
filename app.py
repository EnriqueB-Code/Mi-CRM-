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
# LISTAS MAESTRAS
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

LISTA_STATUS_DANADAS = [
    "Shipped to Singapore", 
    "Threw it away", 
    "Waiting to be shipped to HongKong", 
    "Waiting to be shipped to Mexico's office", 
    "Otros"
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
        
        idx = df_usuarios.index[df_usuarios['Usuario'] == user_limpio].tolist()[0]
        if 'Ultimo Acceso' not in df_usuarios.columns:
            df_usuarios['Ultimo Acceso'] = ""
        df_usuarios.at[idx, 'Ultimo Acceso'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn_servicio.update(worksheet="Usuarios", data=df_usuarios)
        
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
# FUNCIONES DE UTILIDAD Y AUDITORÍA
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

def eliminar_registro_gsheets(conexion, df_original, id_a_borrar, nombre_pestana=None):
    df_nuevo = df_original[df_original['ID'] != id_a_borrar].copy()
    diferencia = len(df_original) - len(df_nuevo)
    if diferencia > 0:
        filas_vacias = pd.DataFrame([[""] * len(df_original.columns)] * diferencia, columns=df_original.columns)
        df_escritura = pd.concat([df_nuevo, filas_vacias], ignore_index=True)
        df_escritura['ID'] = range(1, len(df_escritura) + 1)
        if nombre_pestana:
            conexion.update(worksheet=nombre_pestana, data=df_escritura)
        else:
            conexion.update(data=df_escritura)
    else:
        if nombre_pestana:
            conexion.update(worksheet=nombre_pestana, data=df_nuevo)
        else:
            conexion.update(data=df_nuevo)

def mover_fila(df, id_sel, direccion):
    idx = df.index[df['ID'] == id_sel].tolist()[0]
    if direccion == 'up' and idx > 0:
        b, a = df.iloc[idx].copy(), df.iloc[idx-1].copy()
        df.iloc[idx], df.iloc[idx-1] = a, b
    elif direccion == 'down' and idx < len(df) - 1:
        b, a = df.iloc[idx].copy(), df.iloc[idx+1].copy()
        df.iloc[idx], df.iloc[idx+1] = a, b
    df['ID'] = range(1, len(df) + 1)
    return df

def registrar_auditoria(cambios):
    if not cambios: return
    try:
        df_aud = conn_servicio.read(worksheet="Auditoria", ttl=0)
    except:
        df_aud = pd.DataFrame(columns=["Fecha", "Usuario", "Modulo", "ID Caso", "Campo", "Valor Anterior", "Valor Nuevo"])
    
    logs = []
    fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usr = st.session_state['usuario']
    for c in cambios:
        logs.append({"Fecha": fecha_str, "Usuario": usr, "Modulo": c['modulo'], "ID Caso": c['id'], "Campo": c['campo'], "Valor Anterior": c['ant'], "Valor Nuevo": c['nvo']})
    
    df_final = pd.concat([df_aud, pd.DataFrame(logs)], ignore_index=True)
    conn_servicio.update(worksheet="Auditoria", data=df_final)

# Nombres estables de menú
MENU_SERV = "🔧 Servicio Técnico"
MENU_MKT = "📈 Marketing"
MENU_EVE = "📅 Calendario de Eventos"
MENU_INV = "📦 Inventario de Refacciones"
MENU_DEMO = "💻 Equipos Demo"
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
opciones_menu = [MENU_SERV, MENU_MKT, MENU_EVE, MENU_INV, MENU_DEMO]

if st.session_state['rol'] == 'Admin':
    opciones_menu.append(MENU_USR)

division = st.sidebar.radio("Selecciona la División:", opciones_menu)
st.title("Panel de Control Sincronizado")

# VARIABLE GLOBAL DE FECHA
hoy = date.today()

# ==========================================
# DIVISIÓN: SERVICIO TÉCNICO
# ==========================================
if division == MENU_SERV:
    st.header("Gestión de Servicio")
    cols_servicio = ["ID", "Cliente", "Caso reportado", "Modelo", "Numero de serie", "Seguimiento con fabrica", "Solucion del problema", "Fecha de reporte", "Fecha de cierre", "Estatus", "Creado por"]
    
    df_servicio = conn_servicio.read(ttl=0)
    df_servicio = preparar_df(df_servicio, cols_servicio).fillna("")
    
    if not df_servicio.empty:
        df_servicio['Numero de serie'] = df_servicio['Numero de serie'].apply(limpiar_serie)

    hubo_cambios = False
    if not df_servicio.empty:
        for index, row in df_servicio.iterrows():
            if str(row['Estatus']) != 'Finalizado' and str(row['Fecha de reporte']).strip() != "":
                try:
                    fecha_rep = datetime.strptime(str(row['Fecha de reporte']), '%Y-%m-%d').date()
                    dias_pasados = (hoy - fecha_rep).days
                    seguimiento = str(row['Seguimiento con fabrica']).strip()
                    
                    if dias_pasados >= 3 and seguimiento == "":
                        if str(row['Estatus']) != 'Sin Seguimiento (Alerta)':
                            df_servicio.at[index, 'Estatus'] = 'Sin Seguimiento (Alerta)'
                            hubo_cambios = True
                    elif seguimiento != "" and str(row['Estatus']) == 'Sin Seguimiento (Alerta)':
                        df_servicio.at[index, 'Estatus'] = 'Activo'
                        hubo_cambios = True
                except ValueError: pass
        if hubo_cambios: conn_servicio.update(data=df_servicio)

    tab_reg, tab_edit = st.tabs(["➕ Registrar / Actualizar", "✏️ Editar Caso"])
    
    with tab_reg:
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
                    
                    registrar_auditoria([{'modulo': 'Servicio', 'id': id_actualizar, 'campo': 'Seguimiento con fabrica', 'ant': seg_actual, 'nvo': texto_final}])
                    
                    df_servicio.at[idx, 'Seguimiento con fabrica'] = texto_final
                    df_servicio.at[idx, 'Estatus'] = 'Activo'
                    conn_servicio.update(data=df_servicio)
                    st.session_state['serie_key'] += 1 
                    st.success("Seguimiento guardado exitosamente."); st.rerun()
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
                    modelo_final = modelo_otro.strip() if modelo_seleccionado == "Otro / Particular" and modelo_otro.strip() != "" else modelo_seleccionado
                    nuevo_id = int(df_servicio['ID'].max() + 1) if not df_servicio.empty else 1
                    nuevo_registro = pd.DataFrame([{
                        "ID": nuevo_id, "Cliente": cliente, "Caso reportado": caso, "Modelo": modelo_final, 
                        "Numero de serie": num_serie_str, "Seguimiento con fabrica": nuevo_seg_fabrica, 
                        "Solucion del problema": nueva_solucion, "Fecha de reporte": str(fecha_reporte), 
                        "Fecha de cierre": "", "Estatus": "Activo", "Creado por": st.session_state['usuario']
                    }])
                    conn_servicio.update(data=pd.concat([df_servicio, nuevo_registro], ignore_index=True))
                    st.session_state['serie_key'] += 1; st.success("Caso registrado con éxito."); st.rerun()

    with tab_edit:
        if not df_servicio.empty:
            id_ed_s = st.selectbox("Selecciona ID a editar:", df_servicio['ID'].unique(), key="edit_sel_s")
            if id_ed_s:
                idx = df_servicio.index[df_servicio['ID'] == id_ed_s].tolist()[0]
                with st.form("form_edit_s"):
                    cl_ed = st.text_input("Cliente", value=df_servicio.at[idx, 'Cliente'])
                    mod_act = df_servicio.at[idx, 'Modelo']
                    mod_ed = st.selectbox("Modelo", LISTA_EQUIPOS, index=LISTA_EQUIPOS.index(mod_act) if mod_act in LISTA_EQUIPOS else LISTA_EQUIPOS.index("Otro / Particular"))
                    mod_o_ed = st.text_input("Especifica (si es Otro)", value=mod_act if mod_act not in LISTA_EQUIPOS else "")
                    ns_ed = st.text_input("Número de serie", value=df_servicio.at[idx, 'Numero de serie'])
                    caso_ed = st.text_area("Caso", value=df_servicio.at[idx, 'Caso reportado'])
                    seg_ed = st.text_area("Seguimiento", value=df_servicio.at[idx, 'Seguimiento con fabrica'])
                    sol_ed = st.text_area("Solución", value=df_servicio.at[idx, 'Solucion del problema'])
                    est_ed = st.selectbox("Estatus", ["Activo", "Sin Seguimiento (Alerta)", "Finalizado"], index=["Activo", "Sin Seguimiento (Alerta)", "Finalizado"].index(df_servicio.at[idx, 'Estatus']) if df_servicio.at[idx, 'Estatus'] in ["Activo", "Sin Seguimiento (Alerta)", "Finalizado"] else 0)

                    if st.form_submit_button("Guardar Edición"):
                        modelo_f_ed = mod_o_ed.strip() if mod_ed == "Otro / Particular" and mod_o_ed.strip() != "" else mod_ed
                        cambios = []
                        campos_ver = [('Cliente', cl_ed), ('Modelo', modelo_f_ed), ('Numero de serie', ns_ed), 
                                      ('Caso reportado', caso_ed), ('Seguimiento con fabrica', seg_ed), 
                                      ('Solucion del problema', sol_ed), ('Estatus', est_ed)]
                        
                        for col, nvo_val in campos_ver:
                            ant_val = str(df_servicio.at[idx, col])
                            if ant_val != str(nvo_val):
                                cambios.append({'modulo':'Servicio', 'id':id_ed_s, 'campo':col, 'ant':ant_val, 'nvo':str(nvo_val)})
                                df_servicio.at[idx, col] = str(nvo_val)
                        
                        if cambios:
                            registrar_auditoria(cambios)
                            conn_servicio.update(data=df_servicio)
                            st.success("Cambios guardados."); st.rerun()
                        else:
                            st.info("No se detectaron cambios.")

    st.subheader("Casos Registrados")
    if not df_servicio.empty:
        st.dataframe(df_servicio.style.apply(color_filas, axis=1), use_container_width=True, hide_index=True)
        st.write("### ⚙️ Gestionar Casos")
        
        col_sel, col_up, col_down, col_fin, col_del = st.columns([2, 1, 1, 1.5, 1])
        with col_sel:
            id_gestion = st.selectbox("Selecciona ID:", df_servicio['ID'].unique(), key="gest_serv")
        with col_up:
            st.write(""); st.write("")
            if st.button("⬆️ Subir", key="up_s"):
                df_servicio = mover_fila(df_servicio, id_gestion, 'up')
                conn_servicio.update(data=df_servicio); st.rerun()
        with col_down:
            st.write(""); st.write("")
            if st.button("⬇️ Bajar", key="dw_s"):
                df_servicio = mover_fila(df_servicio, id_gestion, 'down')
                conn_servicio.update(data=df_servicio); st.rerun()
        with col_fin:
            st.write(""); st.write("")
            if st.button("✅ Finalizar Caso"):
                idx = df_servicio.index[df_servicio['ID'] == id_gestion].tolist()[0]
                registrar_auditoria([{'modulo':'Servicio', 'id':id_gestion, 'campo':'Estatus', 'ant':df_servicio.at[idx, 'Estatus'], 'nvo':'Finalizado'}])
                df_servicio.at[idx, 'Estatus'] = 'Finalizado'
                df_servicio.at[idx, 'Fecha de cierre'] = str(hoy)
                conn_servicio.update(data=df_servicio); st.success("Caso finalizado."); st.rerun()
                
        if st.session_state['rol'] == 'Admin':
            with col_del:
                st.write(""); st.write("")
                if st.button("🗑️ Borrar Caso"):
                    eliminar_registro_gsheets(conn_servicio, df_servicio, id_gestion)
                    st.success("Caso eliminado."); st.rerun()
    else:
        st.info("No hay casos registrados actualmente.")

# ==========================================
# DIVISIÓN: MARKETING
# ==========================================
elif division == MENU_MKT:
    st.header("Gestión de Préstamos")
    cols_mkt = ["ID", "KOL", "Lugar de prestamo", "Equipo", "Numero de serie", "Dias de licencia", "Vencimiento Licencia", "Fecha de inicio", "Fecha de finalizacion", "Estado", "Creado por"]
    
    df_marketing = conn_marketing.read(ttl=0)
    df_marketing = preparar_df(df_marketing, cols_mkt).fillna("")

    if not df_marketing.empty:
        if 'Numero de serie' in df_marketing.columns:
            df_marketing['Numero de serie'] = df_marketing['Numero de serie'].apply(limpiar_serie)
        if 'Dias de licencia' in df_marketing.columns:
            df_marketing['Dias de licencia'] = df_marketing['Dias de licencia'].apply(limpiar_decimales)

    hubo_cambios_mkt = False
    
    if not df_marketing.empty:
        for index, row in df_marketing.iterrows():
            if str(row['Estado']) != 'Finalizado':
                if str(row['Fecha de finalizacion']).strip() != "":
                    try:
                        fecha_retorno = datetime.strptime(str(row['Fecha de finalizacion']), '%Y-%m-%d').date()
                        dias_retorno = (fecha_retorno - hoy).days
                        if 0 <= dias_retorno <= 5: st.warning(f"📦 **DEVOLUCIÓN PRÓXIMA:** '{row['Equipo']}' a '{row['KOL']}' devolver en {dias_retorno} días.")
                        elif dias_retorno < 0: st.error(f"❌ **DEVOLUCIÓN VENCIDA:** '{row['KOL']}' debió devolver hace {abs(dias_retorno)} días.")
                    except ValueError: pass

                if str(row['Vencimiento Licencia']).strip() != "":
                    try:
                        venc_licencia = datetime.strptime(str(row['Vencimiento Licencia']), '%Y-%m-%d').date()
                        dias_lic_restantes = (venc_licencia - hoy).days
                        if str(row['Dias de licencia']) != str(dias_lic_restantes):
                            df_marketing.at[index, 'Dias de licencia'] = str(dias_lic_restantes)
                            hubo_cambios_mkt = True
                        if 0 <= dias_lic_restantes <= 5: st.warning(f"🔑 **LICENCIA POR VENCER:** Contraseña de '{row['Equipo']}' de '{row['KOL']}' caduca en {dias_lic_restantes} días.")
                        elif dias_lic_restantes < 0: st.error(f"🚫 **LICENCIA CADUCADA:** Contraseña de '{row['Equipo']}' de '{row['KOL']}' venció hace {abs(dias_lic_restantes)} días.")
                    except ValueError: pass
                    
        if hubo_cambios_mkt: conn_marketing.update(data=df_marketing)

    tab_reg_m, tab_edit_m = st.tabs(["➕ Registrar Préstamo", "✏️ Editar Préstamo"])

    with tab_reg_m:
        with st.form("nuevo_prestamo", clear_on_submit=True):
            kol = st.text_input("Nombre KOL")
            lugar = st.text_input("Lugar Préstamo")
            equipo_seleccionado = st.selectbox("Equipo a Préstamo", LISTA_EQUIPOS)
            equipo_otro = st.text_input("Especifica el equipo (Solo si elegiste 'Otro / Particular')")
            num_serie_mkt = st.text_input("Número de Serie del Equipo")
            
            col1, col2, col3 = st.columns(3)
            with col1: f_inicio = st.date_input("Fecha de Inicio")
            with col2: f_fin = st.date_input("Fecha de Devolución FÍSICA")
            with col3: dias_otorgados = st.number_input("Días de Licencia (Contraseña)", min_value=1, step=1, value=1)
            
            st.caption("💡 *Nota: Si seleccionas 'Otro / Particular', los días de licencia no se tomarán en cuenta.*")
            
            if st.form_submit_button("Guardar Préstamo"):
                if f_fin < f_inicio: 
                    st.error("La fecha de devolución no puede ser menor a la fecha de inicio.")
                else:
                    equipo_final = equipo_otro.strip() if equipo_seleccionado == "Otro / Particular" and equipo_otro.strip() != "" else equipo_seleccionado
                    if equipo_seleccionado == "Otro / Particular":
                        venc_str, dias_str = "", ""
                    else:
                        v_lic = f_inicio + timedelta(days=dias_otorgados)
                        venc_str, dias_str = str(v_lic), str((v_lic - hoy).days)

                    nuevo_id = int(df_marketing['ID'].max() + 1) if not df_marketing.empty else 1
                    nuevo_reg = pd.DataFrame([{
                        "ID": nuevo_id, "KOL": kol, "Lugar de prestamo": lugar, "Equipo": equipo_final, 
                        "Numero de serie": str(num_serie_mkt).strip(), "Dias de licencia": dias_str, 
                        "Vencimiento Licencia": venc_str, "Fecha de inicio": str(f_inicio), 
                        "Fecha de finalizacion": str(f_fin), "Estado": "Activo", "Creado por": st.session_state['usuario']
                    }])
                    conn_marketing.update(data=pd.concat([df_marketing, nuevo_reg], ignore_index=True))
                    st.success("Préstamo registrado exitosamente."); st.rerun()

    with tab_edit_m:
        if not df_marketing.empty:
            id_ed_m = st.selectbox("Selecciona ID a editar:", df_marketing['ID'].unique(), key="edit_sel_m")
            if id_ed_m:
                idx = df_marketing.index[df_marketing['ID'] == id_ed_m].tolist()[0]
                with st.form("form_edit_m"):
                    kol_ed = st.text_input("KOL", value=df_marketing.at[idx, 'KOL'])
                    lug_ed = st.text_input("Lugar", value=df_marketing.at[idx, 'Lugar de prestamo'])
                    eq_act = df_marketing.at[idx, 'Equipo']
                    eq_ed = st.selectbox("Equipo", LISTA_EQUIPOS, index=LISTA_EQUIPOS.index(eq_act) if eq_act in LISTA_EQUIPOS else LISTA_EQUIPOS.index("Otro / Particular"))
                    eq_o_ed = st.text_input("Especifica", value=eq_act if eq_act not in LISTA_EQUIPOS else "")
                    ns_ed = st.text_input("Número de serie", value=df_marketing.at[idx, 'Numero de serie'])
                    est_ed_m = st.selectbox("Estado", ["Activo", "Finalizado"], index=["Activo", "Finalizado"].index(df_marketing.at[idx, 'Estado']) if df_marketing.at[idx, 'Estado'] in ["Activo", "Finalizado"] else 0)

                    if st.form_submit_button("Guardar Edición"):
                        eq_f_ed = eq_o_ed.strip() if eq_ed == "Otro / Particular" and eq_o_ed.strip() != "" else eq_ed
                        cambios = []
                        campos_ver = [('KOL', kol_ed), ('Lugar de prestamo', lug_ed), ('Equipo', eq_f_ed), 
                                      ('Numero de serie', ns_ed), ('Estado', est_ed_m)]
                        for col, nvo_val in campos_ver:
                            ant_val = str(df_marketing.at[idx, col])
                            if ant_val != str(nvo_val):
                                cambios.append({'modulo':'Marketing', 'id':id_ed_m, 'campo':col, 'ant':ant_val, 'nvo':str(nvo_val)})
                                df_marketing.at[idx, col] = str(nvo_val)
                        
                        if cambios:
                            registrar_auditoria(cambios)
                            conn_marketing.update(data=df_marketing)
                            st.success("Cambios guardados."); st.rerun()
                        else:
                            st.info("No se detectaron cambios.")

    st.subheader("Equipos en Préstamo")
    if not df_marketing.empty:
        columnas_visibles = [c for c in df_marketing.columns if c != "Vencimiento Licencia"]
        st.dataframe(df_marketing[columnas_visibles].style.apply(color_filas, axis=1), use_container_width=True, hide_index=True)
        
        st.write("### ⚙️ Gestionar Préstamos y Licencias")
        
        col_sel_m, col_up_m, col_down_m, col_ren_lic, col_ren_dev, col_fin_m, col_del_m = st.columns([1.5, 0.5, 0.5, 1.5, 1.5, 1, 1])
        
        with col_sel_m:
            id_mkt = st.selectbox("Selecciona ID:", df_marketing['ID'].unique(), key="gest_mkt")
        with col_up_m:
            st.write(""); st.write("")
            if st.button("⬆️", key="up_m"):
                df_marketing = mover_fila(df_marketing, id_mkt, 'up')
                conn_marketing.update(data=df_marketing); st.rerun()
        with col_down_m:
            st.write(""); st.write("")
            if st.button("⬇️", key="dw_m"):
                df_marketing = mover_fila(df_marketing, id_mkt, 'down')
                conn_marketing.update(data=df_marketing); st.rerun()
            
        with col_ren_lic:
            with st.form("form_renovar_licencia", clear_on_submit=True):
                dias_extra = st.number_input("+ Días Licencia", min_value=1, step=1, value=1)
                if st.form_submit_button("🔑 Sumar Licencia"):
                    idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                    if str(df_marketing.at[idx, 'Vencimiento Licencia']).strip() == "" and str(df_marketing.at[idx, 'Dias de licencia']).strip() == "":
                        st.warning("⚠️ No maneja licencia.")
                    else:
                        try: venc_actual = datetime.strptime(str(df_marketing.at[idx, 'Vencimiento Licencia']), '%Y-%m-%d').date()
                        except: venc_actual = hoy
                        nuevo_venc = venc_actual + timedelta(days=dias_extra)
                        
                        registrar_auditoria([{'modulo':'Marketing', 'id':id_mkt, 'campo':'Vencimiento Licencia', 'ant':str(venc_actual), 'nvo':str(nuevo_venc)}])
                        df_marketing.at[idx, 'Vencimiento Licencia'] = str(nuevo_venc)
                        df_marketing.at[idx, 'Dias de licencia'] = str((nuevo_venc - hoy).days)
                        conn_marketing.update(data=df_marketing); st.success("Licencia extendida."); st.rerun()

        with col_ren_dev:
            with st.form("form_renovar_devolucion", clear_on_submit=True):
                dias_extra_dev = st.number_input("+ Días Físicos", min_value=1, step=1, value=1)
                if st.form_submit_button("📦 Sumar Devolución"):
                    idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                    try: fecha_dev_actual = datetime.strptime(str(df_marketing.at[idx, 'Fecha de finalizacion']), '%Y-%m-%d').date()
                    except: fecha_dev_actual = hoy
                    nueva_fecha_dev = fecha_dev_actual + timedelta(days=dias_extra_dev)
                    
                    registrar_auditoria([{'modulo':'Marketing', 'id':id_mkt, 'campo':'Fecha de finalizacion', 'ant':str(fecha_dev_actual), 'nvo':str(nueva_fecha_dev)}])
                    df_marketing.at[idx, 'Fecha de finalizacion'] = str(nueva_fecha_dev)
                    conn_marketing.update(data=df_marketing); st.success("Devolución extendida."); st.rerun()
                
        with col_fin_m:
            st.write(""); st.write("")
            if st.button("✅ Finalizar"):
                idx = df_marketing.index[df_marketing['ID'] == id_mkt].tolist()[0]
                registrar_auditoria([{'modulo':'Marketing', 'id':id_mkt, 'campo':'Estado', 'ant':df_marketing.at[idx, 'Estado'], 'nvo':'Finalizado'}])
                df_marketing.at[idx, 'Estado'] = 'Finalizado'
                conn_marketing.update(data=df_marketing); st.success("Préstamo finalizado."); st.rerun()
                
        if st.session_state['rol'] == 'Admin':
            with col_del_m:
                st.write(""); st.write("")
                if st.button("🗑️ Borrar"):
                    eliminar_registro_gsheets(conn_marketing, df_marketing, id_mkt)
                    st.success("Préstamo eliminado."); st.rerun()
    else:
        st.info("No hay préstamos registrados actualmente.")

# ==========================================
# DIVISIÓN: EVENTOS
# ==========================================
elif division == MENU_EVE:
    st.header("📅 Calendario de Eventos")
    cols_eve = ["ID", "Nombre del evento", "Distribuidor", "Fecha de inicio", "Fecha de termino", "Creado por"]
    
    try:
        df_eventos = conn_marketing.read(worksheet="Eventos", ttl=0)
        df_eventos = preparar_df(df_eventos, cols_eve).fillna("")
    except:
        df_eventos = pd.DataFrame(columns=cols_eve)
        
    tab_reg_e, tab_edit_e = st.tabs(["➕ Registrar Evento", "✏️ Editar Evento"])
    
    with tab_reg_e:
        with st.form("form_eventos", clear_on_submit=True):
            ev_nombre = st.text_input("Nombre del evento")
            ev_dist = st.text_input("Distribuidor")
            col1, col2 = st.columns(2)
            with col1: ev_ini = st.date_input("Fecha de inicio")
            with col2: ev_fin = st.date_input("Fecha de término")
            
            if st.form_submit_button("Guardar Evento"):
                nuevo_id = int(df_eventos['ID'].max() + 1) if not df_eventos.empty else 1
                nuevo_reg = pd.DataFrame([{"ID": nuevo_id, "Nombre del evento": ev_nombre, "Distribuidor": ev_dist, "Fecha de inicio": str(ev_ini), "Fecha de termino": str(ev_fin), "Creado por": st.session_state['usuario']}])
                conn_marketing.update(worksheet="Eventos", data=pd.concat([df_eventos, nuevo_reg], ignore_index=True))
                st.success("Evento registrado."); st.rerun()
                
    with tab_edit_e:
        if not df_eventos.empty:
            id_ed_e = st.selectbox("Selecciona ID a editar:", df_eventos['ID'].unique(), key="edit_sel_e")
            if id_ed_e:
                idx = df_eventos.index[df_eventos['ID'] == id_ed_e].tolist()[0]
                with st.form("form_edit_e"):
                    nomb_ed = st.text_input("Nombre", value=df_eventos.at[idx, 'Nombre del evento'])
                    dist_ed = st.text_input("Distribuidor", value=df_eventos.at[idx, 'Distribuidor'])
                    
                    if st.form_submit_button("Guardar Edición"):
                        cambios = []
                        campos_ver = [('Nombre del evento', nomb_ed), ('Distribuidor', dist_ed)]
                        for col, nvo_val in campos_ver:
                            ant_val = str(df_eventos.at[idx, col])
                            if ant_val != str(nvo_val):
                                cambios.append({'modulo':'Eventos', 'id':id_ed_e, 'campo':col, 'ant':ant_val, 'nvo':str(nvo_val)})
                                df_eventos.at[idx, col] = str(nvo_val)
                        
                        if cambios:
                            registrar_auditoria(cambios)
                            conn_marketing.update(worksheet="Eventos", data=df_eventos)
                            st.success("Cambios guardados."); st.rerun()

    st.subheader("Eventos Programados")
    if not df_eventos.empty:
        st.dataframe(df_eventos, use_container_width=True, hide_index=True)
        st.write("### ⚙️ Gestionar Eventos")
        col_sel, col_up, col_dw, col_del = st.columns([2, 1, 1, 2])
        with col_sel:
            id_gest_e = st.selectbox("Selecciona ID:", df_eventos['ID'].unique(), key="gest_eve")
        with col_up:
            st.write(""); st.write("")
            if st.button("⬆️", key="up_e"):
                df_eventos = mover_fila(df_eventos, id_gest_e, 'up')
                conn_marketing.update(worksheet="Eventos", data=df_eventos); st.rerun()
        with col_dw:
            st.write(""); st.write("")
            if st.button("⬇️", key="dw_e"):
                df_eventos = mover_fila(df_eventos, id_gest_e, 'down')
                conn_marketing.update(worksheet="Eventos", data=df_eventos); st.rerun()
        if st.session_state['rol'] == 'Admin':
            with col_del:
                st.write(""); st.write("")
                if st.button("🗑️ Borrar Evento"):
                    eliminar_registro_gsheets(conn_marketing, df_eventos, id_gest_e, "Eventos")
                    st.success("Evento eliminado."); st.rerun()
    else:
        st.info("No hay eventos registrados.")

# ==========================================
# DIVISIÓN: INVENTARIO DE REFACCIONES
# ==========================================
elif division == MENU_INV:
    st.header("📦 Control de Inventario de Refacciones")
    tab_nuevas, tab_danadas = st.tabs(["✨ Piezas Nuevas", "🛠️ Piezas Dañadas"])
    
    # --- PIEZAS NUEVAS ---
    with tab_nuevas:
        cols_nuevas = ["ID", "Box #", "PN", "Description", "SN", "Receive", "Status", "From", "Current Location", "Remarks", "Creado por"]
        try:
            df_nuevas = conn_servicio.read(worksheet="Inv_Nuevas", ttl=0)
            df_nuevas = preparar_df(df_nuevas, cols_nuevas).fillna("")
        except:
            df_nuevas = pd.DataFrame(columns=cols_nuevas)
            
        with st.expander("➕ Registrar Pieza Nueva"):
            with st.form("form_nva_pieza", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    box = st.text_input("Box #")
                    pn = st.text_input("PN (Número de Parte)")
                    sn = st.text_input("SN (Número de Serie)")
                with c2:
                    desc = st.text_area("Description")
                    receive = st.date_input("Receive (Fecha de recepción)")
                with c3:
                    status = st.text_input("Status")
                    from_loc = st.text_input("From (Origen)")
                    curr_loc = st.text_input("Current Location (Ubicación actual)")
                remarks = st.text_input("Remarks (Comentarios)")
                
                if st.form_submit_button("Guardar Pieza Nueva"):
                    nuevo_id = int(df_nuevas['ID'].max() + 1) if not df_nuevas.empty else 1
                    nuevo_reg = pd.DataFrame([{
                        "ID": nuevo_id, "Box #": box, "PN": pn, "Description": desc, "SN": sn,
                        "Receive": str(receive), "Status": status, "From": from_loc, 
                        "Current Location": curr_loc, "Remarks": remarks, "Creado por": st.session_state['usuario']
                    }])
                    conn_servicio.update(worksheet="Inv_Nuevas", data=pd.concat([df_nuevas, nuevo_reg], ignore_index=True))
                    st.success("Pieza nueva registrada exitosamente."); st.rerun()
                    
        if not df_nuevas.empty:
            st.dataframe(df_nuevas, use_container_width=True, hide_index=True)
            st.write("### ⚙️ Gestionar Piezas Nuevas")
            
            with st.expander("✏️ Editar Pieza Nueva"):
                id_ed_n = st.selectbox("Selecciona ID a editar:", df_nuevas['ID'].unique(), key="edit_sel_n")
                if id_ed_n:
                    idx_n = df_nuevas.index[df_nuevas['ID'] == id_ed_n].tolist()[0]
                    with st.form("form_edit_n"):
                        e_box = st.text_input("Box #", value=df_nuevas.at[idx_n, 'Box #'])
                        e_pn = st.text_input("PN", value=df_nuevas.at[idx_n, 'PN'])
                        e_sn = st.text_input("SN", value=df_nuevas.at[idx_n, 'SN'])
                        e_desc = st.text_area("Description", value=df_nuevas.at[idx_n, 'Description'])
                        
                        try:
                            val_date = str(df_nuevas.at[idx_n, 'Receive']).strip()
                            e_rec = datetime.strptime(val_date, '%Y-%m-%d').date()
                        except:
                            e_rec = hoy
                        
                        e_receive = st.date_input("Receive", value=e_rec)
                        e_status = st.text_input("Status", value=df_nuevas.at[idx_n, 'Status'])
                        e_from = st.text_input("From", value=df_nuevas.at[idx_n, 'From'])
                        e_loc = st.text_input("Current Location", value=df_nuevas.at[idx_n, 'Current Location'])
                        e_rem = st.text_input("Remarks", value=df_nuevas.at[idx_n, 'Remarks'])
                        
                        if st.form_submit_button("💾 Guardar Edición"):
                            cambios = []
                            campos_ver = [
                                ('Box #', e_box), ('PN', e_pn), ('SN', e_sn), ('Description', e_desc),
                                ('Receive', str(e_receive)), ('Status', e_status), ('From', e_from),
                                ('Current Location', e_loc), ('Remarks', e_rem)
                            ]
                            for col, nvo_val in campos_ver:
                                ant_val = str(df_nuevas.at[idx_n, col])
                                if ant_val != str(nvo_val):
                                    cambios.append({'modulo':'Inv_Nuevas', 'id':id_ed_n, 'campo':col, 'ant':ant_val, 'nvo':str(nvo_val)})
                                    df_nuevas.at[idx_n, col] = str(nvo_val)
                            
                            if cambios:
                                registrar_auditoria(cambios)
                                conn_servicio.update(worksheet="Inv_Nuevas", data=df_nuevas)
                                st.success("Cambios guardados."); st.rerun()
                            else:
                                st.info("No se detectaron cambios.")
            
            if st.session_state['rol'] == 'Admin':
                id_borrar_n = st.selectbox("Selecciona ID a borrar (Nuevas):", df_nuevas['ID'].unique(), key="del_nv")
                if st.button("🗑️ Borrar Pieza Nueva"):
                    eliminar_registro_gsheets(conn_servicio, df_nuevas, id_borrar_n, "Inv_Nuevas")
                    st.success("Pieza eliminada."); st.rerun()
        else:
            st.info("No hay piezas nuevas registradas.")

    # --- PIEZAS DAÑADAS ---
    with tab_danadas:
        cols_danadas = ["ID", "PN", "Description", "SN", "Origin Unit", "Origin Unit SN", "Status", "Customer", "Distributor", "Tracking Number", "Creado por"]
        try:
            df_danadas = conn_servicio.read(worksheet="Inv_Danadas", ttl=0)
            df_danadas = preparar_df(df_danadas, cols_danadas).fillna("")
        except:
            df_danadas = pd.DataFrame(columns=cols_danadas)
            
        with st.expander("➕ Registrar Pieza Dañada"):
            with st.form("form_danada", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    pn_d = st.text_input("PN (Número de Parte)")
                    sn_d = st.text_input("SN (Número de Serie)")
                    desc_d = st.text_area("Description")
                with c2:
                    ou_d = st.text_input("Origin Unit (Equipo de origen)")
                    ou_sn_d = st.text_input("Origin Unit SN (Serie equipo origen)")
                    status_d = st.selectbox("Status", LISTA_STATUS_DANADAS)
                    status_d_otro = st.text_input("Especifica el status (Solo si elegiste 'Otros')")
                with c3:
                    cust_d = st.text_input("Customer (Cliente)")
                    dist_d = st.text_input("Distributor (Distribuidor)")
                    track_d = st.text_input("Tracking Number (Guía)")
                    
                if st.form_submit_button("Guardar Pieza Dañada"):
                    stat_final = status_d_otro.strip() if status_d == "Otros" and status_d_otro.strip() != "" else status_d
                    nuevo_id = int(df_danadas['ID'].max() + 1) if not df_danadas.empty else 1
                    nuevo_reg = pd.DataFrame([{
                        "ID": nuevo_id, "PN": pn_d, "Description": desc_d, "SN": sn_d,
                        "Origin Unit": ou_d, "Origin Unit SN": ou_sn_d, "Status": stat_final, 
                        "Customer": cust_d, "Distributor": dist_d, "Tracking Number": track_d,
                        "Creado por": st.session_state['usuario']
                    }])
                    conn_servicio.update(worksheet="Inv_Danadas", data=pd.concat([df_danadas, nuevo_reg], ignore_index=True))
                    st.success("Pieza dañada registrada exitosamente."); st.rerun()
                    
        if not df_danadas.empty:
            st.dataframe(df_danadas, use_container_width=True, hide_index=True)
            st.write("### ⚙️ Gestionar Piezas Dañadas")
            
            with st.expander("✏️ Editar Pieza Dañada"):
                id_ed_d = st.selectbox("Selecciona ID a editar:", df_danadas['ID'].unique(), key="edit_sel_d")
                if id_ed_d:
                    idx_d = df_danadas.index[df_danadas['ID'] == id_ed_d].tolist()[0]
                    with st.form("form_edit_d"):
                        e_pn_d = st.text_input("PN", value=df_danadas.at[idx_d, 'PN'])
                        e_sn_d = st.text_input("SN", value=df_danadas.at[idx_d, 'SN'])
                        e_desc_d = st.text_area("Description", value=df_danadas.at[idx_d, 'Description'])
                        e_ou = st.text_input("Origin Unit", value=df_danadas.at[idx_d, 'Origin Unit'])
                        e_ou_sn = st.text_input("Origin Unit SN", value=df_danadas.at[idx_d, 'Origin Unit SN'])
                        
                        stat_act = str(df_danadas.at[idx_d, 'Status']).strip()
                        idx_stat = LISTA_STATUS_DANADAS.index(stat_act) if stat_act in LISTA_STATUS_DANADAS else LISTA_STATUS_DANADAS.index("Otros")
                        e_status_d = st.selectbox("Status", LISTA_STATUS_DANADAS, index=idx_stat)
                        e_status_d_otro = st.text_input("Especifica (Si elegiste Otros)", value=stat_act if stat_act not in LISTA_STATUS_DANADAS else "")
                        
                        e_cust = st.text_input("Customer", value=df_danadas.at[idx_d, 'Customer'])
                        e_dist = st.text_input("Distributor", value=df_danadas.at[idx_d, 'Distributor'])
                        e_track = st.text_input("Tracking Number", value=df_danadas.at[idx_d, 'Tracking Number'])
                        
                        if st.form_submit_button("💾 Guardar Edición"):
                            stat_f_ed = e_status_d_otro.strip() if e_status_d == "Otros" and e_status_d_otro.strip() != "" else e_status_d
                            cambios = []
                            campos_ver = [
                                ('PN', e_pn_d), ('SN', e_sn_d), ('Description', e_desc_d), 
                                ('Origin Unit', e_ou), ('Origin Unit SN', e_ou_sn), ('Status', stat_f_ed),
                                ('Customer', e_cust), ('Distributor', e_dist), ('Tracking Number', e_track)
                            ]
                            for col, nvo_val in campos_ver:
                                ant_val = str(df_danadas.at[idx_d, col])
                                if ant_val != str(nvo_val):
                                    cambios.append({'modulo':'Inv_Danadas', 'id':id_ed_d, 'campo':col, 'ant':ant_val, 'nvo':str(nvo_val)})
                                    df_danadas.at[idx_d, col] = str(nvo_val)
                            
                            if cambios:
                                registrar_auditoria(cambios)
                                conn_servicio.update(worksheet="Inv_Danadas", data=df_danadas)
                                st.success("Cambios guardados."); st.rerun()
                            else:
                                st.info("No se detectaron cambios.")
            
            if st.session_state['rol'] == 'Admin':
                id_borrar_d = st.selectbox("Selecciona ID a borrar (Dañadas):", df_danadas['ID'].unique(), key="del_da")
                if st.button("🗑️ Borrar Pieza Dañada"):
                    eliminar_registro_gsheets(conn_servicio, df_danadas, id_borrar_d, "Inv_Danadas")
                    st.success("Pieza eliminada."); st.rerun()
        else:
            st.info("No hay piezas dadas de baja registradas.")

# ==========================================
# DIVISIÓN: EQUIPOS DEMO (NUEVA SECCIÓN DINÁMICA)
# ==========================================
elif division == MENU_DEMO:
    st.header("💻 Inventario de Equipos Demo (Oficina)")
    cols_demo = ["ID", "Model", "Serial Number", "Dedicated Unit", "Creado por"]
    
    try:
        df_demo = conn_marketing.read(worksheet="Equipos_Demo", ttl=0)
        df_demo = preparar_df(df_demo, cols_demo).fillna("")
        if not df_demo.empty:
            df_demo['Serial Number'] = df_demo['Serial Number'].apply(limpiar_serie)
    except:
        df_demo = pd.DataFrame(columns=cols_demo)

    # 1. OBTENER SERIES BAJO PRÉSTAMO ACTIVO EN MARKETING EN TIEMPO REAL
    series_prestadas = []
    try:
        df_mkt_actual = conn_marketing.read(ttl=0)
        df_mkt_actual = preparar_df(df_mkt_actual, ["Numero de serie", "Estado"]).fillna("")
        series_prestadas = df_mkt_actual[df_mkt_actual['Estado'] == 'Activo']["Numero de serie"].apply(limpiar_serie).tolist()
    except:
        pass

    # 2. FILTRAR EL INVENTARIO DINÁMICAMENTE
    if not df_demo.empty:
        df_demo['Serie_Aux'] = df_demo['Serial Number'].apply(limpiar_serie)
        df_demo_disponibles = df_demo[~df_demo['Serie_Aux'].isin(series_prestadas)].drop(columns=['Serie_Aux'])
        df_demo_prestados = df_demo[df_demo['Serie_Aux'].isin(series_prestadas)].drop(columns=['Serie_Aux'])
        df_demo = df_demo.drop(columns=['Serie_Aux'])
    else:
        df_demo_disponibles = pd.DataFrame(columns=cols_demo)
        df_demo_prestados = pd.DataFrame(columns=cols_demo)

    # 3. VISTAS DEL INVENTARIO
    st.subheader("✅ Equipos Disponibles en la Oficina")
    if not df_demo_disponibles.empty:
        st.dataframe(df_demo_disponibles, use_container_width=True, hide_index=True)
    else:
        st.info("No hay equipos demo disponibles en oficina en este momento.")

    if not df_demo_prestados.empty:
        with st.expander("📦 Ver Equipos Actuales en Préstamo Externo"):
            st.warning("Estos equipos no aparecen arriba porque actualmente están asignados a un KOL en Marketing.")
            st.dataframe(df_demo_prestados, use_container_width=True, hide_index=True)

    # 4. OPERACIONES DEL CATÁLOGO (ALTAS, BAJAS, CAMBIOS)
    st.write("---")
    st.write("### ⚙️ Administración de Catálogo de Equipos Demo")
    tab_alta_d, tab_edit_d = st.tabs(["➕ Registrar Equipo Demo", "✏️ Editar / Eliminar Equipo"])

    with tab_alta_d:
        with st.form("form_alta_demo", clear_on_submit=True):
            d_modelo = st.text_input("Model (Ej. Phased Array Probe S1-5P)")
            d_serie = st.text_input("Serial Number")
            
            d_ded_sel = st.selectbox("Dedicated Unit", LISTA_EQUIPOS, key="ded_ins_d")
            d_ded_otro = st.text_input("Especifica Dedicated Unit (Si elegiste 'Otro / Particular')", key="ded_ins_o_d")
            
            if st.form_submit_button("Guardar Equipo Demo"):
                if d_serie.strip() == "":
                    st.error("El Serial Number es obligatorio.")
                else:
                    ded_final_d = d_ded_otro.strip() if d_ded_sel == "Otro / Particular" and d_ded_otro.strip() != "" else d_ded_sel
                    nuevo_id = int(df_demo['ID'].max() + 1) if not df_demo.empty else 1
                    nuevo_reg = pd.DataFrame([{
                        "ID": nuevo_id, 
                        "Model": str(d_modelo).strip(), 
                        "Serial Number": str(d_serie).strip(), 
                        "Dedicated Unit": ded_final_d,
                        "Creado por": st.session_state['usuario']
                    }])
                    conn_marketing.update(worksheet="Equipos_Demo", data=pd.concat([df_demo, nuevo_reg], ignore_index=True))
                    st.success("Equipo demo agregado al catálogo maestro."); st.rerun()

    with tab_edit_d:
        if not df_demo.empty:
            id_ed_demo = st.selectbox("Selecciona ID de Equipo Demo para modificar:", df_demo['ID'].unique(), key="sb_edit_demo")
            if id_ed_demo:
                idx_demo = df_demo.index[df_demo['ID'] == id_ed_demo].tolist()[0]
                
                with st.form("form_edit_demo"):
                    e_mod_d = st.text_input("Model", value=df_demo.at[idx_demo, 'Model'])
                    e_ser_d = st.text_input("Serial Number", value=df_demo.at[idx_demo, 'Serial Number'])
                    
                    ded_act = str(df_demo.at[idx_demo, 'Dedicated Unit']).strip()
                    idx_ded = LISTA_EQUIPOS.index(ded_act) if ded_act in LISTA_EQUIPOS else LISTA_EQUIPOS.index("Otro / Particular")
                    
                    e_ded_sel = st.selectbox("Dedicated Unit", LISTA_EQUIPOS, index=idx_ded)
                    e_ded_otro = st.text_input("Especifica (Si elegiste Otro)", value=ded_act if ded_act not in LISTA_EQUIPOS else "")
                    
                    col_sav_d, col_spc_d = st.columns([1, 4])
                    with col_sav_d:
                        save_btn = st.form_submit_button("💾 Guardar Cambios")
                        
                    if save_btn:
                        ded_f_ed = e_ded_otro.strip() if e_ded_sel == "Otro / Particular" and e_ded_otro.strip() != "" else e_ded_sel
                        cambios = []
                        campos_ver = [
                            ('Model', str(e_mod_d).strip()), 
                            ('Serial Number', str(e_ser_d).strip()), 
                            ('Dedicated Unit', ded_f_ed)
                        ]
                        
                        for col, nvo_val in campos_ver:
                            ant_val = str(df_demo.at[idx_demo, col])
                            if ant_val != str(nvo_val):
                                cambios.append({'modulo':'Equipos_Demo', 'id':id_ed_demo, 'campo':col, 'ant':ant_val, 'nvo':str(nvo_val)})
                                df_demo.at[idx_demo, col] = str(nvo_val)
                                
                        if cambios:
                            registrar_auditoria(cambios)
                            conn_marketing.update(worksheet="Equipos_Demo", data=df_demo)
                            st.success("Equipo modificado."); st.rerun()
                        else:
                            st.info("Sin cambios detectados.")

                if st.session_state['rol'] == 'Admin':
                    st.write("⚠️ **Zona de peligro (Admin):**")
                    if st.button("🗑️ Eliminar permanentemente de la Base de Datos"):
                        eliminar_registro_gsheets(conn_marketing, df_demo, id_ed_demo, "Equipos_Demo")
                        st.success("Equipo eliminado del inventario maestro."); st.rerun()
        else:
            st.info("No hay equipos registrados en la base de datos.")

# ==========================================
# DIVISIÓN: PANEL DE USUARIOS (SOLO ADMIN)
# ==========================================
elif division == MENU_USR:
    st.header("Gestión de Usuarios")
    
    df_usuarios = conn_servicio.read(worksheet="Usuarios", ttl=0).dropna(how='all')
    st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
    
    with st.expander("➕ Crear Nuevo Usuario", expanded=False):
        with st.form("nuevo_usuario", clear_on_submit=True):
            nuevo_user = st.text_input("Nombre de Usuario")
            nuevo_pass = st.text_input("Contraseña")
            nuevo_rol = st.selectbox("Rol", ["Usuario", "Admin"])
            
            if st.form_submit_button("Crear Usuario"):
                if nuevo_user and nuevo_pass:
                    fila_user = pd.DataFrame([{"Usuario": str(nuevo_user).strip(), "Password": str(nuevo_pass).strip(), "Rol": str(nuevo_rol).strip(), "Ultimo Acceso": ""}])
                    conn_servicio.update(worksheet="Usuarios", data=pd.concat([df_usuarios, fila_user], ignore_index=True))
                    st.success(f"Usuario '{nuevo_user}' creado."); st.rerun()
                else:
                    st.error("Por favor, llena todos los campos.")
                    
    st.markdown("---")
    st.subheader("🕵️‍♂️ Registro de Auditoría (Cambios realizados)")
    try:
        df_auditoria = conn_servicio.read(worksheet="Auditoria", ttl=0).dropna(how='all')
        if not df_auditoria.empty:
            st.dataframe(df_auditoria, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay registros de cambios.")
    except:
        st.info("La tabla de Auditoria aún no se ha creado o está vacía.")
