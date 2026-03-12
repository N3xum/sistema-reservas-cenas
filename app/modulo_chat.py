from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from .models import Usuario, Menu, Reserva 
from .ia_service import consultar_gemini

# Creamos el blueprint independiente para la Inteligencia Artificial
chat_bp = Blueprint('chat_bp', __name__)

@chat_bp.route('/chat_ia', methods=['POST'])
@login_required
def chat_ia():
    datos = request.get_json()
    mensaje_original = datos.get('mensaje', '')
    mensaje_minusculas = mensaje_original.lower() 
    
    contexto_datos = ""
    # --- INICIO DE MEMORIA A CORTO PLAZO ---
    if 'historial_chat' not in session:
        session['historial_chat'] = []  # Crea una lista vacía si es su primer mensaje
    
    # --- DICCIONARIOS DE PALABRAS (Declarados arriba) ---
    palabras_estado = ["mis reservas", "mi reserva", "tengo reservas", "tengo alguna", "mi estado", "historial", "confirmada", "pendiente", "aprobada", "rechazada", "agendé", "agende", "reservé", "reserve"]
    palabras_fecha = ["espacio", "disponibilidad", "disponible", "lugar", "lleno", "ocupado", "mesas", "mesa", "para el", "mañana", "hoy", "campo", "sitio", "fecha", "calendario", "parral", "libre", "cupo", "finde", "viernes", "sábado", "sabado", "domingo"]
    palabras_menu = ["menú", "menu", "plato", "platillo", "recomienda", "precio", "carta", "ofrecen", "costo", "vale", "opciones", "barato", "caro"]

    # 1. LÓGICA DE JHILDA (Rastreador de Reservas - PRIORIDAD ALTA)
    if any(palabra in mensaje_minusculas for palabra in palabras_estado):
        mis_reservas = Reserva.query.filter_by(usuario_id=current_user.id).all()
        
        if not mis_reservas:
            detalle_reservas = "El usuario no tiene ninguna reserva en el sistema."
        else:
            detalle_reservas = ""
            for r in mis_reservas:
                detalle_reservas += f"- Fecha: {r.fecha_reserva}, Estado: {r.estado}\n"
                
        contexto_datos = f"""
        El usuario está preguntando por el estado de sus reservas en Detalle Añejo.
        Aquí está el historial real extraído de la base de datos:
        {detalle_reservas}
        
        Instrucción Estricta: 
        1. Si no tiene reservas, invítalo amablemente a agendar una cena romántica.
        2. Si tiene reservas, léele las fechas y el estado. 
        3. Si están 'Confirmadas', dile que la mesa bajo el parral lo espera. Si están 'Pendientes', dile que el administrador las aprobará pronto.
        """
        
    # 2. TU LOGICA PETER (Disponibilidad y fechas)
    elif any(palabra in mensaje_minusculas for palabra in palabras_fecha):
        from datetime import date
        fecha_hoy = date.today()
        
        reservas_activas = Reserva.query.filter(Reserva.estado == 'Confirmada', Reserva.fecha_reserva >= fecha_hoy).all()
        
        resumen_fechas = {}
        for res in reservas_activas:
            fecha_str = str(res.fecha_reserva)
            resumen_fechas[fecha_str] = resumen_fechas.get(fecha_str, 0) + 1
            
        contexto_datos = f"""
        El usuario quiere saber la disponibilidad de mesas de Detalle Añejo.
        Nuestra capacidad máxima por noche es de 10 mesas en el parral.
        
        ⏳ FECHA ACTUAL DEL SISTEMA: {fecha_hoy} (Año: {fecha_hoy.year})
        
        Aquí tienes el reporte de las mesas YA CONFIRMADAS por fecha (en formato AAAA-MM-DD):
        {resumen_fechas}
        
        Instrucción Estricta: 
        1. Identifica qué fecha pide el usuario. Si dice por ejemplo "21 de marzo", deduce automáticamente que se refiere a la fecha {fecha_hoy.year}-03-21. Si dice "mañana", súmale un día a la fecha actual.
        2. Revisa el reporte para esa fecha exacta. Si la fecha no aparece en el reporte, significa que hay 0 reservas (las 10 mesas están libres).
        3. Respóndele de forma elegante. Si tiene 7 o más mesas ocupadas, dile que hay alta demanda. Si tiene menos, anímalo a reservar su cena rústica indicando que hay buena disponibilidad.
        """
        
    # 3. VALLEJOS ROBERTO (Menus - PRIORIDAD BAJA)
    elif any(palabra in mensaje_minusculas for palabra in palabras_menu):
        menus_disponibles = Menu.query.filter_by(disponibilidad=True).all()
        
        if not menus_disponibles:
            lista_menus = "Actualmente no hay menús registrados o disponibles."
        else:
            lista_menus = ""
            for m in menus_disponibles:
                lista_menus += f"- {m.nombre_experiencia}: {m.descripcion} (Precio: {m.precio} Bs)\n"
                
        contexto_datos = f"""
        El usuario está preguntando por nuestra oferta gastronómica en Detalle Añejo.
        Aquí tienes la lista real de menús extraída de la base de datos:
        {lista_menus}
        
        Instrucción Estricta: 
        1. Actúa como el Maître experto del restaurante.
        2. Analiza lo que pide el usuario (ej: si busca algo económico, para un aniversario, etc.).
        3. Recomiéndale de forma elegante y persuasiva UNA o DOS opciones de la lista que mejor encajen.
        4. Menciona siempre el precio y la descripción para antojar al cliente.
        """    
        
    # 4. RESPUESTA POR DEFECTO
    else:
        contexto_datos = """
        El usuario saluda o hace una pregunta general. 
        Instruccion: Dale la bienvenida a Detalle Anejo y dile brevemente que puedes ayudarle a:
        1. Recomendarle un menú para su velada.
        2. Revisar el estado de sus reservas.
        3. Consultar la disponibilidad de mesas para una fecha específica
        """
        
   # 1. Convertimos la lista de memoria en un texto legible para la IA
    historial_texto = "\n".join(session['historial_chat'])
    
    # 2. Se lo inyectamos al contexto final
    if historial_texto:
        contexto_datos += f"\n\n--- HISTORIAL DE ESTA CONVERSACIÓN ---\n{historial_texto}\n--------------------------------------"
        
    # 3. Llamamos a Gemini
    respuesta_ia = consultar_gemini(mensaje_original, contexto_datos)
    
    # 4. Guardamos este nuevo intercambio en la memoria
    session['historial_chat'].append(f"Cliente: {mensaje_original}")
    session['historial_chat'].append(f"Maître: {respuesta_ia}")
    
    # 5. Limpieza automática: Solo recordamos los últimos 3 intercambios (6 líneas) para no saturar a la IA
    if len(session['historial_chat']) > 6:
        session['historial_chat'] = session['historial_chat'][-6:]
        
    session.modified = True # Obligamos a Flask a guardar el cambio en la sesión
    
    return jsonify({'respuesta': respuesta_ia})