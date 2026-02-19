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
        st.text_input("Ingresá la contraseña del sistema", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        mostrar_logo()
        st.text_input("Contraseña incorrecta", type="password", on_change=password_entered, key="password")
        st.error("😕 Acceso denegado.")
        return False
    return True

# --- INICIO DE LA APP ---
if check_password():
    # 2. Conexión y Carga de Datos (ttl=0 para ver cambios al instante)
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Entidad", "Categoría", "Monto", "Estado", "Notas"])

    # 3. Lógica Contable (Saldo Real vs Pendientes)
    if not df.empty:
        # Asegurar que Monto sea numérico
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        
        # Dinero en mano (Pagado)
        ingresos_reales = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        egresos_reales = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]["Monto"].sum()
        saldo_real = ingresos_reales - egresos_reales
        
        # Dinero en espera (Pendiente)
        a_cobrar = df[(df["Tipo"] == "Ingreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
        a_pagar = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pendiente")]["Monto"].sum()
    else:
        ingresos_reales = egresos_reales = saldo_real = a_cobrar = a_pagar = 0

    # 4. Barra Lateral (Sidebar)
    mostrar_logo(en_sidebar=True)
    st.sidebar.divider()
    st.sidebar.metric("💰 SALDO CAJA (Real)", f"$ {saldo_real:,.2f}")
    
    if a_cobrar > 0: st.sidebar.warning(f"📩 A Cobrar: $ {a_cobrar:,.2f}")
    if a_pagar > 0: st.sidebar.error(f"💸 A Pagar: $ {a_pagar:,.2f}")
    
    st.sidebar.divider()
    menu = st.sidebar.selectbox("Menú Principal", ["📊 Dashboard", "➕ Cargar Movimiento", "📝 Gestionar Pendientes", "📂 Ver Historial"])
    st.sidebar.info(f"Fecha: {date.today().strftime('%d/%m/%Y')}")

    # --- 5. SECCIÓN: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Resumen de Finanzas")
        
        # Fila de métricas reales
        st.subheader("Estado de Caja Real")
        c1, c2, c3 = st.columns(3)
        c1.metric("Cobrado", f"$ {ingresos_reales:,.2f}")
        c2.metric("Pagado", f"$ {egresos_reales:,.2f}")
        c3.metric("Saldo Real", f"$ {saldo_real:,.2f}")
        
        st.markdown("---")
        
        # Fila de métricas proyectadas
        st.subheader("Proyecciones (Pendientes)")
        p1, p2, p3 = st.columns(3)
        p1.metric("Pendiente de Cobro", f"$ {a_cobrar:,.2f}", delta="Ingreso futuro")
        p2.metric("Pendiente de Pago", f"$ {a_pagar:,.2f}", delta="- Salida futura", delta_color="inverse")
        p3.metric("Saldo Proyectado", f"$ {saldo_real + a_cobrar - a_pagar:,.2f}", help="Si se liquidara todo lo pendiente")

        if not df.empty:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.subheader("Gastos Reales por Categoría")
                df_pag_eg = df[(df["Tipo"] == "Egreso") & (df["Estado"] == "Pagado")]
                if not df_pag_eg.empty:
                    fig_out = px.pie(df_pag_eg, values='Monto', names='Categoría', hole=0.4)
                    st.plotly_chart(fig_out, use_container_width=True)
                else: st.info("Sin gastos pagados.")
            with col_graf2:
                st.subheader("Estado de Cobros")
                df_ing = df[df["Tipo"] == "Ingreso"]
                if not df_ing.empty:
                    fig_in = px.bar(df_ing, x='Estado', y='Monto', color='Estado', barmode='group')
                    st.plotly_chart(fig_in, use_container_width=True)

    # --- 6. SECCIÓN: CARGA ---
    elif menu == "➕ Cargar Movimiento":
        st.title("➕ Cargar Nuevo Movimiento")
        with st.form("form_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_fecha = st.date_input("Fecha", date.today())
                f_tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                f_entidad = st.text_input("Entidad (Cliente/Proveedor)")
            with c2:
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                f_cat = st.selectbox("Categoría", ["Pauta Oficial", "Pauta Privada", "Google Adsense", "Sueldos", "Hosting", "Servicios", "Otros"])
                f_estado = st.radio("Estado Inicial", ["Pagado", "Pendiente"], horizontal=True)
            f_notas = st.text_area("Notas")
            
            if st.form_submit_button("Guardar Registro"):
                if f_entidad == "" or f_monto <= 0:
                    st.error("⚠️ Entidad y Monto son obligatorios.")
                else:
                    fecha_arg = f_fecha.strftime("%d/%m/%Y")
                    nueva_fila = pd.DataFrame([{"Fecha": fecha_arg, "Tipo": f_tipo, "Entidad": f_entidad, "Categoría": f_cat, "Monto": f_monto, "Estado": f_estado, "Notas": f_notas}])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.toast("¡Guardado!", icon="✅")
                    st.rerun()

    # --- 7. SECCIÓN: GESTIONAR PENDIENTES ---
    elif menu == "📝 Gestionar Pendientes":
        st.title("📝 Gestión de Cobros y Pagos Pendientes")
        st.info("Utilizá esta sección para pasar movimientos de 'Pendiente' a 'Pagado'.")
        
        pendientes = df[df["Estado"] == "Pendiente"].copy()
        
        if pendientes.empty:
            st.success("¡Excelente! No tenés nada pendiente por ahora. 🎉")
        else:
            for index, row in pendientes.iterrows():
                # Icono según tipo
                icono = "🟢 [COBRO]" if row['Tipo'] == "Ingreso" else "🔴 [PAGO]"
                with st.expander(f"{icono} {row['Entidad']} - $ {row['Monto']:,.2f} ({row['Fecha']})"):
                    st.write(f"**Categoría:** {row['Categoría']}")
                    st.write(f"**Notas:** {row['Notas']}")
                    if st.button(f"Confirmar Liquidación de {row['Entidad']}", key=f"btn_{index}"):
                        # Cambiar estado en el DataFrame
                        df.at[index, "Estado"] = "Pagado"
                        # Actualizar Google Sheets
                        conn.update(worksheet="Hoja 1", data=df)
                        st.balloons()
                        st.success(f"¡{row['Entidad']} actualizado a Pagado!")
                        st.rerun()

    # --- 8. SECCIÓN: HISTORIAL ---
    elif menu == "📂 Ver Historial":
        st.title("📂 Historial de Movimientos")
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True)
        else:
            st.info("Aún no hay registros.")
