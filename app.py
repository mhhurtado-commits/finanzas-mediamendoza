import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import os

# 1. Configuración de la Página
st.set_page_config(page_title="Gestión Mediamendoza", page_icon="📈", layout="wide")

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
        st.text_input("Ingresá la contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        mostrar_logo(); st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado."); return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas", "Vencimiento"])

    # --- 3. LÓGICA CONTABLE ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        # Saldo Real (Pagados)
        ing_reales = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        eg_reales = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real = ing_reales - eg_reales
        
        # Pendientes y Obligaciones
        a_cobrar = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        obligaciones = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
    else:
        ing_reales = eg_reales = saldo_real = a_cobrar = obligaciones = 0

    # --- 4. BARRA LATERAL ---
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO REAL", f"$ {saldo_real:,.2f}")
    if obligaciones > 0: st.sidebar.error(f"🗓️ Obligaciones: $ {obligaciones:,.2f}")
    st.sidebar.divider()
    menu = st.sidebar.selectbox("Menú Principal", ["📊 Dashboard", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📆 Próximos Vencimientos", "📂 Ver Historial"])

    # --- 5. SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Caja Real", f"$ {saldo_real:,.2f}")
        c2.metric("Pendiente de Cobro", f"$ {a_cobrar:,.2f}")
        c3.metric("Obligaciones a Pagar", f"$ {obligaciones:,.2f}", delta_color="inverse")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Distribución de Egresos Totales")
            df_eg = df[df["Tipo"] == "Egreso"]
            if not df_eg.empty:
                fig = px.pie(df_eg, values='Monto', names='Categoría', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Estado de Ingresos")
            df_in = df[df["Tipo"] == "Ingreso"]
            if not df_in.empty:
                fig2 = px.bar(df_in, x='Estado', y='Monto', color='Categoría', barmode='group')
                st.plotly_chart(fig2, use_container_width=True)

    # --- 6. SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        with st.form("form_carga", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                f_fecha = st.date_input("Fecha de hoy/carga", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad (Ej: Hosting, AFIP, Cliente X)")
            with col_b:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Sueldos", "Hosting", "Impuestos", "Préstamos/Planes", "Servicios", "Otros"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            # Campo nuevo para obligaciones
            f_venc = st.date_input("Fecha de Vencimiento (Si es Pendiente)", date.today())
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar Registro"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ Entidad y Monto obligatorios")
                else:
                    nueva_fila = pd.DataFrame([{
                        "Fecha": f_fecha.strftime("%d/%m/%Y"),
                        "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat,
                        "Monto": f_monto, "Estado": f_estado, "Notas": f_notas,
                        "Vencimiento": f_venc.strftime("%d/%m/%Y")
                    }])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.toast("¡Guardado exitoso!"); st.rerun()

    # --- 7. SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidar Pendientes")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        for idx, row in pendientes.iterrows():
            with st.expander(f"{row['Tipo']} - {row['Entidad']} ($ {row['Monto']:,.2f})"):
                st.write(f"Vence: {row.get('Vencimiento', 'N/A')}")
                if st.button(f"Confirmar Pago", key=f"pay_{idx}"):
                    df.at[idx, "Estado"] = "Pagado"
                    conn.update(worksheet="Hoja 1", data=df)
                    st.rerun()

    # --- 8. SECCIÓN: PRÓXIMOS VENCIMIENTOS (NUEVA) ---
    elif menu == "📆 Próximos Vencimientos":
        st.title("📆 Calendario de Obligaciones")
        st.info("Aquí ves lo que vence próximamente para organizar los pagos.")
        
        # Filtramos solo egresos pendientes
        eg_pendientes = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")].copy()
        
        if eg_pendientes.empty:
            st.success("No tenés vencimientos pendientes. ¡Día tranquilo! ☕")
        else:
            # Intentamos ordenar por fecha de vencimiento
            eg_pendientes['Venc_Date'] = pd.to_datetime(eg_pendientes['Vencimiento'], format='%d/%m/%Y', errors='coerce')
            eg_pendientes = eg_pendientes.sort_values(by='Venc_Date')
            
            for _, row in eg_pendientes.iterrows():
                # Alerta roja si ya venció
                hoy = datetime.combine(date.today(), datetime.min.time())
                dias_restantes = (row['Venc_Date'] - hoy).days
                
                if dias_restantes < 0:
                    st.error(f"VENCIDO: {row['Entidad']} - Venció el {row['Vencimiento']} ($ {row['Monto']:,.2f})")
                elif dias_restantes <= 3:
                    st.warning(f"POR VENCER ({dias_restantes} días): {row['Entidad']} - Vence el {row['Vencimiento']}")
                else:
                    st.info(f"A tiempo: {row['Entidad']} - Vence el {row['Vencimiento']}")

    # --- 9. SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial")
        st.dataframe(df.iloc[::-1], use_container_width=True)
