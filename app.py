import streamlit as st
import os
import re
import zipfile
import urllib.parse
from PyPDF2 import PdfMerger, PdfReader

st.set_page_config(page_title="Sistema Contable - Hospital Lagomaggiore", page_icon="📁", layout="wide")

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

def analizar_y_clasificar_archivo(ruta_pdf):
    """
    Clasifica el documento (Factura, Monotributo, ATM) e identifica 
    al cliente por nombre o CUIT propio, ignorando los datos de los hospitales.
    """
    tipo_doc = "OTRO"
    nombre_cliente = "GENERAL"
    cuit_encontrado = "SIN_CUIT"
    
    # CUITs institucionales y de compradores a ignorar por completo
    cuits_a_ignorar = ["30999282292", "33999281759", "20273592601", "23335427904"]

    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_completo += (pagina.extract_text() or "") + "\n"
        
        texto_upper = texto_completo.upper()

        # 1. Identificar el Tipo de Documento
        if "FACTURA" in texto_upper or "CAE N°" in texto_upper or "PUNTO DE VENTA" in texto_upper:
            tipo_doc = "FACTURA"
        elif "MONOTRIBUTO" in texto_upper or "VEP" in texto_upper or "OBLIGACION MENSUAL" in texto_upper or "MERCADO PAGO" in texto_upper or "PAGASTE A" in texto_upper:
            tipo_doc = "MONOTRIBUTO"
        elif "ATM" in texto_upper or "ADMINISTRACION TRIBUTARIA MENDOZA" in texto_upper or "CUMPLIMIENTO FISCAL" in texto_upper:
            tipo_doc = "ATM"

        # 2. Identificar por Apellido/Nombre clave conocido del estudio
        clientes_conocidos = ["MANSILLA", "COLQUE", "CONIL", "ARROYO"]
        for cli in clientes_conocidos:
            if cli in texto_upper:
                nombre_cliente = cli
                break

        # 3. Extracción de CUIT descartando hospitales
        matches_cuits = re.findall(r'\b(?:20|23|27|30|33|34)-?\d{8}-?\d{1}\b', texto_completo)
        for m in matches_cuits:
            cuit_limpio = m.replace("-", "")
            if cuit_limpio not in cuits_a_ignorar and not cuit_limpio.startswith("30999"):
                cuit_encontrado = cuit_limpio
                break

    except Exception:
        pass
        
    return tipo_doc, nombre_cliente, cuit_encontrado

