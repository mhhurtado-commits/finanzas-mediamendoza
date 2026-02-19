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

    # --- LÓGICA CONTABLE ---
    if not df.empty:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        ing_reales = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        eg_reales = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real = ing_reales - eg_reales
        a_cobrar = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        obligaciones = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
    else:
        ing_reales = eg_reales = saldo_real = a_cobrar = obligaciones = 0

    # --- 4. BARRA LATERAL (NUEVO MENÚ VISIBLE) ---
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    
    # MENÚ TIPO RADIO (Siempre a la vista)
    st.sidebar.subheader("Navegación")
    menu = st.sidebar.radio(
        "Ir a:",
        ["📊 Dashboard", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📆 Próximos Vencimientos", "📂 Ver Historial"],
        index=0
    )
    
    st.sidebar.divider()
    st.sidebar.subheader("Estado de Caja")
    st.sidebar.metric("💰 SALDO REAL", f"$ {saldo_real:,.2f}")
    if obligaciones > 0: 
        st.sidebar.error(f"⚠️ Obligaciones: $ {obligaciones:,.2f}")
    
    st.sidebar.divider()
    st.sidebar.info(f"📅 {date.today().strftime('%d/%m/%Y')}")

    # --- SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen General")
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo en Caja", f"$ {saldo_real:,.2f}")
        c2.metric("Pendiente de Cobro", f"$ {a_cobrar:,.2f}")
        c3.metric("Obligaciones Pendientes", f"$ {obligaciones:,.2f}", delta_color="inverse")
        
        st.markdown("---")
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Egresos por Categoría")
                df_eg = df[df["Tipo"] == "Egreso"]
                if not df_eg.empty:
                    fig = px.pie(df_eg, values='Monto', names='Categoría', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("Ingresos: Pagado vs Pendiente")
                df_in = df[df["Tipo"] == "Ingreso"]
                if not df_in.empty:
                    fig2 = px.bar(df_in, x='Estado', y='Monto', color='Categoría', barmode='group')
                    st.plotly_chart(fig2, use_container_width=True)

    # --- SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Nuevo Registro")
        with st.form("form_carga", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                f_fecha = st.date_input("Fecha de carga", date.today())
                f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad / Concepto")
            with col_b:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Sueldos", "Hosting", "Impuestos", "Préstamos/Planes", "Servicios", "Otros"])
                f_estado = st.radio("Estado", ["Pagado", "Pendiente"], horizontal=True)
            
            f_venc = st.date_input("Fecha de Vencimiento", date.today())
            st.caption(f"Vencimiento seleccionado: {f_venc.strftime('%d/%m/%Y')}")
            f_notas = st.text_area("Notas / Detalles")
            
            if st.form_submit_button("💾 Guardar en Base de Datos"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ Completá Entidad y Monto")
                else:
                    nueva_fila = pd.DataFrame([{
                        "Fecha": f_fecha.strftime("%d/%m/%Y"),
                        "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat,
                        "Monto": f_monto, "Estado": f_estado, "Notas": f_notas,
                        "Vencimiento": f_venc.strftime("%d/%m/%Y")
                    }])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.toast("✅ Registro guardado"); st.rerun()

    # --- SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Liquidar Pendientes")
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        if pendientes.empty:
            st.success("No hay movimientos pendientes de pago o cobro.")
        else:
            for idx, row in pendientes.iterrows():
                with st.expander(f"{row['Tipo']} - {row['Entidad']} ($ {row['Monto']:,.2f})"):
                    st.write(f"Vencimiento original: {row.get('Vencimiento', 'N/A')}")
                    if st.button(f"Confirmar Liquidación", key=f"pay_{idx}"):
                        df.at[idx, "Estado"] = "Pagado"
                        conn.update(worksheet="Hoja 1", data=df)
                        st.rerun()

    # --- SECCIÓN: PRÓXIMOS VENCIMIENTOS ---
    elif menu == "📆 Próximos Vencimientos":
        st.title("📆 Calendario de Obligaciones")
        eg_pendientes = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")].copy()
        if eg_pendientes.empty:
            st.success("Todo al día.")
        else:
            eg_pendientes['Venc_Date'] = pd.to_datetime(eg_pendientes['Vencimiento'], format='%d/%m/%Y', errors='coerce')
            eg_pendientes = eg_pendientes.sort_values(by='Venc_Date')
            for _, row in eg_pendientes.iterrows():
                hoy = datetime.combine(date.today(), datetime.min.time())
                dias = (row['Venc_Date'] - hoy).days
                if dias < 0: st.error(f"❌ VENCIDO ({row['Vencimiento']}): {row['Entidad']} - $ {row['Monto']:,.2f}")
                elif dias <= 3: st.warning(f"⏳ POR VENCER ({dias} días): {row['Entidad']} ($ {row['Monto']:,.2f})")
                else: st.info(f"✅ A tiempo: {row['Entidad']} - Vence {row['Vencimiento']}")

    # --- SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial Completo")
        st.dataframe(df.iloc[::-1], use_container_width=True)
