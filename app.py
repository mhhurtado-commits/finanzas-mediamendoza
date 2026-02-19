import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
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

    # --- SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Efectivo Real", f"$ {saldo_real_total:,.2f}")
        m2.metric("A Cobrar", f"$ {a_cobrar_pend:,.2f}")
        m3.metric("A Pagar", f"$ {a_pagar_pend:,.2f}", delta_color="inverse")
        m4.metric("E-Cheques", f"$ {echeques_cartera:,.2f}")
        
        if not df.empty:
            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("🏦 Dinero por Cuenta")
                cuentas = df["Cuenta"].unique()
                resumen_cuentas = []
                for c in cuentas:
                    i = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
                    e = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
                    if (i-e) != 0: resumen_cuentas.append({"Cuenta": c, "Saldo": i - e})
                if resumen_cuentas:
                    st.plotly_chart(px.bar(pd.DataFrame(resumen_cuentas), x="Cuenta", y="Saldo", color="Cuenta"), use_container_width=True)
            with g2:
                st.subheader("💸 Gastos por Categoría")
                df_eg = df[df["Tipo"] == "Egreso"]
                if not df_eg.empty:
                    st.plotly_chart(px.pie(df_eg, values="Monto", names="Categoría", hole=0.4), use_container_width=True)

    # --- SECCIÓN: VENCIMIENTOS (CON ALERTAS RESTAURADAS) ---
    elif menu == "📆 Vencimientos":
        st.title("📆 Control de Próximos Vencimientos")
        
        # Filtramos solo lo que está pendiente (Ingresos y Egresos)
        pend = df[df["Estado"] == "Pendiente"].copy()
        
        if pend.empty:
            st.success("🎉 ¡Excelente! No tenés vencimientos pendientes por ahora.")
        else:
            # Convertimos fecha de vencimiento para comparar
            pend['V_Date'] = pd.to_datetime(pend['Vencimiento'], format='%d/%m/%Y', errors='coerce').dt.date
            pend = pend.sort_values('V_Date')
            hoy = date.today()

            col_izq, col_der = st.columns(2)
            
            with col_izq:
                st.subheader("📉 Deudas y Egresos")
                eg_pend = pend[pend["Tipo"] == "Egreso"]
                if eg_pend.empty: st.write("Sin deudas pendientes.")
                for _, r in eg_pend.iterrows():
                    dias_faltantes = (r['V_Date'] - hoy).days if not pd.isnull(r['V_Date']) else 999
                    
                    label = f"{r['Vencimiento']} - {r['Entidad']} ($ {r['Monto']:,.2f})"
                    
                    if dias_faltantes < 0:
                        st.error(f"🚨 **VENCIDO**: {label}")
                    elif dias_faltantes <= 3:
                        st.warning(f"⏳ **VENCE PRONTO** ({dias_faltantes} días): {label}")
                    else:
                        st.info(f"✅ **A tiempo**: {label}")

            with col_der:
                st.subheader("📈 Cobros Pendientes")
                in_pend = pend[pend["Tipo"] == "Ingreso"]
                if in_pend.empty: st.write("Sin cobros pendientes.")
                for _, r in in_pend.iterrows():
                    dias_faltantes = (r['V_Date'] - hoy).days if not pd.isnull(r['V_Date']) else 999
                    label = f"{r['Vencimiento']} - {r['Entidad']} ($ {r['Monto']:,.2f})"
                    
                    if dias_faltantes < 0:
                        st.error(f"🚩 **RECLAMAR PAGO (Atrasado)**: {label}")
                    else:
                        st.success(f"💰 **A Cobrar**: {label}")

    # --- SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        categorias_dict = {
            "Ingreso": ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Otros Ingresos"],
            "Egreso": ["Sueldos", "Hosting", "Servicios", "Impuestos", "Comisiones", "Marketing", "Otros"]
        }
        f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_entidad = st.text_input("Entidad / Concepto")
                f_cat = st.selectbox("Categoría", categorias_dict[f_tipo])
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0)
                f_cuenta = st.selectbox("Cuenta", ["Caja Efectivo", "Banco Galicia", "Mercado Pago", "Banco Nación"])
                f_medio = st.selectbox("Medio", ["Transferencia", "Efectivo", "E-Cheque", "Débito"])
            
            f_venc = st.date_input("Vencimiento", date.today())
            f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            if st.form_submit_button("💾 Guardar"):
                nueva = pd.DataFrame([{"Fecha": f_fecha.strftime("%d/%m/%Y"), "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Vencimiento": f_venc.strftime("%d/%m/%Y"), "Cuenta": f_cuenta, "Medio": f_medio}])
                df_final = pd.concat([df, nueva], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_final)
                st.success("Guardado!"); st.rerun()

    # --- OTRAS SECCIONES ---
    elif menu == "🏦 Bancos y Cuentas":
        st.title("🏦 Bancos")
        for c in df["Cuenta"].unique():
            i = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Ingreso")]["Monto"].sum()
            e = df[(df["Cuenta"] == c) & (df["Estado"] == "Pagado") & (df["Tipo"] == "Egreso")]["Monto"].sum()
            st.metric(c, f"$ {i-e:,.2f}")

    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidar")
        for idx, row in df[df["Estado"] == "Pendiente"].iterrows():
            if st.button(f"Liquidar {row['Entidad']} ($ {row['Monto']})", key=idx):
                df.at[idx, "Estado"] = "Pagado"
                conn.update(worksheet="Hoja 1", data=df)
                st.rerun()

    elif menu == "📂 Historial":
        st.title("📂 Historial")
        st.dataframe(df.iloc[::-1], use_container_width=True)
