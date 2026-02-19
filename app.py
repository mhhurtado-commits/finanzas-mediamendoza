import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date

# 1. Configuración de Seguridad y Página
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="💰", layout="wide")

def check_password():
    """Manejo de seguridad por contraseña."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido - Mediamendoza")
        st.text_input("Ingresá la contraseña del sistema", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    else:
        return True

if check_password():
    # 2. Conexión y Carga de Datos (ttl=0 para actualización inmediata)
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # 3. Cálculo de Saldos
    if not df.empty:
        # Aseguramos que Monto sea numérico
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        total_in = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
        total_out = df[df["Tipo"] == "Egreso"]["Monto"].sum()
        saldo_actual = total_in - total_out
    else:
        total_in = total_out = saldo_actual = 0

    # 4. Barra Lateral (Sidebar) con Saldo y Navegación
    st.sidebar.title("💎 Mediamendoza")
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO ACTUAL", f"$ {saldo_actual:,.2f}")
    st.sidebar.divider()
    
    menu = st.sidebar.selectbox("Seleccioná una sección", ["📊 Dashboard", "➕ Cargar Movimiento", "📂 Ver Historial"])

    # --- SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos", f"$ {total_in:,.2f}")
        c2.metric("Total Egresos", f"$ {total_out:,.2f}")
        c3.metric("Saldo Neto", f"$ {saldo_actual:,.2f}")

        if not df.empty and len(df) > 0:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("Distribución de Gastos")
                df_egresos = df[df["Tipo"] == "Egreso"]
                if not df_egresos.empty:
                    fig_out = px.pie(df_egresos, values='Monto', names='Categoría', hole=0.4)
                    st.plotly_chart(fig_out, use_container_width=True)
                else:
                    st.info("No hay egresos cargados.")

            with col_graf2:
                st.subheader("Ingresos por Categoría")
                df_ingresos = df[df["Tipo"] == "Ingreso"]
                if not df_ingresos.empty:
                    fig_in = px.bar(df_ingresos, x='Categoría', y='Monto', color='Categoría')
                    st.plotly_chart(fig_in, use_container_width=True)
                else:
                    st.info("No hay ingresos cargados.")
        else:
            st.info("Cargá tu primer movimiento para ver las estadísticas.")

    # --- SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Cargar Nuevo Movimiento")
        
        # Formulario que se limpia al enviar
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo de Operación", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad (Cliente/Proveedor)")
            with c2:
                f_monto = st.number_input("Monto en Pesos ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Sueldos", "Hosting", "Servicios", "Otros"])
                f_estado = st.radio("Estado de Operación", ["Pagado", "Pendiente"], horizontal=True)
            
            f_notas = st.text_area("Notas Adicionales")
            
            submit_button = st.form_submit_button("Guardar Registro")
            
            if submit_button:
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ El nombre de la entidad y el monto son obligatorios.")
                else:
                    # Formatear fecha a dd/mm/aaaa
                    fecha_arg = f_fecha.strftime("%d/%m/%Y")
                    
                    nueva_fila = pd.DataFrame([{
                        "Fecha": fecha_arg, 
                        "Tipo": f_tipo, 
                        "Entidad": f_entidad, 
                        "Categoría": f_cat, 
                        "Monto": f_monto, 
                        "Estado": f_estado, 
                        "Notas": f_notas
                    }])
                    
                    # Unir y Guardar
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    
                    st.toast("¡Datos enviados a Google Sheets!", icon="🚀")
                    # Forzar reinicio para actualizar el saldo en la barra lateral inmediatamente
                    st.rerun()

    # --- SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial de Movimientos")
        st.markdown("Los registros más nuevos aparecen arriba.")
        # Mostramos el historial invertido (últimos arriba)
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True)
        else:
            st.write("No hay datos para mostrar.")
