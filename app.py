import streamlit as st
import pandas as pd
from datetime import date

# Configuración de la página
st.set_page_config(page_title="Finanzas Mediamendoza", page_icon="📈")

st.title("📊 Gestión Financiera - Mediamendoza")
st.write("Carga de ingresos y egresos de forma rápida.")

# Formulario de Carga
with st.form("formulario_finanzas"):
    col1, col2 = st.columns(2)
    
    with col1:
        fecha = st.date_input("Fecha", date.today())
        tipo = st.selectbox("Tipo de Operación", ["Ingreso", "Egreso"])
        entidad = st.text_input("Cliente / Proveedor", placeholder="Ej: Gobierno de Mendoza")
    
    with col2:
        monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        categoria = st.selectbox("Categoría", [
            "Pauta Oficial", "Pauta Privada", "Google Adsense", 
            "Sueldos", "Hosting", "Servicios", "Otros"
        ])
        estado = st.radio("Estado de Pago", ["Pagado", "Pendiente"], horizontal=True)

    notas = st.text_area("Notas adicionales")
    
    submit = st.form_submit_button("Guardar Movimiento")

# Lógica al apretar el botón
if submit:
    if entidad == "" or monto == 0:
        st.error("Por favor, completa el nombre de la entidad y el monto.")
    else:
        # Aquí la app mostraría los datos cargados (luego se guardan en el Excel)
        st.success(f"¡Registrado! {tipo}: {entidad} por ${monto}")
        
        # Simulación de visualización de datos
        nuevo_dato = {
            "Fecha": fecha, "Tipo": tipo, "Entidad": entidad, 
            "Categoría": categoria, "Monto": monto, "Estado": estado
        }
        st.write("Resumen de carga:", nuevo_dato)