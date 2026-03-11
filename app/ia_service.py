import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Cargar las variables ocultas (tu clave secreta del .env)
load_dotenv()

# 2. Configurar la API de Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ Error: No se encontró GEMINI_API_KEY en el archivo .env")

genai.configure(api_key=api_key)

# 3. Elegir el modelo (Usamos la versión 1.5 Flash porque es súper rápida y gratuita)
model = genai.GenerativeModel('gemini-2.5-flash')

def consultar_gemini(mensaje_usuario, contexto_datos=""):
    """
    Esta es la función maestra. 
    Recibe la pregunta del usuario y los datos de tu base de datos (contexto_datos).
    """
    
    # 4. El "Prompt del Sistema": Aquí le damos la personalidad al bot
    prompt_sistema = f"""
    Eres el asistente virtual inteligente de 'Detalle Añejo', un restaurante exclusivo de cenas rústicas.
    Tu tono debe ser elegante, amable, profesional y conciso.
    
    A continuación, te proporciono datos reales extraídos de nuestra base de datos para que puedas responder:
    ---
    DATOS DEL SISTEMA:
    {contexto_datos}
    ---
    
    Pregunta o solicitud del usuario: {mensaje_usuario}
    
    REGLA ESTRICTA: Responde basándote ÚNICAMENTE en los DATOS DEL SISTEMA proporcionados arriba. 
    Analiza esos datos y da una respuesta útil o un resumen. Si los datos están vacíos o no responden a la pregunta, 
    discúlpate cortésmente diciendo que no tienes esa información en este momento.
    No inventes menús, ni clientes, ni reservas que no estén en los DATOS DEL SISTEMA.
    """
    
    try:
        # 5. Enviar todo a Google y devolver la respuesta
        respuesta = model.generate_content(prompt_sistema)
        return respuesta.text
    except Exception as e:
        return f"Lo siento, hubo un problema de conexión con el sistema central: {str(e)}"