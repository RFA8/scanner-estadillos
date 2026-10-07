import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI

# 1. Configuración de la pantalla
st.set_page_config(
    page_title="Scanner Estadillos", 
    page_icon="📱", 
    layout="centered"
)

st.title("📱 Lector de Notas -> Excel")

# 2. Conexión a OpenAI desde los Secrets de Streamlit
api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    st.error("⚠️ No se ha detectado la API Key de OpenAI. Configúrala en los Secrets de Streamlit.")
    st.stop()

client = OpenAI(api_key=api_key)

# 3. Captura o subida de foto
st.write("Haz una foto a la hoja de campo o selecciona una foto de la galería:")
foto_camara = st.camera_input("📷 Hacer foto")
foto_galeria = st.file_uploader("🖼️ O subir foto guardada", type=["jpg", "jpeg", "png"])

foto_final = foto_camara if foto_camara is not None else foto_galeria

if foto_final is not None:
    st.image(foto_final, caption="Foto cargada", use_container_width=True)
    
    if st.button("⚡ CONVERTIR A EXCEL", type="primary"):
        with st.spinner("La IA está leyendo los datos de tu nota..."):
            try:
                # Convertir imagen a base64
                bytes_data = foto_final.getvalue()
                base64_image = base64.b64encode(bytes_data).decode('utf-8')

                prompt = """
                Analiza esta foto de una hoja de notas/estadillo de campo agrícola.
                Extrae toda la información manuscrita o impresa estructurándola en filas y columnas.
                
                Devuelve ÚNICAMENTE un objeto JSON válido con este formato estricto:
                {
                    "datos": [
                        {"Lote": "MUESTRA-1", "Tratamiento": "Control", "Fecha": "2026-05-10", "Valor": 120.5, "Observaciones": "OK"},
                        ...
                    ]
                }
                Si no hay cabeceras claras, usa nombres lógicos en español.
                No incluyas explicaciones ni formato markdown. Solo código JSON puro.
                """

                # Petición a GPT-4o
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }],
                    max_tokens=2000,
                )

                # Limpieza de JSON
                json_str = response.choices[0].message.content.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]

                # Convertir a DataFrame
                datos_json = json.loads(json_str.strip())
                df = pd.DataFrame(datos_json["datos"])

                st.success("¡Lectura completada!")
                st.subheader("📋 Datos detectados:")
                
                # Editor interactivode celdas
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)

                # Generar archivo Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_editado.to_excel(writer, index=False, sheet_name='Datos_Campo')
                excel_bytes = output.getvalue()

                # Botón de descarga
                st.download_button(
                    label="📥 DESCARGAR ARCHIVO EXCEL (.XLSX)",
                    data=excel_bytes,
                    file_name="estadillo_campo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            except Exception as e:
                st.error(f"Error procesando la imagen: {e}")
