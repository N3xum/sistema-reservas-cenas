from flask import Blueprint, request, jsonify
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
    
    # 1. VALLEJOS ROBERTO (Menus)
    if "menú" in mensaje_minusculas or "menu" in mensaje_minusculas or "plato" in mensaje_minusculas or "recomienda" in mensaje_minusculas or "precio" in mensaje_minusculas or "comida" in mensaje_minusculas:
        
        # Filtramos para que la IA solo vea los menús que sí están disponibles
        menus_disponibles = Menu.query.filter_by(disponibilidad=True).all()
        
        if not menus_disponibles:
            lista_menus = "Actualmente no hay menús registrados o disponibles."
        else:
            lista_menus = ""
            for m in menus_disponibles:
                # CORREGIDO: Usamos m.nombre_experiencia
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
        
    # 2. LÓGICA DE JHILDA (Rastreador de Reservas)
    elif "mis reservas" in mensaje_minusculas or "mi reserva" in mensaje_minusculas or "tengo reservas" in mensaje_minusculas or "tengo alguna reserva" in mensaje_minusculas or "mi estado" in mensaje_minusculas:
        
        # Jhilda: Consultamos solo las reservas del cliente que está escribiendo
        mis_reservas = Reserva.query.filter_by(usuario_id=current_user.id).all()
        
        if not mis_reservas:
            detalle_reservas = "El usuario no tiene ninguna reserva en el sistema."
        else:
            detalle_reservas = ""
            for r in mis_reservas:
                # Ajusta 'fecha_reserva' o 'estado' si tus columnas se llaman diferente
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
        
    # 3. TU LOGICA PETER (Termómetro de Disponibilidad)
    elif "espacio" in mensaje_minusculas or "disponibilidad" in mensaje_minusculas or "disponible" in mensaje_minusculas or "lugar" in mensaje_minusculas or "lleno" in mensaje_minusculas or "ocupado" in mensaje_minusculas or "mesas" in mensaje_minusculas or "mesa" in mensaje_minusculas or "para el" in mensaje_minusculas or "mañana" in mensaje_minusculas or "hoy" in mensaje_minusculas:
        
        from datetime import date
        fecha_hoy = date.today()
        
        # Consultamos TODAS las reservas confirmadas de hoy en adelante
        reservas_activas = Reserva.query.filter(Reserva.estado == 'Confirmada', Reserva.fecha_reserva >= fecha_hoy).all()
        
        # Armamos un diccionario contando cuántas mesas están ocupadas por día
        resumen_fechas = {}
        for res in reservas_activas:
            fecha_str = str(res.fecha_reserva) # Ej: '2026-03-21'
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
        
    # 4. RESPUESTA POR DEFECTO
    else:
        contexto_datos = """
        El usuario saluda o hace una pregunta general. 
        Instruccion: Dale la bienvenida a Detalle Anejo y dile brevemente que puedes ayudarle a:
        1. Recomendarle un menú para su velada.
        2. Revisar el estado de sus reservas.
        3. Consultar la disponibilidad de mesas para una fecha específica
        """
        
    respuesta_ia = consultar_gemini(mensaje_original, contexto_datos)
    return jsonify({'respuesta': respuesta_ia})