import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date

# 1. Configuración de Seguridad y Página
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="💰", layout="wide")

def check_password():
    """Devuelve True si el usuario ingresó la contraseña correcta."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Ingresá la contraseña de Mediamendoza", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña incorrecta. Intentá de nuevo:", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    else:
        return True

if check_password():
    # 2. Conexión y Carga de Datos
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1")
    except:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # 3. Sidebar (Menú Lateral)
    menu = st.sidebar.selectbox("Seleccioná una sección", ["📊 Dashboard", "➕ Cargar Movimiento", "📂 Ver Historial"])

    if menu == "📊 Dashboard":
        st.title("📊 Reporte Financiero Mediamendoza")
        
        if not df.empty:
            # Convertir monto a número por las dudas
            df["Monto"] = pd.to_numeric(df["Monto"])
            
            # Métricas Principales
            total_in = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
            total_out = df[df["Tipo"] == "Egreso"]["Monto"].sum()
            balance = total_in - total_out

            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos Totales", f"$ {total_in:,.2f}")
            c2.metric("Egresos Totales", f"$ {total_out:,.2f}")
            c3.metric("Saldo Neto", f"$ {balance:,.2f}", delta=float(balance))

            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)

            with col_graf1:
                st.subheader("Distribución de Gastos")
                fig_out = px.pie(df[df["Tipo"] == "Egreso"], values='Monto', names='Categoría', hole=0.4)
                st.plotly_chart(fig_out, use_container_width=True)

            with col_graf2:
                st.subheader("Ingresos por Categoría")
                fig_in = px.bar(df[df["Tipo"] == "Ingreso"], x='Categoría', y='Monto', color='Categoría')
                st.plotly_chart(fig_in, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar gráficos.")

    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Comprobante")
        with st.form("form_carga"):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad")
            with c2:
                f_monto = st.number_input("Monto", min_value=0.0)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Sueldos", "Hosting", "Servicios", "Otros"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            f_notas = st.text_area("Notas")
            if st.form_submit_button("Guardar Datos"):
                nueva_fila = pd.DataFrame([{"Fecha": str(f_fecha), "Tipo": f_tipo, "Entidad":
    st.dataframe(df.tail(10), use_container_width=True)
else:
    st.info("Todavía no hay movimientos registrados.")

