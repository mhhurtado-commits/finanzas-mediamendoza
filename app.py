import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date
import os

# 1. Configuración
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="📈", layout="wide")

def mostrar_logo():
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("Mediamendoza")

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
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        mostrar_logo()
        st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # --- 2. LÓGICA CONTABLE AVANZADA ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        
        # SALDO REAL (Solo lo Pagado)
        ingresos_reales = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        egresos_reales = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real = ingresos_reales - egresos_reales
        
        # PROYECCIONES (Lo Pendiente)
        a_cobrar = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        a_pagar = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
    else:
        ingresos_reales = egresos_reales = saldo_real = a_cobrar = a_pagar = 0

    # --- 3. BARRA LATERAL ---
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
    
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO CAJA (Real)", f"$ {saldo_real:,.2f}")
    
    # Mostrar alertas si hay pendientes importantes
    if a_cobrar > 0:
        st.sidebar.warning(f"📩 A Cobrar: $ {a_cobrar:,.2f}")
    if a_pagar > 0:
        st.sidebar.error(f"💸 A Pagar: $ {a_pagar:,.2f}")
    
    st.sidebar.divider()
    menu = st.sidebar.selectbox("Menú", ["📊 Dashboard", "➕ Cargar Movimiento", "📂 Ver Historial"])

    # --- 4. SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen de Caja y Proyecciones")
        
        # Fila 1: Dinero Real
        st.subheader("Estado de Caja (Efectivo)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos (Cobrados)", f"$ {ingresos_reales:,.2f}")
        c2.metric("Egresos (Pagados)", f"$ {egresos_reales:,.2f}")
        c3.metric("Saldo Real", f"$ {saldo_real:,.2f}", delta_color="normal")
        
        st.markdown("---")
        
        # Fila 2: Lo Pendiente
        st.subheader("Pendientes (Por liquidar)")
        p1, p2, p3 = st.columns(3)
        p1.metric("Por Cobrar", f"$ {a_cobrar:,.2f}", delta="Ingresos Futuros")
        p2.metric("Por Pagar", f"$ {a_pagar:,.2f}", delta="- Salida Prevista", delta_color="inverse")
        p3.metric("Saldo Proyectado", f"$ {saldo_real + a_cobrar - a_pagar:,.2f}", help="Saldo si se cobrara y pagara todo lo pendiente")

        if not df.empty:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.subheader("Gastos Reales por Categoría")
                df_pagados = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]
                if not df_pagados.empty:
                    fig_out = px.pie(df_pagados, values='Monto', names='Categoría', hole=0.4)
                    st.plotly_chart(fig_out, use_container_width=True)
                else:
                    st.info("No hay gastos pagados aún.")
            with col_graf2:
                st.subheader("Ingresos (Pagados vs Pendientes)")
                fig_comp = px.bar(df[df["Tipo"] == "Ingreso"], x='Estado', y='Monto', color='Estado', 
                                 color_discrete_map={'Pagado': '#00CC96', 'Pendiente': '#EF553B'})
                st.plotly_chart(fig_comp, use_container_width=True)

    # --- 5. SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad")
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Sueldos", "Hosting", "Servicios", "Otros"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            f_notas = st.text_area("Notas")
            if st.form_submit_button("Guardar en Mediamendoza"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ Datos incompletos.")
                else:
                    fecha_arg = f_fecha.strftime("%d/%m/%Y")
                    nueva_fila = pd.DataFrame([{"Fecha": fecha_arg, "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas}])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.toast("¡Registro guardado!")
                    st.rerun()

    # --- 6. SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial Completo")
        # Filtro rápido
        estado_filtro = st.multiselect("Filtrar por Estado:", ["Pagado", "Pendiente"], default=["Pagado", "Pendiente"])
        df_filtrado = df[df["Estado"].isin(estado_filtro)]
        st.dataframe(df_filtrado.iloc[::-1], use_container_width=True)
