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
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.error("Contraseña incorrecta")

    if not st.session_state["password_correct"]:
        mostrar_logo(); st.title("🔐 Acceso Restringido")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
        # --- PARCHE DE SEGURIDAD PARA COLUMNAS NUEVAS ---
        for col in ["Vencimiento", "Cuenta", "Medio"]:
            if col not in df.columns:
                df[col] = "Sin asignar"
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas", "Vencimiento", "Cuenta", "Medio"])

    # --- LÓGICA DE SALDOS ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        df_pagados = df[df["Estado"] == "Pagado"]
        saldo_total = df_pagados[df_pagados["Tipo"] == "Ingreso"]["Monto"].sum() - df_pagados[df_pagados["Tipo"] == "Egreso"]["Monto"].sum()
        obligaciones = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        echeques_cartera = df[(df['Medio'] == 'E-Cheque') & (df['Estado'] == 'Pendiente')]['Monto'].sum()
    else:
        saldo_total = obligaciones = echeques_cartera = 0

    # --- BARRA LATERAL ---
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    st.sidebar.subheader("Navegación")
    menu = st.sidebar.radio("Ir a:", ["📊 Dashboard", "🏦 Bancos y Cuentas", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📆 Vencimientos", "📂 Historial"])
    
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO TOTAL REAL", f"$ {saldo_total:,.2f}")
    if echeques_cartera > 0:
        st.sidebar.info(f"📑 E-Cheques: $ {echeques_cartera:,.2f}")

    # --- SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo Real", f"$ {saldo_total:,.2f}")
        c2.metric("Obligaciones a Pagar", f"$ {obligaciones:,.2f}", delta_color="inverse")
        c3.metric("E-Cheques en Cartera", f"$ {echeques_cartera:,.2f}")
        
        if not df.empty:
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Saldos por Cuenta")
                cuentas = df["Cuenta"].unique()
                resumen_cuentas = []
                for c in cuentas:
                    ing = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
                    eg = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
                    resumen_cuentas.append({"Cuenta": c, "Saldo": ing - eg})
                
                if resumen_cuentas:
                    fig_c = px.bar(pd.DataFrame(resumen_cuentas), x="Cuenta", y="Saldo", color="Cuenta")
                    st.plotly_chart(fig_c, use_container_width=True)
            with col2:
                st.subheader("Gastos por Categoría")
                df_eg = df[df["Tipo"] == "Egreso"]
                if not df_eg.empty:
                    fig_p = px.pie(df_eg, values="Monto", names="Categoría", hole=0.4)
                    st.plotly_chart(fig_p, use_container_width=True)

    # --- SECCIÓN: BANCOS Y CUENTAS ---
    elif menu == "🏦 Bancos y Cuentas":
        st.title("🏦 Gestión de Cuentas")
        if not df.empty:
            cuentas = df["Cuenta"].unique()
            for c in cuentas:
                ing = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
                eg = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
                with st.expander(f"Detalle de {c}"):
                    st.metric("Saldo Actual", f"$ {ing - eg:,.2f}")
                    st.dataframe(df[df["Cuenta"] == c].iloc[::-1], use_container_width=True)

    # --- SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad / Concepto")
                # Lista de cuentas (puedes editar estas opciones)
                f_cuenta = st.selectbox("Cuenta / Banco", ["Caja Efectivo", "Banco Galicia", "Mercado Pago", "Banco Nación", "E-Cheque Terceros"])
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Sueldos", "Hosting", "Comisiones", "Impuestos", "Otros"])
                f_medio = st.selectbox("Medio", ["Transferencia", "Efectivo", "E-Cheque", "Débito"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            f_venc = st.date_input("Vencimiento", date.today())
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar"):
                nueva = pd.DataFrame([{"Fecha": f_fecha.strftime("%d/%m/%Y"), "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas, "Vencimiento": f_venc.strftime("%d/%m/%Y"), "Cuenta": f_cuenta, "Medio": f_medio}])
                df_final = pd.concat([df, nueva], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_final)
                st.toast("Guardado!")
                st.rerun()

    # --- SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidar Pendientes")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        for idx, row in pendientes.iterrows():
            with st.expander(f"{row['Tipo']} - {row['Entidad']} ($ {row['Monto']:,.2f})"):
                st.write(f"Cuenta: {row['Cuenta']} | Vence: {row['Vencimiento']}")
                if st.button(f"Confirmar", key=f"p_{idx}"):
                    df.at[idx, "Estado"] = "Pagado"
                    conn.update(worksheet="Hoja 1", data=df)
                    st.rerun()

    # --- SECCIÓN: VENCIMIENTOS ---
    elif menu == "📆 Vencimientos":
        st.title("📆 Próximos Vencimientos")
        pend = df[df["Estado"] == "Pendiente"].copy()
        if not pend.empty:
            pend['V_Date'] = pd.to_datetime(pend['Vencimiento'], format='%d/%m/%Y', errors='coerce')
            pend = pend.sort_values('V_Date')
            for _, r in pend.iterrows():
                st.write(f"**{r['Vencimiento']}** - {r['Entidad']} ($ {r['Monto']:,.2f})")

    # --- SECCIÓN: HISTORIAL ---
    elif menu == "📂 Historial":
        st.title("📂 Historial")
        st.dataframe(df.iloc[::-1], use_container_width=True)
