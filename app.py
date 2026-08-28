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

def clasificar_y_extraer_datos(ruta_pdf):
    tipo_doc = "OTRO"
    cuit_encontrado = "SIN_CUIT"
    
    try:
        reader = PdfReader(ruta_pdf)
        texto = ""
        for pagina in reader.pages:
            texto += (pagina.extract_text() or "").upper()

        if "FACTURA" in texto or "CAE N°" in texto or "PUNTO DE VENTA" in texto:
            tipo_doc = "FACTURA"
        elif "MONOTRIBUTO" in texto or "VEP" in texto or "OBLIGACION MENSUAL" in texto:
            tipo_doc = "MONOTRIBUTO"
        elif "ATM" in texto or "ADMINISTRACION TRIBUTARIA MENDOZA" in texto or "CUMPLIMIENTO FISCAL" in texto:
            tipo_doc = "ATM"

        match_cuit_completo = re.search(r'\b(?:20|23|27|30|33|34)-?\d{8}-?\d{1}\b', texto)
        if match_cuit_completo:
            cuit_encontrado = match_cuit_completo.group(0).replace("-", "")

    except Exception:
        pass
        
    return tipo_doc, cuit_encontrado

if verificar_login():
    st.sidebar.success(f"Conectado: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📁 Sistema de Unificación Ordenada por CUIT")
    st.write("Clasificación estricta: 1º Factura, 2º Monotributo, 3º ATM agrupados por contribuyente.")

    correo_hospital = "facturaslagomaggiore@gmail.com"

    archivos_subidos = st.file_uploader(
        "Subir lote masivo de PDFs (Facturas, Monotributo, ATM)", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        st.info(f"Total de archivos cargados: {len(archivos_subidos)}")

        if st.button("Procesar, Ordenar y Agrupar por Cliente"):
            clientes_dict = {}
            rutas_temporales = []

            with st.spinner("Analizando y clasificando documentos por contribuyente..."):
                for archivo in archivos_subidos:
                    ruta_temp = os.path.join(CARPETA_TEMPORAL, archivo.name)
                    try:
                        with open(ruta_temp, "wb") as f:
                            f.write(archivo.getbuffer())
                        rutas_temporales.append(ruta_temp)

                        tipo_doc, cuit = clasificar_y_extraer_datos(ruta_temp)
                        
                        if cuit not in clientes_dict:
                            clientes_dict[cuit] = {"FACTURA": [], "MONOTRIBUTO": [], "ATM": [], "OTRO": []}
                        
                        clientes_dict[cuit][tipo_doc].append(ruta_temp)
                    except Exception:
                        pass

            st.success(f"¡Proceso exitoso! Se identificaron {len(clientes_dict)} contribuyentes.")

            zip_path = os.path.join(CARPETA_TEMPORAL, "Expedientes_Ordenados_Hospital.zip")
            archivos_generados = {}
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for cuit, docs in clientes_dict.items():
                    merger = PdfMerger()
                    
                    orden_tipos = ["FACTURA", "MONOTRIBUTO", "ATM", "OTRO"]
                    for tipo in orden_tipos:
                        for f_path in docs[tipo]:
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

            st.markdown("### 📥 Descarga de Expedientes Ordenados")
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📦 Descargar ZIP con PDFs ordenados (Factura -> Monotributo -> ATM)",
                    data=f,
                    file_name="Expedientes_Ordenados_Hospital.zip",
                    mime="application/zip"
                )

            st.markdown("---")
            st.markdown("### 📨 Panel de Control y Enlaces")

            for cuit, docs in clientes_dict.items():
                total_archivos = len(docs["FACTURA"]) + len(docs["MONOTRIBUTO"]) + len(docs["ATM"]) + len(docs["OTRO"])
                with st.expander(f"CUIT: {cuit} — Documentos detectados: {total_archivos} (Facturas: {len(docs['FACTURA'])}, Monotributo: {len(docs['MONOTRIBUTO'])}, ATM: {len(docs['ATM'])})"):
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("#### ✉️ Correo (Gmail)")
                        asunto_mail = f"Documentación Mensual - CUIT: {cuit}"
                        cuerpo_mail = f"Estimados,\n\nAdjuntamos la documentación unificada (Factura, Monotributo y ATM) correspondiente al CUIT {cuit}.\n\nAtentamente,\nEstudio Contable CGL."
                        
                        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={correo_hospital}&su={urllib.parse.quote(asunto_mail)}&body={urllib.parse.quote(cuerpo_mail)}"
                        st.markdown(f"[✉️ Abrir Gmail para CUIT {cuit}]({gmail_url})", unsafe_allow_html=True)
                        st.caption("*(Adjuntá el PDF del CUIT descargado desde el ZIP)*")

                    with col2:
                        st.markdown("#### 💬 Alertas de WhatsApp")
                        telefono = st.text_input(f"Celular ({cuit})", placeholder="Ej: 2615555555", key=f"tel_{cuit}")
                        if telefono:
                            tipo_reclamo = st.selectbox(
                                "Motivo:",
                                [
                                    "Falta comprobante de pago de Monotributo",
                                    "Contraseña de ARCA / ATM incorrecta o vencida",
                                    "Figura deuda pendiente en ATM",
                                    "Documentación incompleta"
                                ],
                                key=f"mot__{cuit}"
                            )
                            if "Monotributo" in tipo_reclamo:
                                msg_wa = f"Hola! Del estudio contable. Para el CUIT {cuit} aún no figura el pago del monotributo. Podrás enviarnos el comprobante?"
                            elif "ARCA" in tipo_reclamo:
                                msg_wa = f"Hola! Del estudio contable. La contraseña de ARCA / ATM del CUIT {cuit} figura incorrecta o vencida. Nos pasas la clave?"
                            elif "deuda" in tipo_reclamo:
                                msg_wa = f"Hola! Del estudio contable. Detectamos saldo deudor en ATM para el CUIT {cuit}. Necesitamos regularizarlo."
                            else:
                                msg_wa = f"Hola! Del estudio contable. Falta documentación para armar el expediente del CUIT {cuit}."

                            link_wa = f"https://wa.me/549{telefono}?text={urllib.parse.quote(msg_wa)}"
                            st.markdown(f"[💬 Enviar WhatsApp]({link_wa})", unsafe_allow_html=True)

            for ruta in rutas_temporales:
                if os.path.exists(ruta):
                    os.remove(ruta)
