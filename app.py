import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date
import os

# 1. Configuración de la Página
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="📈", layout="wide")

# Función para mostrar el logo
def mostrar_logo(en_sidebar=False):
    if os.path.exists("logo.png"):
        if en_sidebar:
            st.sidebar.image("logo.png", use_container_width=True)
        else:
            st.image("logo.png", width=250)
    else:
        if not en_sidebar:
            st.title("📊 Mediamendoza Finanzas")

# Función de seguridad
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    if "password_correct" not in st.session_state:
        mostrar_logo()
        st.title("🔐 Acceso Restringido")
        st.text_input("Ingresá la contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        mostrar_logo()
        st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    return True

# --- INICIO DE LA APP ---
if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # 3. Lógica Contable
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        ingresos_reales = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        egresos_reales = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real = ingresos_reales - egresos_reales
        a_cobrar = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        a_pagar = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
    else:
        ingresos_reales = egresos_reales = saldo_real = a_cobrar = a_pagar = 0

    # 4. Barra Lateral
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO CAJA (Real)", f"$ {saldo_real:,.2f}")
    if a_cobrar > 0: st.sidebar.warning(f"📩 A Cobrar: $ {a_cobrar:,.2f}")
    if a_pagar > 0: st.sidebar.error(f"💸 A Pagar: $ {a_pagar:,.2f}")
    st.sidebar.divider()
    menu = st.sidebar.selectbox("Menú Principal", ["📊 Dashboard", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📂 Ver Historial"])

    # --- 5. SECCIÓN: DASHBOARD (GRÁFICOS REPARADOS) ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Cobrado", f"$ {ingresos_reales:,.2f}")
        c2.metric("Pagado", f"$ {egresos_reales:,.2f}")
        c3.metric("Saldo Real", f"$ {saldo_real:,.2f}")
        
        st.markdown("---")
        
        if not df.empty:
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("Distribución de Gastos (Todos)")
                # Mostramos todos los egresos para que el gráfico no esté vacío, 
                # pero los pintamos por estado
                df_eg = df[df["Tipo"] == "Egreso"]
                if not df_eg.empty:
                    fig_eg = px.pie(df_eg, values='Monto', names='Categoría', hole=0.4, 
                                   title="Egresos por Categoría (Pagados + Pendientes)")
                    st.plotly_chart(fig_eg, use_container_width=True)
                else:
                    st.info("No hay egresos registrados para mostrar gráfico.")

            with col_graf2:
                st.subheader("Análisis de Ingresos")
                df_in = df[df["Tipo"] == "Ingreso"]
                if not df_in.empty:
                    fig_in = px.bar(df_in, x='Estado', y='Monto', color='Categoría', 
                                   title="Ingresos: Pagados vs Pendientes")
                    st.plotly_chart(fig_in, use_container_width=True)
                else:
                    st.info("No hay ingresos registrados para mostrar gráfico.")
            
            st.markdown("---")
            st.subheader("Estado de Pendientes")
            p1, p2, p3 = st.columns(3)
            p1.metric("Pendiente de Cobro", f"$ {a_cobrar:,.2f}")
            p2.metric("Pendiente de Pago", f"$ {a_pagar:,.2f}")
            p3.metric("Saldo Proyectado", f"$ {saldo_real + a_cobrar - a_pagar:,.2f}")
        else:
            st.info("Cargá datos para ver las estadísticas.")

    # --- 6. SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Cargar Nuevo Movimiento")
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Seleccioná la Fecha", date.today())
                st.info(f"Fecha: {f_fecha.strftime('%d/%m/%Y')}")
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad")
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Sueldos", "Hosting", "Servicios", "Otros"])
                f_estado = st.radio("Estado Inicial", ["Pagado", "Pendiente"], horizontal=True)
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar Registro"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ Datos obligatorios faltantes.")
                else:
                    fecha_arg = f_fecha.strftime("%d/%m/%Y")
                    nueva_fila = pd.DataFrame([{"Fecha": fecha_arg, "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas}])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.toast("¡Guardado!")
                    st.rerun()

    # --- 7. SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Gestión de Pendientes")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        if pendientes.empty:
            st.success("No hay nada pendiente. 🎉")
        else:
            for index, row in pendientes.iterrows():
                label = f"🟢 [COBRO] {row['Entidad']}" if row['Tipo'] == "Ingreso" else f"🔴 [PAGO] {row['Entidad']}"
                with st.expander(f"{label} - $ {row['Monto']:,.2f}"):
                    st.write(f"Fecha: {row['Fecha']} | Categoría: {row['Categoría']}")
                    if st.button(f"Confirmar Liquidación", key=f"upd_{index}"):
                        df.at[index, "Estado"] = "Pagado"
                        conn.update(worksheet="Hoja 1", data=df)
                        st.success("¡Actualizado!")
                        st.rerun()

    # --- 8. SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial")
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True)
