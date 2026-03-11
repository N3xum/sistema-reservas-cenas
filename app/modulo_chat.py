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
    
    # 1. LOGICA DE ROBERTO (Recomendador de Menus)
    if "menu" in mensaje_minusculas or "plato" in mensaje_minusculas or "recomienda" in mensaje_minusculas or "precio" in mensaje_minusculas:
        contexto_datos = "El usuario pregunta por menus o precios. (Aviso interno: Roberto conectara la tabla Menu aqui)."
        
    # 2. LÓGICA DE JHILDA (Rastreador de Reservas)
    elif "reserva" in mensaje_minusculas or "confirmada" in mensaje_minusculas or "estado" in mensaje_minusculas or "mesa" in mensaje_minusculas:
        
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
    elif "espacio" in mensaje_minusculas or "disponibilidad" in mensaje_minusculas or "lleno" in mensaje_minusculas or "ocupado" in mensaje_minusculas or "mesas" in mensaje_minusculas or "mañana" in mensaje_minusculas or "hoy" in mensaje_minusculas:
        
        from datetime import date
        fecha_hoy = date.today() # ¡El reloj del sistema!
        
        # Consultamos TODAS las reservas confirmadas de hoy en adelante
        reservas_activas = Reserva.query.filter(Reserva.estado == 'Confirmada', Reserva.fecha_reserva >= fecha_hoy).all()
        
        # Armamos un diccionario contando cuántas mesas están ocupadas por día
        resumen_fechas = {}
        for res in reservas_activas:
            fecha_str = str(res.fecha_reserva) # Ej: '2026-03-10'
            resumen_fechas[fecha_str] = resumen_fechas.get(fecha_str, 0) + 1
            
        contexto_datos = f"""
        El usuario quiere saber la disponibilidad de mesas de Detalle Añejo.
        IMPORTANTE: Nuestra capacidad máxima por noche es de 10 mesas en el parral.
        
        ⏳ FECHA ACTUAL DEL SISTEMA: {fecha_hoy}
        (Usa esta fecha exacta como punto de partida cuando el usuario diga "hoy", "mañana", "el viernes", etc.)
        
        Aquí tienes el reporte de las mesas YA CONFIRMADAS por fecha:
        {resumen_fechas}
        
        Instrucción Estricta: 
        1. Analiza para cuándo quiere la mesa el usuario (calcula la fecha basándote en la fecha actual).
        2. Revisa el reporte. Si la fecha no aparece en el reporte, significa que hay 0 reservas (tenemos las 10 mesas libres).
        3. Si la fecha tiene 7 o más mesas ocupadas, dile que hay alta demanda y sugiérele reservar urgente.
        4. Si tiene menos de 7, dile con entusiasmo que hay excelente disponibilidad y anímalo a agendar su cena romántica.
        """
        
    # 4. RESPUESTA POR DEFECTO
    else:
        contexto_datos = """
        El usuario saluda o hace una pregunta general. 
        Instruccion: Dale la bienvenida a Detalle Anejo y dile brevemente que puedes ayudarle a:
        1. Recomendarle un menu.
        2. Revisar el estado de sus reservas.
        3. Consultar los datos de su cuenta.
        """
        
    respuesta_ia = consultar_gemini(mensaje_original, contexto_datos)
    return jsonify({'respuesta': respuesta_ia})