import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date

# 1. Configuración de Seguridad y Página
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="💰", layout="wide")

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido - Mediamendoza")
        st.text_input("Ingresá la contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    else:
        return True

if check_password():
    # 2. Conexión y Carga de Datos
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # Forzamos que no use caché para que los saldos se actualicen al instante
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # 3. Cálculo de Saldos (Para tenerlos siempre disponibles)
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        total_in = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
        total_out = df[df["Tipo"] == "Egreso"]["Monto"].sum()
        saldo_actual = total_in - total_out
    else:
        total_in = total_out = saldo_actual = 0

    # 4. Sidebar con Saldo Siempre Visible
    st.sidebar.image("https://www.mediamendoza.com/img/logo.png", width=200) # Opcional: logo del diario
    st.sidebar.title("Menú de Control")
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO ACTUAL", f"$ {saldo_actual:,.2f}")
    st.sidebar.divider()
    
    menu = st.sidebar.selectbox("Seleccioná una sección", ["📊 Dashboard", "➕ Cargar Movimiento", "📂 Ver Historial"])

    if menu == "📊 Dashboard":
        st.title("📊 Reporte Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos", f"$ {total_in:,.2f}")
        c2.metric("Total Egresos", f"$ {total_out:,.2f}")
        c3.metric("Saldo Neto", f"$ {saldo_actual:,.2f}")

        if not df.empty:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.subheader("Gastos por Categoría")
                fig_out = px.pie(df[df["Tipo"] == "Egreso"], values='Monto', names='Categoría', hole=0.4)
                st.plotly_chart(fig_out, use_container_width=True)
            with col_graf2:
                st.subheader("Ingresos por Categoría")
                fig_in = px.bar(df[df["Tipo"] == "Ingreso"], x='Categoría', y='Monto', color='Categoría')
                st.plotly_chart(fig_in, use_container_width=True)

    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Comprobante")
        
        # Formulario
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad (Cliente/Prov)")
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Sueldos", "Hosting", "Servicios", "Otros"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("Guardar en Mediamendoza"):
                # Formatear fecha a dd/mm/aaaa para Argentina
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
                
                df_final = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_final)
                st.success(f"✅ ¡Guardado! El saldo se ha actualizado.")
                st.balloons()
                st.info("Formulario limpio. Podés cargar otro movimiento.")

    elif menu == "📂 Ver Historial":
        st.title("📂 Historial de Movimientos")
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
