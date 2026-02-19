import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# Configuración visual de la App
st.set_page_config(page_title="Finanzas Mediamendoza", page_icon="📈")

# Título y Estética del Diario
st.title("📊 Control Financiero - Mediamendoza.com")
st.markdown("---")

# URL de tu Google Sheet (Asegúrate de que el permiso esté en "Cualquier persona con el enlace" como Editor)
URL_SHEET = "https://docs.google.com/spreadsheets/d/1ryZuW0j3_zC3a2ci5jyXJcis7-Tz9iuPyIUhXbcRP3U/edit?usp=sharing"

# Establecer conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Intentar leer los datos existentes
try:
    df = conn.read(spreadsheet=URL_SHEET, worksheet="Hoja 1")
except Exception as e:
    st.error("No se pudo leer la planilla. Verificá que el nombre de la pestaña sea 'Hoja 1'.")
    df = pd.DataFrame()

# --- FORMULARIO DE CARGA ---
st.subheader("📝 Cargar Nuevo Movimiento")
with st.form("formulario_finanzas"):
    col1, col2 = st.columns(2)
    
    with col1:
        fecha = st.date_input("Fecha de Operación", date.today())
        tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
        entidad = st.text_input("Entidad (Cliente o Proveedor)", placeholder="Ej: Google / Gobierno Mza")
    
    with col2:
        monto = st.number_input("Monto Total ($)", min_value=0.0, format="%.2f")
        categoria = st.selectbox("Categoría", [
            "Pauta Oficial", "Pauta Privada", "Google Adsense", 
            "Sueldos", "Hosting", "Servicios", "Otros"
        ])
        estado = st.radio("Estado del Pago", ["Pagado", "Pendiente"], horizontal=True)

    notas = st.text_area("Notas o Nro de Comprobante")
    
    boton_guardar = st.form_submit_button("💾 Guardar en Base de Datos")

# --- LÓGICA DE GUARDADO ---
if boton_guardar:
    if entidad == "" or monto <= 0:
        st.warning("⚠️ Por favor, completá el nombre de la entidad y un monto válido.")
    else:
        # Crear la nueva fila con los datos del formulario
        nueva_fila = pd.DataFrame([{
            "Fecha": str(fecha),
            "Tipo": tipo,
            "Entidad": entidad,
            "Categoría": categoria,
            "Monto": monto,
            "Estado": estado,
            "Notas": notas
        }])
        
        # Combinar con los datos actuales
        df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
        
        try:
            # Subir a Google Sheets
            conn.update(spreadsheet=URL_SHEET, worksheet="Hoja 1", data=df_actualizado)
            st.success("✅ ¡Datos guardados con éxito en la planilla!")
            st.balloons()
            # Botón para refrescar y ver los cambios
            st.button("Actualizar Vista")
        except Exception as e:
            st.error(f"❌ Error al intentar guardar: {e}")

# --- VISTA DE DATOS ---
st.markdown("---")
st.subheader("📋 Últimos Movimientos Registrados")
if not df.empty:
    # Mostramos los últimos 10 registros
    st.dataframe(df.tail(10), use_container_width=True)
else:
    st.info("Todavía no hay movimientos registrados.")
