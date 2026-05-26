import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
conn = sqlite3.connect('sistema_gestion.db', check_same_thread=False)
c = conn.cursor()

# Tabla de Servicio
c.execute('''
    CREATE TABLE IF NOT EXISTS servicio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        caso_reportado TEXT,
        fecha_reporte DATE,
        numero_serie TEXT,
        seguimiento_fabrica TEXT,
        solucion TEXT,
        fecha_cierre DATE
    )
''')

# Tabla de Marketing (Actualizada con número de serie)
c.execute('''
    CREATE TABLE IF NOT EXISTS marketing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kol TEXT,
        lugar_prestamo TEXT,
        equipo TEXT,
        numero_serie TEXT,
        fecha_inicio DATE,
        fecha_fin DATE,
        dias_uso INTEGER
    )
''')
conn.commit()

# --- INTERFAZ DE LA APLICACIÓN ---
st.set_page_config(page_title="Sistema de Gestión", layout="wide")
st.title("Panel de Control")

# Menú lateral para navegar entre divisiones
division = st.sidebar.radio("Selecciona la División:", ["🔧 Servicio Técnico", "📈 Marketing"])

# ==========================================
# DIVISIÓN: SERVICIO
# ==========================================
if division == "🔧 Servicio Técnico":
    st.header("Gestión de Servicio")
    
    with st.expander("➕ Registrar Nuevo Caso"):
        with st.form("form_servicio"):
            cliente = st.text_input("Cliente")
            caso = st.text_area("Caso Reportado")
            fecha_reporte = st.date_input("Fecha de Reporte")
            num_serie = st.text_input("Número de Serie del Equipo")
            seguimiento = st.text_area("Seguimiento con Fábrica")
            solucion = st.text_area("Solución del Problema")
            fecha_cierre = st.date_input("Fecha de Cierre (Opcional)", value=None)
            
            submit_servicio = st.form_submit_button("Guardar Registro")
            
            if submit_servicio:
                c.execute('''INSERT INTO servicio 
                             (cliente, caso_reportado, fecha_reporte, numero_serie, seguimiento_fabrica, solucion, fecha_cierre) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (cliente, caso, fecha_reporte, num_serie, seguimiento, solucion, fecha_cierre))
                conn.commit()
                st.success("¡Caso registrado correctamente!")

    st.subheader("Casos Registrados")
    df_servicio = pd.read_sql_query("SELECT * FROM servicio", conn)
    st.dataframe(df_servicio, use_container_width=True)

# ==========================================
# DIVISIÓN: MARKETING
# ==========================================
elif division == "📈 Marketing":
    st.header("Gestión de Préstamos (KOL)")
    
    with st.expander("➕ Registrar Nuevo Préstamo"):
        with st.form("form_marketing"):
            kol = st.text_input("Nombre del KOL")
            lugar = st.text_input("Lugar de Préstamo del Equipo")
            equipo = st.text_input("Equipo a Préstamo")
            num_serie_mkt = st.text_input("Número de Serie del Equipo") # <--- NUEVO CAMPO AÑADIDO
            
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha de Inicio")
            with col2:
                fecha_fin = st.date_input("Fecha de Finalización")
            
            submit_marketing = st.form_submit_button("Guardar Préstamo")
            
            if submit_marketing:
                # Calcula automáticamente los días de uso
                dias_uso = (fecha_fin - fecha_inicio).days
                if dias_uso < 0:
                    st.error("La fecha de finalización no puede ser menor a la de inicio.")
                else:
                    # <--- CONSULTA SQL ACTUALIZADA
                    c.execute('''INSERT INTO marketing 
                                 (kol, lugar_prestamo, equipo, numero_serie, fecha_inicio, fecha_fin, dias_uso) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (kol, lugar, equipo, num_serie_mkt, fecha_inicio, fecha_fin, dias_uso))
                    conn.commit()
                    st.success(f"¡Préstamo registrado! Días totales de uso: {dias_uso}")

    st.subheader("Equipos en Préstamo y Recordatorios")
    df_marketing = pd.read_sql_query("SELECT * FROM marketing", conn)
    
    if not df_marketing.empty:
        # Lógica para el recordatorio de 5 días
        hoy = date.today()
        for index, row in df_marketing.iterrows():
            fecha_fin_dt = datetime.strptime(row['fecha_fin'], '%Y-%m-%d').date()
            dias_restantes = (fecha_fin_dt - hoy).days
            
            if 0 <= dias_restantes <= 5:
                st.warning(f"⚠️ **RECORDATORIO:** El préstamo del equipo '{row['equipo']}' (Serie: {row['numero_serie']}) al KOL '{row['kol']}' finaliza en {dias_restantes} días (Fecha: {row['fecha_fin']}).")
            elif dias_restantes < 0:
                st.error(f"❌ **VENCIDO:** El préstamo a '{row['kol']}' terminó hace {abs(dias_restantes)} días.")
                
        st.dataframe(df_marketing, use_container_width=True)
    else:
        st.info("No hay préstamos registrados aún.")