if verificar_login():
    st.sidebar.success(f"Conectado: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📁 Sistema de Unificación y Orden Inteligente por Cliente")
    st.write("Clasificación estricta: 1º Factura, 2º Monotributo, 3º ATM con descargas directas individuales.")

    archivos_subidos = st.file_uploader(
        "Subir lote masivo de PDFs (Facturas, Monotributo, ATM de todos los clientes)", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        st.info(f"Total de archivos cargados: {len(archivos_subidos)}")

        if st.button("Procesar, Ordenar y Agrupar por Cliente"):
            clientes_dict = {}
            rutas_temporales = []

            with st.spinner("Analizando documentos y unificando por contribuyente..."):
                for archivo in archivos_subidos:
                    ruta_temp = os.path.join(CARPETA_TEMPORAL, archivo.name)
                    try:
                        with open(ruta_temp, "wb") as f:
                            f.write(archivo.getbuffer())
                        rutas_temporales.append(ruta_temp)

                        tipo_doc, nombre_cli, cuit_cli = analizar_y_clasificar_archivo(ruta_temp)
                        
                        # Usamos el nombre detectado como clave principal para agrupar perfecto
                        clave_agrupacion = f"{nombre_cli} ({cuit_cli})"
                        
                        if clave_agrupacion not in clientes_dict:
                            clientes_dict[clave_agrupacion] = {"FACTURA": [], "MONOTRIBUTO": [], "ATM": [], "OTRO": []}
                        
                        clientes_dict[clave_agrupacion][tipo_doc].append(ruta_temp)
                    except Exception:
                        pass

            st.success(f"¡Proceso exitoso! Se armaron los expedientes para {len(clientes_dict)} clientes.")

            # Generación del ZIP con orden estricto: Factura -> Monotributo -> ATM
            zip_path = os.path.join(CARPETA_TEMPORAL, "Expedientes_Ordenados_Hospital.zip")
            archivos_generados = {}
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for cliente_key, docs in clientes_dict.items():
                    merger = PdfMerger()
                    
                    # ORDEN OBLIGATORIO: Factura primero, Monotributo segundo, ATM tercero
                    orden_tipos = ["FACTURA", "MONOTRIBUTO", "ATM", "OTRO"]
                    for tipo in orden_tipos:
                        for f_path in docs[tipo]:
                            try:
                                merger.append(f_path)
                            except Exception:
                                pass
                    
                    nombre_archivo_limpio = cliente_key.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
                    nombre_salida = f"Expediente_{nombre_archivo_limpio}.pdf"
                    ruta_salida_cliente = os.path.join(CARPETA_TEMPORAL, nombre_salida)
                    
                    try:
                        merger.write(ruta_salida_cliente)
                        merger.close()
                        zipf.write(ruta_salida_cliente, nombre_salida)
                        archivos_generados[cliente_key] = ruta_salida_cliente
                    except Exception:
                        pass

            st.markdown("### 📥 Descarga Masiva de Expedientes")
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📦 Descargar ZIP con todos los expedientes ordenados",
                    data=f,
                    file_name="Expedientes_Ordenados_Hospital.zip",
                    mime="application/zip"
                )

            st.markdown("---")
            st.markdown("### 🗂️ Panel de Control y Descarga Individual por Cliente")
            st.write("Descargá el PDF de cada cliente de forma individual con un clic para adjuntarlo fácilmente en tu correo o gestionar su WhatsApp.")

            for cliente_key, docs in clientes_dict.items():
                total_docs = len(docs["FACTURA"]) + len(docs["MONOTRIBUTO"]) + len(docs["ATM"]) + len(docs["OTRO"])
                
                with st.expander(f"👤 Contribuyente: {cliente_key} — Documentos: {total_docs} (Facturas: {len(docs['FACTURA'])}, Monotributo: {len(docs['MONOTRIBUTO'])}, ATM: {len(docs['ATM'])})"):
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 📥 Descarga de PDF Unificado")
                        if cliente_key in archivos_generados:
                            ruta_pdf_indiv = archivos_generados[cliente_key]
                            with open(ruta_pdf_indiv, "rb") as pdf_file:
                                st.download_button(
                                    label=f"📄 Descargar PDF de {cliente_key}",
                                    data=pdf_file,
                                    file_name=f"Expediente_{cliente_key.replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{cliente_key}"
                                )
                        st.caption("*(Guardá este archivo y adjuntalo en tu correo de Gmail institucional)*")

                    with col2:
                        st.markdown("#### 💬 Alertas de WhatsApp")
                        telefono = st.text_input(f"Celular para {cliente_key}", placeholder="Ej: 2615555555", key=f"tel_{cliente_key}")
                        if telefono:
                            tipo_reclamo = st.selectbox(
                                "Motivo del mensaje:",
                                [
                                    "Falta comprobante de pago de Monotributo",
                                    "Contraseña de ARCA / ATM incorrecta o vencida",
                                    "Figura deuda pendiente en ATM",
                                    "Documentación incompleta"
                                ],
                                key=f"mot_{cliente_key}"
                            )
                            if "Monotributo" in tipo_reclamo:
                                msg_wa = f"Hola! Del estudio contable. Para {cliente_key} aún no figura el pago del monotributo. Podrás enviarnos el comprobante?"
                            elif "ARCA" in tipo_reclamo:
                                msg_wa = f"Hola! Del estudio contable. La contraseña de ARCA / ATM de {cliente_key} figura incorrecta o vencida. Nos pasas la clave?"
                            elif "deuda" in tipo_reclamo:
                                msg_wa = f"Hola! Del estudio contable. Detectamos saldo deudor en ATM para {cliente_key}. Necesitamos regularizarlo."
                            else:
                                msg_wa = f"Hola! Del estudio contable. Falta documentación para armar el expediente de {cliente_key}."

                            link_wa = f"https://wa.me/549{telefono}?text={urllib.parse.quote(msg_wa)}"
                            st.markdown(f"[💬 Enviar WhatsApp]({link_wa})", unsafe_allow_html=True)

            for ruta in rutas_temporales:
                if os.path.exists(ruta):
                    os.remove(ruta)
