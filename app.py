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
    "empleado1": "clave123",
    "empleado2": "clave456",
    "cristian": "admin2026"
}

# Configuración de Correo (Hospital y Estudio)
CORREO_DESTINO = "facturaslagomaggiore@gmail.com"
CORREO_ESTUDIO = "tucorreo@estudio.com"
PASSWORD_ESTUDIO = "tu_password_de_aplicacion_gmail"

CARPETA_TEMPORAL = "./temp_docs"
if not os.path.exists(CARPETA_TEMPORAL):
    os.makedirs(CARPETA_TEMPORAL)

# --- SISTEMA DE LOGIN ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.subheader("🔐 Acceso Restringido - Estudio Contable Garro")
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar"):
            if usuario in USUARIOS and USUARIOS[usuario] == password:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
        return False
    return True

# --- INTERFAZ PRINCIPAL DE LA APP ---
def main_app():
    st.title("📊 Procesador y Unificador de Facturación")
    st.write(f"Usuario conectado: **{st.session_state.usuario}**. Sube los archivos del cliente para unificarlos y enviarlos al hospital.")

    with st.sidebar:
        st.header("Sesión Activa")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()

    # Formulario de carga
    nombre_cliente = st.text_input("Nombre y Apellido o CUIT del Cliente (Ej: JuanPerez)", placeholder="Sin espacios ni caracteres raros")
    
    st.info("ℹ️ **Requisitos:** La factura y el monotributo son obligatorios. La constancia de ATM se suma si está disponible.")
    
    archivo_factura = st.file_uploader("1. Subir Factura (Obligatorio) (PDF)", type=["pdf"])
    archivo_monotributo = st.file_uploader("2. Subir Constancia de Monotributo (Obligatorio) (PDF)", type=["pdf"])
    archivo_atm = st.file_uploader("3. Subir Libre de Deuda / Constancia ATM (Opcional) (PDF)", type=["pdf"])

    if st.button("🚀 Procesar, Unificar y Enviar al Hospital"):
        if not nombre_cliente:
            st.warning("Por favor, ingresa el nombre o CUIT del cliente para identificar los archivos.")
        elif not archivo_factura or not archivo_monotributo:
            st.error("Faltan documentos obligatorios (Factura o Constancia de Monotributo).")
        else:
            with st.spinner("Procesando documentación..."):
                try:
                    rutas_archivos = []
                    
                    # Guardar temporalmente
                    path_factura = os.path.join(CARPETA_TEMPORAL, f"{nombre_cliente}_Factura.pdf")
                    with open(path_factura, "wb") as f:
                        f.write(archivo_factura.getbuffer())
                    rutas_archivos.append(path_factura)

                    path_mono = os.path.join(CARPETA_TEMPORAL, f"{nombre_cliente}_Monotributo.pdf")
                    with open(path_mono, "wb") as f:
                        f.write(archivo_monotributo.getbuffer())
                    rutas_archivos.append(path_mono)

                    tiene_atm = False
                    if archivo_atm:
                        path_atm = os.path.join(CARPETA_TEMPORAL, f"{nombre_cliente}_ATM.pdf")
                        with open(path_atm, "wb") as f:
                            f.write(archivo_atm.getbuffer())
                        rutas_archivos.append(path_atm)
                        tiene_atm = True

                    # Unificar PDFs en orden estricto
                    merger = PdfMerger()
                    for r in rutas_archivos:
                        merger.append(r)

                    pdf_salida = os.path.join(CARPETA_TEMPORAL, f"{nombre_cliente}_Consolidado.pdf")
                    merger.write(pdf_salida)
                    merger.close()

                    # Envío por correo Gmail del estudio al Hospital
                    msg = EmailMessage()
                    msg['Subject'] = f"Facturación y Constancias - {nombre_cliente}"
                    msg['From'] = CORREO_ESTUDIO
                    msg['To'] = CORREO_DESTINO
                    msg.set_content(f"Estimados,\n\nAdjunto la documentación consolidada correspondiente al proveedor {nombre_cliente}.\n\nAtentamente,\nEstudio Contable.")

                    with open(pdf_salida, 'rb') as f:
                        file_data = f.read()
                    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=f"{nombre_cliente}_Consolidado.pdf")

                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                        smtp.login(CORREO_ESTUDIO, PASSWORD_ESTUDIO)
                        smtp.send_message(msg)

                    st.success(f"✅ ¡Documentación de {nombre_cliente} unificada y enviada con éxito a {CORREO_DESTINO}!")
                    if tiene_atm:
                        st.info("📁 Se incluyó correctamente la constancia de ATM en el PDF unificado.")
                    else:
                        st.warning("⚠️ Nota: No se adjuntó constancia de ATM (el proceso continuó con los documentos obligatorios).")

                    # Generador de mensaje de WhatsApp sugerido
                    st.markdown("### 📱 Mensaje sugerido de WhatsApp para el cliente:")
                    st.code(f"Hola {nombre_cliente}, desde el estudio contable te escribimos porque necesitamos actualizar tu comprobante de monotributo o verificar tu clave de ARCA/ATM para avanzar con la presentación en el hospital. ¿Podrás enviárnoslo? ¡Muchas gracias!")

                except Exception as e:
                    st.error(f"Ocurrió un error en el proceso técnico: {e}")

# --- EJECUCIÓN ---
if verificar_login():
    main_app()