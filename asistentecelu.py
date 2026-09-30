import streamlit as st
from google import genai
import datetime
from gtts import gTTS
import io
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder
import json
import os
from PIL import Image
import urllib.parse
from duckduckgo_search import DDGS

st.set_page_config(page_title="J.A.R.V.I.S. Móvil", page_icon="🤖")

# --- INYECCIÓN DE INTERFAZ SCI-FI (CSS adaptado a móvil) ---
st.markdown("""
<style>
    .stApp { background-color: #050914; color: #00ffcc; font-family: 'Consolas', 'Courier New', monospace; }
    h1, h2, h3, p, span { color: #00ffcc !important; text-shadow: 0 0 5px rgba(0, 255, 204, 0.5); }
    .stChatMessage { background-color: rgba(0, 255, 204, 0.05); border-left: 2px solid #00ffcc; border-radius: 5px; padding: 10px; box-shadow: -2px 0 5px rgba(0, 255, 204, 0.2); }
    .stChatInputContainer textarea { background-color: #0a1128 !important; border: 1px solid #00ffcc !important; color: #00ffcc !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🤖 J.A.R.V.I.S.")

ARCHIVO_HISTORIA = "memoria_jarvis.json"

def cargar_memoria():
    if os.path.exists(ARCHIVO_HISTORIA):
        with open(ARCHIVO_HISTORIA, "r", encoding="utf-8") as f:
            datos = json.load(f)
            if isinstance(datos, list): return {"Chat Principal": datos}
            return datos
    return {f"Sesión {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}": []}

def guardar_memoria(todas_las_sesiones):
    with open(ARCHIVO_HISTORIA, "w", encoding="utf-8") as f:
        json.dump(todas_las_sesiones, f, ensure_ascii=False, indent=4)

if "todas_las_sesiones" not in st.session_state:
    st.session_state.todas_las_sesiones = cargar_memoria()
    st.session_state.sesion_actual = list(st.session_state.todas_las_sesiones.keys())[-1]

# --- HERRAMIENTAS MÓVILES ---
def obtener_hora() -> str:
    return f"La fecha y hora actual es: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def generar_imagen(descripcion_en_ingles: str) -> str:
    prompt_url = urllib.parse.quote(f"masterpiece, 8k resolution, cinematic lighting, {descripcion_en_ingles}")
    url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1024&height=1024&model=flux&enhance=true&nologo=true"
    return f"Imagen lista. Responde incluyendo exactamente este código: ![Imagen]({url})"

def buscar_en_internet(consulta: str) -> str:
    try:
        resultados = DDGS().text(consulta, max_results=3)
        if not resultados: return "No encontré resultados."
        return "Búsqueda:\n" + "\n".join([f"- {r['title']}: {r['body']}" for r in resultados])
    except Exception as e: return f"Error de búsqueda: {e}"

# --- CEREBRO ---
if "chat" not in st.session_state:
    # 1. PON TU API KEY AQUÍ
    cliente = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    st.session_state.cliente = cliente
    st.session_state.chat = cliente.chats.create(
        model="gemini-3.5-flash-lite",
        config={"system_instruction": "Eres mi asistente personal J.A.R.V.I.S. Respondes de forma breve, sarcástica y con clase.", "tools": [obtener_hora, generar_imagen, buscar_en_internet]}
    )
    st.session_state.ultimo_audio = None
    st.session_state.ultima_imagen = None

with st.sidebar:
    st.header("🗂️ Memoria")
    if st.button("➕ Nueva Sesión", use_container_width=True):
        nuevo_nombre = f"Sesión {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        st.session_state.todas_las_sesiones[nuevo_nombre] = []
        st.session_state.sesion_actual = nuevo_nombre
        st.session_state.chat = st.session_state.cliente.chats.create(
            model="gemini-3.5-flash-lite",
            config={"system_instruction": "Eres mi asistente personal J.A.R.V.I.S. Respondes breve y con sarcasmo.", "tools": [obtener_hora, generar_imagen, buscar_en_internet]}
        )
        guardar_memoria(st.session_state.todas_las_sesiones)
        st.rerun()
    st.divider()
    for nombre_sesion in reversed(list(st.session_state.todas_las_sesiones.keys())):
        if st.button(nombre_sesion, type="primary" if nombre_sesion == st.session_state.sesion_actual else "secondary", use_container_width=True):
            st.session_state.sesion_actual = nombre_sesion
            st.session_state.chat = st.session_state.cliente.chats.create(
                model="gemini-3.5-flash-lite",
                config={"system_instruction": "Eres mi asistente personal J.A.R.V.I.S. Respondes breve y con sarcasmo.", "tools": [obtener_hora, generar_imagen, buscar_en_internet]}
            )
            st.rerun()

historial_actual = st.session_state.todas_las_sesiones[st.session_state.sesion_actual]
for mensaje in historial_actual:
    with st.chat_message(mensaje["rol"]): st.markdown(mensaje["texto"])

# --- CONTROLES MÓVILES ---
texto_escrito = st.chat_input("Comando...")
col1, col2 = st.columns(2)
with col1:
    audio_bytes = audio_recorder(text="Voz", recording_color="#00ffcc", icon_size="2x")
with col2:
    imagen_subida = st.file_uploader("Foto", type=["jpg", "png", "jpeg"], label_visibility="collapsed")

texto_final = texto_escrito
if audio_bytes and audio_bytes != st.session_state.ultimo_audio:
    st.session_state.ultimo_audio = audio_bytes
    with st.spinner("Procesando..."):
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            try: texto_final = r.recognize_google(r.record(source), language='es-EC')
            except: st.warning("No escuché bien.")

if texto_final:
    contenido = [texto_final]
    imagen_a_mostrar = None
    if imagen_subida and imagen_subida.file_id != st.session_state.ultima_imagen:
        st.session_state.ultima_imagen = imagen_subida.file_id
        imagen_a_mostrar = Image.open(imagen_subida)
        contenido.append(imagen_a_mostrar)

    with st.chat_message("user"):
        st.markdown(texto_final)
        if imagen_a_mostrar: st.image(imagen_a_mostrar, width=200)
    
    historial_actual.append({"rol": "user", "texto": texto_final})
    guardar_memoria(st.session_state.todas_las_sesiones)

    with st.spinner("Red neuronal activa..."):
        try:
            respuesta = st.session_state.chat.send_message(contenido).text
        except Exception as e: respuesta = f"Error de red: {e}"
    
    with st.chat_message("assistant"):
        st.markdown(respuesta)
        try:
            texto_voz = respuesta.split("![")[0].replace('"', '').replace('*', '')
            tts = gTTS(text=texto_voz, lang='es', tld='com.mx')
            audio_mem = io.BytesIO()
            tts.write_to_fp(audio_mem)
            st.audio(audio_mem, format='audio/mp3', autoplay=True)
        except: pass
            
    historial_actual.append({"rol": "assistant", "texto": respuesta})
    guardar_memoria(st.session_state.todas_las_sesiones)
    st.rerun()