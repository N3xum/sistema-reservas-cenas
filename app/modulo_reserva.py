import os
import io
import openpyxl
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import Reserva, Menu
from . import db
from .ia_service import consultar_gemini

reserva_bp = Blueprint('reserva_bp', __name__)

# Configuración de la carpeta para guardar comprobantes
CARPETA_COMPROBANTES = 'app/static/comprobantes'

# 1. LEER (Listado con filtro de estado) y RETO EXTRA
@reserva_bp.route('/reservas')
@login_required
def listar_reservas():
    # Filtro obligatorio: por estado de la reserva
    estado_filtro = request.args.get('estado', '')
    
    # Lógica de vistas: Admin ve todo, Cliente ve solo lo suyo
    query = Reserva.query
    if current_user.rol != 'administrador':
        query = query.filter_by(usuario_id=current_user.id)
        
    if estado_filtro:
        query = query.filter(Reserva.estado == estado_filtro)
        
    reservas = query.all()
    return render_template('listar_reservas.html', reservas=reservas, estado_filtro=estado_filtro)

# 2. CREAR (El cliente reserva una cena y sube el pago)
@reserva_bp.route('/reservas/crear/<int:menu_id>', methods=['GET', 'POST'])
@login_required
def crear_reserva(menu_id):
    menu = Menu.query.get_or_404(menu_id)
    
    if request.method == 'POST':
        fecha_reserva_str = request.form['fecha_reserva']
        fecha_obj = datetime.strptime(fecha_reserva_str, '%Y-%m-%d').date()
        
        # Validación: No permitir reservas en el pasado
        if fecha_obj < datetime.now().date():
            flash('La fecha de la reserva no puede ser en el pasado.')
            return redirect(url_for('reserva_bp.crear_reserva', menu_id=menu_id))

        # Lógica para subir el comprobante de pago
        comprobante = request.files.get('comprobante')
        nombre_comprobante = None
        
        if comprobante and comprobante.filename != '':
            nombre_comprobante = secure_filename(comprobante.filename)
            ruta_guardado = os.path.join(CARPETA_COMPROBANTES, nombre_comprobante)
            # Crea la carpeta automáticamente si no existe
            os.makedirs(CARPETA_COMPROBANTES, exist_ok=True)
            comprobante.save(ruta_guardado)

        nueva_reserva = Reserva(
            usuario_id=current_user.id,
            menu_id=menu.id,
            fecha_reserva=fecha_obj,
            hora_reserva=request.form['hora_reserva'],
            cantidad_personas=request.form['cantidad_personas'],
            ubicacion_mesa=request.form['ubicacion_mesa'],
            notas_especiales=request.form['notas_especiales'],
            comprobante_pago=nombre_comprobante  # Se guarda el nombre del archivo en la BD
        )
        db.session.add(nueva_reserva)
        db.session.commit()
        flash('¡Tu reserva y pago han sido enviados! Te confirmaremos pronto.')
        return redirect(url_for('reserva_bp.listar_reservas'))
        
    return render_template('crear_reserva.html', menu=menu)

# 3. EDITAR (Admin cambia el estado o detalles)
@reserva_bp.route('/reservas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_reserva(id):
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('reserva_bp.listar_reservas'))

    reserva = Reserva.query.get_or_404(id)

    if request.method == 'POST':
        reserva.estado = request.form['estado']
        reserva.ubicacion_mesa = request.form['ubicacion_mesa']
        db.session.commit()
        flash('Reserva actualizada correctamente.')
        return redirect(url_for('reserva_bp.listar_reservas'))

    return render_template('editar_reserva.html', reserva=reserva)

# 4. ELIMINAR (Cancelar reserva)
@reserva_bp.route('/reservas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_reserva(id):
    reserva = Reserva.query.get_or_404(id)
    
    # Solo el admin o el dueño de la reserva pueden cancelarla
    if current_user.rol != 'administrador' and reserva.usuario_id != current_user.id:
        flash('Acceso denegado.')
        return redirect(url_for('reserva_bp.listar_reservas'))

    db.session.delete(reserva)
    db.session.commit()
    flash('La reserva ha sido cancelada.')
    return redirect(url_for('reserva_bp.listar_reservas'))

# ==========================================
# RETO: Exportar a Excel
# ==========================================
@reserva_bp.route('/reservas/exportar')
@login_required
def exportar_excel():
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('reserva_bp.listar_reservas'))

    reservas = Reserva.query.order_by(Reserva.fecha_reserva).all()
    
    # Crear un libro de Excel en memoria
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Reservas"
    
    # Encabezados de las columnas
    ws.append(['ID', 'Cliente', 'Menú', 'Fecha', 'Hora', 'Personas', 'Ubicación', 'Estado'])
    
    # Llenar los datos
    for r in reservas:
        ws.append([
            r.id, 
            r.cliente.nombre, 
            r.menu_elegido.nombre_experiencia, 
            r.fecha_reserva.strftime('%Y-%m-%d'), 
            r.hora_reserva.strftime('%H:%M'), 
            r.cantidad_personas, 
            r.ubicacion_mesa, 
            r.estado
        ])
    
    # Guardar en un objeto de memoria para descargarlo directamente
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(output, download_name="Reporte_Cenas.xlsx", as_attachment=True)

@reserva_bp.route('/analisis_ia_reservas')
@login_required
def analisis_ia_reservas():
    # Solo el administrador puede ver esto
    if current_user.rol != 'administrador':
        return redirect(url_for('usuario_bp.dashboard'))
    
    # Jhilda: Contamos cómo están las reservas
    confirmadas = Reserva.query.filter_by(estado='Confirmada').count()
    pendientes = Reserva.query.filter_by(estado='Pendiente').count()
    canceladas = Reserva.query.filter_by(estado='Cancelada').count()
    
    contexto = f"Datos actuales: {confirmadas} confirmadas, {pendientes} pendientes de revisión y {canceladas} canceladas."
    pregunta = "Eres la IA analista de Detalle Añejo. Analiza el estado de las reservas. Si hay muchas canceladas, sugiere una estrategia de retención. Si hay muchas pendientes, avísale al administrador que debe apurarse a revisarlas para no perder clientes. Dame una predicción simple para la operación de la cocina."
    
    analisis = consultar_gemini(pregunta, contexto)
    
    return render_template('analisis_reservas.html', 
                           confirmadas=confirmadas, 
                           pendientes=pendientes, 
                           canceladas=canceladas, 
                           analisis_ia=analisis)