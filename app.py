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
        columnas_necesarias = ["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas", "Vencimiento", "Cuenta", "Medio"]
        for col in columnas_necesarias:
            if col not in df.columns:
                df[col] = "Sin asignar"
    except Exception:
        df = pd.DataFrame(columns=columnas_necesarias)

    # --- LÓGICA DE SALDOS ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        ing_pag = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        eg_pag = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real_total = ing_pag - eg_pag
        a_cobrar_pend = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        a_pagar_pend = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        echeques_cartera = df[(df['Medio'] == 'E-Cheque') & (df['Estado'] == 'Pendiente')]['Monto'].sum()
    else:
        saldo_real_total = a_cobrar_pend = a_pagar_pend = echeques_cartera = 0

    # --- BARRA LATERAL ---
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "🏦 Bancos y Cuentas", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📆 Vencimientos", "📂 Historial"])
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO CAJA TOTAL", f"$ {saldo_real_total:,.2f}")

    # --- SECCIÓN: DASHBOARD (REDISEÑADO) ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero Control 360")
        
        # FILA 1: Métricas de Impacto
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Efectivo Real (Caja)", f"$ {saldo_real_total:,.2f}")
        m2.metric("Pendiente de Cobro", f"$ {a_cobrar_pend:,.2f}")
        m3.metric("Obligaciones a Pagar", f"$ {a_pagar_pend:,.2f}", delta_color="inverse")
        m4.metric("E-Cheques en Cartera", f"$ {echeques_cartera:,.2f}")
        
        st.markdown("---")
        
        if not df.empty:
            # FILA 2: Análisis de Ingresos y Bancos
            g1, g2 = st.columns(2)
            
            with g1:
                st.subheader("🏦 Dinero por Cuenta (Pagado)")
                cuentas = df["Cuenta"].unique()
                resumen_cuentas = []
                for c in cuentas:
                    i = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
                    e = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
                    if (i-e) != 0: resumen_cuentas.append({"Cuenta": c, "Saldo": i - e})
                if resumen_cuentas:
                    fig_c = px.bar(pd.DataFrame(resumen_cuentas), x="Cuenta", y="Saldo", color="Cuenta", template="plotly_dark")
                    st.plotly_chart(fig_c, use_container_width=True)
                else: st.info("Sin movimientos pagados.")

            with g2:
                st.subheader("📈 Cobros: Real vs Pendiente")
                df_ing = df[df["Tipo"] == "Ingreso"]
                if not df_ing.empty:
                    fig_ing = px.bar(df_ing, x='Estado', y='Monto', color='Categoría', barmode='group')
                    st.plotly_chart(fig_ing, use_container_width=True)

            # FILA 3: EL GRÁFICO DE GASTOS (Restaurado)
            st.markdown("---")
            st.subheader("💸 Distribución de Gastos (Egresos Totales)")
            df_eg = df[df["Tipo"] == "Egreso"]
            if not df_eg.empty:
                # Usamos un gráfico de torta para ver la proporción de gastos
                fig_eg = px.pie(df_eg, values="Monto", names="Categoría", hole=0.4, 
                               color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_eg, use_container_width=True)
            else:
                st.info("No hay egresos registrados para mostrar el análisis de gastos.")

    # --- SECCIÓN: CARGA (INTERACTIVA) ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        categorias_dict = {
            "Ingreso": ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Venta de Activos", "Otros Ingresos"],
            "Egreso": ["Sueldos", "Hosting / Dominios", "Servicios (Luz, Internet)", "Impuestos (AFIP, Rentas)", "Comisiones Bancarias", "Préstamos/Cuotas", "Marketing/Publicidad", "Otros Gastos"]
        }
        f_tipo = st.selectbox("1. Seleccioná el Tipo", ["Ingreso", "Egreso"])
        
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha de carga", date.today())
                f_entidad = st.text_input("Entidad / Concepto")
                f_cat = st.selectbox("Categoría", categorias_dict[f_tipo])
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cuenta = st.selectbox("Cuenta / Banco", ["Caja Efectivo", "Banco Galicia", "Mercado Pago", "Banco Nación", "E-Cheque Terceros"])
                f_medio = st.selectbox("Medio", ["Transferencia", "Efectivo", "E-Cheque", "Débito Automático"])
            
            st.divider()
            c3, c4 = st.columns(2)
            with c3: f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            with c4: f_venc = st.date_input("Vencimiento", date.today())
            f_notas = st.text_area("Notas adicionales")

            if st.form_submit_button("💾 Guardar Registro"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ Entidad y Monto requeridos")
                else:
                    nueva = pd.DataFrame([{"Fecha": f_fecha.strftime("%d/%m/%Y"), "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas, "Vencimiento": f_venc.strftime("%d/%m/%Y"), "Cuenta": f_cuenta, "Medio": f_medio}])
                    df_final = pd.concat([df, nueva], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.success("✅ Guardado correctamente")
                    st.rerun()

    # --- RESTO DE SECCIONES (BANCOS, PENDIENTES, HISTORIAL) ---
    elif menu == "🏦 Bancos y Cuentas":
        st.title("🏦 Estado de Cuentas")
        cuentas = df["Cuenta"].unique()
        for c in cuentas:
            i = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
            e = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
            with st.expander(f"Cuenta: {c} | Saldo: $ {i-e:,.2f}"):
                st.dataframe(df[df["Cuenta"] == c].iloc[::-1], use_container_width=True)

    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidar Pendientes")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        if pendientes.empty: st.success("Todo al día.")
        else:
            for idx, row in pendientes.iterrows():
                with st.expander(f"{row['Tipo']} - {row['Entidad']} ($ {row['Monto']:,.2f})"):
                    if st.button(f"Confirmar Pago/Cobro", key=f"btn_{idx}"):
                        df.at[idx, "Estado"] = "Pagado"
                        conn.update(worksheet="Hoja 1", data=df)
                        st.rerun()

    elif menu == "📆 Vencimientos":
        st.title("📆 Próximos Vencimientos")
        eg_pend = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")].copy()
        if not eg_pend.empty:
            eg_pend['V_Date'] = pd.to_datetime(eg_pend['Vencimiento'], format='%d/%m/%Y', errors='coerce')
            eg_pend = eg_pend.sort_values('V_Date')
            for _, r in eg_pend.iterrows():
                st.write(f"**{r['Vencimiento']}** - {r['Entidad']} ($ {r['Monto']:,.2f})")

    elif menu == "📂 Historial":
        st.title("📂 Historial")
        st.dataframe(df.iloc[::-1], use_container_width=True)
