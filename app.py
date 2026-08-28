import streamlit as st
import os
import smtplib
from email.message import EmailMessage
from pypdf import PdfMerger

# Configuración de la página web
st.set_page_config(page_title="Sistema Contable - Hospital Lagomaggiore", page_icon="📁", layout="centered")

# --- CREDENCIALES DE EMPLEADOS ---
# Podés modificar o agregar usuarios y contraseñas según tu equipo
USUARIOS = {
    "empleado1":"clave123",
    "empleado2":"clave456",
    "cristiano":"admin2026"
}

# Configuración de Correo (Hospital y Estudio)
CORREO_DESTINO = "facturaslagomaggiore@gmail.com"
CORREO_ESTUDIO = "tucorreo@estudio.com"
ESTUDIO_DE_CONTRASEÑAS = "tu_contraseña_de_aplicacion_gmail"

CARPETA_TEMPORAL = "./temp_docs"
if not os.path.exists(CARPETA_TEMPORAL):
    os.makedirs(CARPETA_TEMPORAL)

# --- SISTEMA DE INICIO DE SESIÓN ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.subheader("🔒 Acceso al Sistema - Estudio Contable")
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar"):
            if usuario in USUARIOS and USUARIOS[usuario] == clave:
                st.session_state.autenticado = True
                st.session_state.usuario_actual = usuario
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
        return False
    return True

# Ejecutar control de sesión
if verificar_login():
    st.sidebar.success(f"Conectado como: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📁 Sistema de Facturación y Unificación")
    st.write("Herramienta para procesamiento y envío de documentación.")

    # Área de carga de archivos
    archivos_subidos = st.file_uploader("Subir archivos PDF de los clientes", type=["pdf"], accept_multiple_files=True)

    if archivos_subidos:
        st.write(f"Archivos cargados exitosamente: {len(archivos_subidos)}")
        
        if st.button("Procesar y Enviar"):
            merger = PdfMerger()
            rutas_temporales = []

            for archivo in archivos_subidos:
                ruta_temp = os.path.join(CARPETA_TEMPORAL, archivo.name)
                with open(ruta_temp, "wb") as f:
                    f.write(archivo.getbuffer())
                merger.append(ruta_temp)
                rutas_temporales.append(ruta_temp)

            archivo_salida = os.path.join(CARPETA_TEMPORAL, "Documentacion_Unificada.pdf")
            merger.write(archivo_salida)
            merger.close()

            st.success("¡Los archivos se unificaron correctamente!")
            
            with open(archivo_salida, "rb") as f:
                st.download_button("Descargar PDF Unificado", f, file_name="Documentacion_Unificada.pdf", mime="application/pdf")

            # Limpieza de temporales al terminar
            for ruta in rutas_temporales:
                if os.path.exists(ruta):
                    os.remove(ruta)
