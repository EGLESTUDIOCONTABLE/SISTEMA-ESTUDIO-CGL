import streamlit as st
import os
import re
import zipfile
import urllib.parse
from PyPDF2 import PdfMerger, PdfReader

st.set_page_config(page_title="Sistema Contable - Hospital Lagomaggiore", page_icon="📁", layout="wide")

# --- CREDENCIALES DEL SISTEMA ---
USUARIOS = {
    "empleado1": "clave123",
    "empleado2": "clave456",
    "cristiano": "admin2026"
}

CARPETA_TEMPORAL = "./temp_docs"
if not os.path.exists(CARPETA_TEMPORAL):
    os.makedirs(CARPETA_TEMPORAL)

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

def extraer_cuit(ruta_pdf):
    """Busca un CUIT válido dentro del texto del PDF"""
    try:
        reader = PdfReader(ruta_pdf)
        texto = ""
        for pagina in reader.pages:
            texto += pagina.extract_text() or ""
        
        match = re.search(r'\b(20|23|27|30|33|34)-?\d{8}-?\d{1}\b', texto)
        if match:
            return match.group(0).replace("-", "")
    except Exception:
        pass
    return "SIN_CUIT_IDENTIFICADO"

if verificar_login():
    st.sidebar.success(f"Conectado: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📁 Sistema de Procesamiento y Gestión por CUIT")
    st.write("Agrupación automática de documentación, generación de ZIP y enlaces directos a Gmail y WhatsApp.")

    # Correo fijo del hospital para los enlaces de Gmail
    correo_hospital = "facturaslagomaggiore@gmail.com"

    archivos_subidos = st.file_uploader(
        "Subir lote masivo de PDFs (Facturas, Monotributo, ATM de todos los clientes)", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        st.info(f"Total de archivos cargados: {len(archivos_subidos)}")

        if st.button("Procesar y Generar Expedientes por Cliente"):
            clientes_dict = {}
            rutas_temporales = []

            with st.spinner("Analizando documentos y detectando CUITs..."):
                for archivo in archivos_subidos:
                    ruta_temp = os.path.join(CARPETA_TEMPORAL, archivo.name)
                    try:
                        with open(ruta_temp, "wb") as f:
                            f.write(archivo.getbuffer())
                        rutas_temporales.append(ruta_temp)

                        cuit = extraer_cuit(ruta_temp)
                        if cuit not in clientes_dict:
                            clientes_dict[cuit] = []
                        clientes_dict[cuit].append(ruta_temp)
                    except Exception:
                        pass

            st.success(f"¡Proceso exitoso! Se armaron expedientes para {len(clientes_dict)} clientes.")

            zip_path = os.path.join(CARPETA_TEMPORAL, "Clientes_Unificados_Hospital.zip")
            archivos_generados = {}
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for cuit, lista_archivos in clientes_dict.items():
                    merger = PdfMerger()
                    for f_path in lista_archivos:
                        try:
                            merger.append(f_path)
                        except Exception:
                            pass
                    
                    nombre_salida = f"Cliente_CUIT_{cuit}_Unificado.pdf"
                    ruta_salida_cliente = os.path.join(CARPETA_TEMPORAL, nombre_salida)
                    
                    try:
                        merger.write(ruta_salida_cliente)
                        merger.close()
                        zipf.write(ruta_salida_cliente, nombre_salida)
                        archivos_generados[cuit] = ruta_salida_cliente
                    except Exception:
                        pass

            st.markdown("### 📥 Descarga Masiva de Expedientes")
            st.write("Descargá el archivo comprimido con todos los PDFs unificados por CUIT listos para adjuntar en tu correo:")
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📦 Descargar ZIP con todos los PDFs separados",
                    data=f,
                    file_name="Documentacion_Clientes_Unificada.zip",
                    mime="application/zip"
                )

            st.markdown("---")
            st.markdown("### 📨 Gestión Individual por Cliente (Gmail y WhatsApp)")
            st.write("Desde aquí podés abrir directamente el correo prearmado para Gmail o enviar las alertas de WhatsApp.")

            for cuit, lista_archivos in clientes_dict.items():
                with st.expander(f"Cliente CUIT: {cuit} ({len(lista_archivos)} archivos relacionados)"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### ✉️ Envío de Correo (Gmail)")
                        asunto_mail = f"Documentación Mensual - CUIT: {cuit}"
                        cuerpo_mail = f"Estimados,\n\nAdjuntamos la documentación unificada correspondiente al CUIT {cuit}.\n\nAtentamente,\nEstudio Contable CGL."
                        
                        # Generador de enlace oficial de Gmail web (abre sesión de egl.estudiocontable@gmail.com)
                        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={correo_hospital}&su={urllib.parse.quote(asunto_mail)}&body={urllib.parse.quote(cuerpo_mail)}"
                        st.markdown(f"[✉️ Redactar correo en Gmail para CUIT {cuit}]({gmail_url})", unsafe_allow_html=True)
                        st.caption("*(Recordá adjuntar el PDF descargado del CUIT correspondiente)*")

                    with col2:
                        st.markdown("#### 💬 Alertas de WhatsApp")
                        telefono = st.text_input(f"Celular de contacto ({cuit})", placeholder="Ej: 2615555555", key=f"tel_{cuit}")
                        
                        if telefono:
                            tipo_reclamo = st.selectbox(
                                f"Motivo de contacto:",
                                [
                                    "Falta comprobante de pago de Monotributo",
                                    "Contraseña de ARCA / ATM incorrecta o vencida",
                                    "Figura deuda pendiente en ATM",
                                    "Documentación incompleta / Faltante general"
                                ],
                                key=f"motivo_{cuit}"
                            )

                            if "Monotributo" in tipo_reclamo:
                                mensaje_wa = f"Hola! Te escribo del estudio contable. Al revisar tu CUIT {cuit}, notamos que aún no figura registrado el pago del monotributo de este periodo. Podrás enviarnos el comprobante de pago por este medio?"
                            elif "ARCA" in tipo_reclamo:
                                mensaje_wa = f"Hola! Te escribo del estudio contable. Tuvimos un inconveniente al ingresar a tus cuentas de ARCA / ATM ya que la contraseña figura como incorrecta o vencida. Podrás pasarnos la clave actualizada?"
                            elif "deuda" in tipo_reclamo:
                                mensaje_wa = f"Hola! Te escribo del estudio contable. Al consultar tus tributos para el CUIT {cuit}, detectamos que figura saldo deudor en ATM. Necesitamos regularizarlo a la brevedad."
                            else:
                                mensaje_wa = f"Hola! Te escribo del estudio contable. Estamos armando tu documentación del CUIT {cuit} y nos está faltando parte de la información requerida. Podrás enviárnosla?"

                            link_wa = f"https://wa.me/549{telefono}?text={urllib.parse.quote(mensaje_wa)}"
                            st.markdown(f"[💬 Abrir WhatsApp con reclamo]({link_wa})", unsafe_allow_html=True)
                        else:
                            st.caption("Ingresá el celular para habilitar el botón de WhatsApp.")

            for ruta in rutas_temporales:
                if os.path.exists(ruta):
                    os.remove(ruta)
