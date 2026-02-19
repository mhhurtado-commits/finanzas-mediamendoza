import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import os

# 1. Configuración de la Página
st.set_page_config(page_title="Gestión Mediamendoza PRO", page_icon="🏦", layout="wide")

def mostrar_logo(en_sidebar=False):
    if os.path.exists("logo.png"):
        if en_sidebar: st.sidebar.image("logo.png", use_container_width=True)
        else: st.image("logo.png", width=250)
    else:
        if not en_sidebar: st.title("📊 Mediamendoza Finanzas")

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        mostrar_logo(); st.title("🔐 Acceso Restringido")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        mostrar_logo(); st.text_input("Error", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado."); return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # Cargamos los datos. Si agregaste columnas nuevas en el Excel manualmente, Streamlit las traerá.
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas", "Vencimiento", "Cuenta", "Medio"])

    # --- LÓGICA MULTI-CUENTA ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        # Solo lo Pagado afecta el saldo real
        df_reales = df[df["Estado"] == "Pagado"]
        
        # Función para calcular saldo por cuenta
        def saldo_por_cuenta(nombre_cuenta):
            ing = df_reales[(df_reales["Cuenta"] == nombre_cuenta) & (df_reales["Tipo"] == "Ingreso")]["Monto"].sum()
            eg = df_reales[(df_reales["Cuenta"] == nombre_cuenta) & (df_reales["Tipo"] == "Egreso")]["Monto"].sum()
            return ing - eg

        saldo_total = df_reales[df_reales["Tipo"] == "Ingreso"]["Monto"].sum() - df_reales[df_reales["Tipo"] == "Egreso"]["Monto"].sum()
        obligaciones = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
    else:
        saldo_total = obligaciones = 0

    # --- 4. BARRA LATERAL ---
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    
    st.sidebar.subheader("Navegación")
    menu = st.sidebar.radio(
        "Ir a:",
        ["📊 Dashboard", "🏦 Cuentas y Bancos", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📆 Vencimientos", "📂 Historial"],
        index=0
    )
    
    st.sidebar.divider()
    st.sidebar.subheader("Caja Global")
    st.sidebar.metric("💰 SALDO TOTAL", f"$ {saldo_total:,.2f}")
    
    st.sidebar.divider()
    st.sidebar.info(f"📅 {date.today().strftime('%d/%m/%Y')}")

    # --- SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo Total", f"$ {saldo_total:,.2f}")
        c2.metric("Obligaciones", f"$ {obligaciones:,.2f}", delta_color="inverse")
        c3.metric("E-Cheques en Cartera", f"$ {df[(df['Medio'] == 'E-Cheque') & (df['Estado'] == 'Pendiente')]['Monto'].sum():,.2f}")
        
        st.markdown("---")
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Saldos por Cuenta")
                cuentas_lista = df["Cuenta"].unique()
                saldos_data = {"Cuenta": [], "Saldo": []}
                for c in cuentas_lista:
                    saldos_data["Cuenta"].append(c)
                    saldos_data["Saldo"].append(saldo_por_cuenta(c))
                fig_cuentas = px.bar(saldos_data, x="Cuenta", y="Saldo", color="Cuenta", text_auto='.2s')
                st.plotly_chart(fig_cuentas, use_container_width=True)
            with col2:
                st.subheader("Gastos por Categoría")
                fig_pie = px.pie(df[df["Tipo"] == "Egreso"], values="Monto", names="Categoría", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

    # --- SECCIÓN: CUENTAS Y BANCOS (NUEVA) ---
    elif menu == "🏦 Cuentas y Bancos":
        st.title("🏦 Estado de mis Cuentas")
        if not df.empty:
            cuentas_activas = df["Cuenta"].unique()
            cols = st.columns(len(cuentas_activas))
            for i, c in enumerate(cuentas_activas):
                s = saldo_por_cuenta(c)
                cols[i].metric(c, f"$ {s:,.2f}")
            
            st.markdown("---")
            st.subheader("Detalle de E-Cheques y Valores")
            echeques = df[df["Medio"] == "E-Cheque"]
            st.dataframe(echeques, use_container_width=True)

    # --- SECCIÓN: CARGA (CON MULTI-CUENTA) ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad / Concepto")
                f_cuenta = st.selectbox("Cuenta / Banco", ["Caja Efectivo", "Banco Galicia", "Mercado Pago", "Banco Nación"])
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Sueldos", "Hosting", "Comisiones Bancarias", "Impuestos", "Servicios", "Otros"])
                f_medio = st.selectbox("Medio de Pago", ["Transferencia", "Efectivo", "E-Cheque", "Débito Automático"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            f_venc = st.date_input("Fecha de Vencimiento / Cobro Cheque", date.today())
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar Registro"):
                nueva_fila = pd.DataFrame([{
                    "Fecha": f_fecha.strftime("%d/%m/%Y"), "Tipo": f_tipo, "Entidad": f_entidad, 
                    "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas,
                    "Vencimiento": f_venc.strftime("%d/%m/%Y"), "Cuenta": f_cuenta, "Medio": f_medio
                }])
                df_final = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_final)
                st.toast("✅ Registrado"); st.rerun()

    # --- SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidar Pendientes")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        for idx, row in pendientes.iterrows():
            with st.expander(f"{row['Tipo']} - {row['Entidad']} ({row['Cuenta']}) - $ {row['Monto']:,.2f}"):
                if st.button(f"Marcar como Liquidado", key=f"pay_{idx}"):
                    df.at[idx, "Estado"] = "Pagado"
                    conn.update(worksheet="Hoja 1", data=df)
                    st.rerun()

    # --- SECCIÓN: VENCIMIENTOS ---
    elif menu == "📆 Vencimientos":
        st.title("📆 Calendario de Obligaciones")
        eg_pendientes = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")].copy()
        if not eg_pendientes.empty:
            eg_pendientes['Venc_Date'] = pd.to_datetime(eg_pendientes['Vencimiento'], format='%d/%m/%Y', errors='coerce')
            eg_pendientes = eg_pendientes.sort_values(by='Venc_Date')
            for _, row in eg_pendientes.iterrows():
                st.write(f"Vence {row['Vencimiento']}: {row['Entidad']} en {row['Cuenta']} - $ {row['Monto']:,.2f}")

    # --- SECCIÓN: HISTORIAL ---
    elif menu == "📂 Historial":
        st.title("📂 Historial Completo")
        st.dataframe(df.iloc[::-1], use_container_width=True)
