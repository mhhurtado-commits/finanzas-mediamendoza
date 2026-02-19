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
        else: st.error("Contraseña incorrecta")
    if not st.session_state["password_correct"]:
        mostrar_logo(); st.title("🔐 Acceso Restringido")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
        # PARCHE: Asegurar que existan todas las columnas para evitar KeyError
        columnas_necesarias = ["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas", "Vencimiento", "Cuenta", "Medio"]
        for col in columnas_necesarias:
            if col not in df.columns:
                df[col] = "Sin asignar"
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas", "Vencimiento", "Cuenta", "Medio"])

    # --- LÓGICA DE SALDOS Y MÉTRICAS ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        
        # 1. Saldo Real (Lo que ya pasó)
        ing_pagados = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        eg_pagados = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real_total = ing_pagados - eg_pagados
        
        # 2. Pendientes (Lo que va a pasar)
        a_cobrar_pend = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        a_pagar_pend = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        
        # 3. Instrumentos específicos
        echeques_cartera = df[(df['Medio'] == 'E-Cheque') & (df['Estado'] == 'Pendiente')]['Monto'].sum()
    else:
        saldo_real_total = a_cobrar_pend = a_pagar_pend = echeques_cartera = 0

    # --- BARRA LATERAL ---
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "🏦 Bancos y Cuentas", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📆 Vencimientos", "📂 Historial"])
    
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO CAJA TOTAL", f"$ {saldo_real_total:,.2f}")
    if a_cobrar_pend > 0: st.sidebar.warning(f"📩 Pend. Cobro: $ {a_cobrar_pend:,.2f}")
    
    # --- SECCIÓN: DASHBOARD REPARADO ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero Integral")
        
        # Fila 1: Métricas Principales
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Efectivo Real (Caja)", f"$ {saldo_real_total:,.2f}")
        m2.metric("Pendiente de Cobro", f"$ {a_cobrar_pend:,.2f}", delta="Ingreso futuro")
        m3.metric("Obligaciones (Deuda)", f"$ {a_pagar_pend:,.2f}", delta="- Egreso futuro", delta_color="inverse")
        m4.metric("E-Cheques en Mano", f"$ {echeques_cartera:,.2f}")
        
        st.markdown("---")
        
        if not df.empty:
            # Fila 2: Gráficos Operativos
            g1, g2 = st.columns(2)
            
            with g1:
                st.subheader("🏦 Saldos Reales por Cuenta")
                cuentas = df["Cuenta"].unique()
                resumen_cuentas = []
                for c in cuentas:
                    i = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
                    e = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
                    if (i-e) != 0: resumen_cuentas.append({"Cuenta": c, "Saldo": i - e})
                
                if resumen_cuentas:
                    fig_cuentas = px.bar(pd.DataFrame(resumen_cuentas), x="Cuenta", y="Saldo", color="Cuenta", text_auto='.2s')
                    st.plotly_chart(fig_cuentas, use_container_width=True)
                else: st.info("No hay saldos en cuentas para mostrar.")

            with g2:
                st.subheader("📈 Ingresos: Cobrados vs Pendientes")
                df_ingresos = df[df["Tipo"] == "Ingreso"]
                if not df_ingresos.empty:
                    fig_ing = px.bar(df_ingresos, x='Estado', y='Monto', color='Categoría', barmode='group')
                    st.plotly_chart(fig_ing, use_container_width=True)
                else: st.info("No hay registros de ingresos.")

            # Fila 3: Análisis de Gastos
            st.markdown("---")
            st.subheader("💸 Distribución de Egresos por Categoría (Total)")
            df_egresos = df[df["Tipo"] == "Egreso"]
            if not df_egresos.empty:
                fig_gastos = px.pie(df_egresos, values="Monto", names="Categoría", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_gastos, use_container_width=True)

    # --- SECCIÓN: BANCOS Y CUENTAS ---
    elif menu == "🏦 Bancos y Cuentas":
        st.title("🏦 Estado de Cuentas")
        cuentas = df["Cuenta"].unique()
        for c in cuentas:
            i = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
            e = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
            with st.expander(f"Cuenta: {c}"):
                st.metric("Saldo Disponible", f"$ {i - e:,.2f}")
                st.dataframe(df[df["Cuenta"] == c].iloc[::-1], use_container_width=True)

    # --- SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        with st.form("form_carga", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad / Concepto")
                f_cuenta = st.selectbox("Cuenta / Banco", ["Caja Efectivo", "Banco Galicia", "Mercado Pago", "Banco Nación", "E-Cheque Terceros"])
            with col_b:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Sueldos", "Hosting", "Comisiones", "Impuestos", "Servicios", "Otros"])
                f_medio = st.selectbox("Medio", ["Transferencia", "Efectivo", "E-Cheque", "Débito Automático"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            f_venc = st.date_input("Vencimiento", date.today())
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar Registro"):
                nueva = pd.DataFrame([{"Fecha": f_fecha.strftime("%d/%m/%Y"), "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas, "Vencimiento": f_venc.strftime("%d/%m/%Y"), "Cuenta": f_cuenta, "Medio": f_medio}])
                df_final = pd.concat([df, nueva], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_final)
                st.toast("✅ Registro Exitoso"); st.rerun()

    # --- SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidación de Movimientos")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        if pendientes.empty:
            st.success("No hay pendientes.")
        else:
            for idx, row in pendientes.iterrows():
                with st.expander(f"{row['Tipo']} - {row['Entidad']} ($ {row['Monto']:,.2f})"):
                    st.write(f"Vence: {row['Vencimiento']} | Cuenta: {row['Cuenta']}")
                    if st.button(f"Confirmar Liquidación", key=f"btn_{idx}"):
                        df.at[idx, "Estado"] = "Pagado"
                        conn.update(worksheet="Hoja 1", data=df)
                        st.rerun()

    # --- SECCIÓN: VENCIMIENTOS ---
    elif menu == "📆 Vencimientos":
        st.title("📆 Calendario de Vencimientos")
        eg_pend = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")].copy()
        if eg_pend.empty:
            st.success("Nada vence pronto.")
        else:
            eg_pend['V_Date'] = pd.to_datetime(eg_pend['Vencimiento'], format='%d/%m/%Y', errors='coerce')
            eg_pend = eg_pend.sort_values('V_Date')
            for _, r in eg_pend.iterrows():
                st.write(f"**{r['Vencimiento']}** - {r['Entidad']} ($ {r['Monto']:,.2f}) en {r['Cuenta']}")

    # --- SECCIÓN: HISTORIAL ---
    elif menu == "📂 Historial":
        st.title("📂 Historial")
        st.dataframe(df.iloc[::-1], use_container_width=True)
