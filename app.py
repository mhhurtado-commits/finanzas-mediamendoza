import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date

# 1. Configuración de Seguridad y Página
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="📈", layout="wide")

def check_password():
    """Manejo de seguridad por contraseña."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Logo también en la pantalla de login para que se vea institucional
        st.image("https://www.mediamendoza.com/img/logo.png", width=300)
        st.title("🔐 Acceso Restringido")
        st.text_input("Ingresá la contraseña del sistema", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.image("https://www.mediamendoza.com/img/logo.png", width=300)
        st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    else:
        return True

if check_password():
    # 2. Conexión y Carga de Datos
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # 3. Cálculo de Saldos
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        total_in = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
        total_out = df[df["Tipo"] == "Egreso"]["Monto"].sum()
        saldo_actual = total_in - total_out
    else:
        total_in = total_out = saldo_actual = 0

    # 4. Barra Lateral (Sidebar) PERSONALIZADA
    # Aquí insertamos el logo del diario
    st.sidebar.image("https://www.mediamendoza.com/img/logo.png", use_container_width=True)
    st.sidebar.markdown("<h1 style='text-align: center; font-size: 20px;'>Sistema de Finanzas</h1>", unsafe_allow_html=True)
    st.sidebar.divider()
    
    # Muestra el saldo con un color amigable
    st.sidebar.metric("💰 SALDO ACTUAL", f"$ {saldo_actual:,.2f}")
    st.sidebar.divider()
    
    menu = st.sidebar.selectbox("Seleccioná una sección", ["📊 Dashboard", "➕ Cargar Movimiento", "📂 Ver Historial"])
    st.sidebar.info(f"Usuario: Administrador\nFecha: {date.today().strftime('%d/%m/%Y')}")

    # --- SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos", f"$ {total_in:,.2f}")
        c2.metric("Total Egresos", f"$ {total_out:,.2f}")
        # El delta ayuda a ver visualmente si el saldo es positivo
        c3.metric("Saldo Neto", f"$ {saldo_actual:,.2f}", delta=f"{saldo_actual:,.2f}")

        if not df.empty and len(df) > 0:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("Distribución de Gastos")
                df_egresos = df[df["Tipo"] == "Egreso"]
                if not df_egresos.empty:
                    fig_out = px.pie(df_egresos, values='Monto', names='Categoría', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_out, use_container_width=True)
                else:
                    st.info("No hay egresos cargados.")

            with col_graf2:
                st.subheader("Ingresos por Categoría")
                df_ingresos = df[df["Tipo"] == "Ingreso"]
                if not df_ingresos.empty:
                    fig_in = px.bar(df_ingresos, x='Categoría', y='Monto', color='Categoría', color_discrete_sequence=px.colors.sequential.Greens_r)
                    st.plotly_chart(fig_in, use_container_width=True)
                else:
                    st.info("No hay ingresos cargados.")
        else:
            st.info("Cargá tu primer movimiento para ver las estadísticas.")

    # --- SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Cargar Nuevo Movimiento")
        
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
            
            if st.form_submit_button("Guardar Registro"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ El nombre de la entidad y el monto son obligatorios.")
                else:
                    fecha_arg = f_fecha.strftime("%d/%m/%Y")
                    nueva_fila = pd.DataFrame([{"Fecha": fecha_arg, "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas}])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.toast("Guardado con éxito", icon="✅")
                    st.rerun()

    # --- SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial de Movimientos")
        if not df.empty:
            # Estilo para la tabla
            st.dataframe(df.iloc[::-1], use_container_width=True)
        else:
            st.write("No hay datos para mostrar.")
