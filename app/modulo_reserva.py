from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from datetime import datetime
import io
import openpyxl
from .models import Reserva, Menu
from . import db

reserva_bp = Blueprint('reserva_bp', __name__)

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

# 2. CREAR (El cliente reserva una cena)
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

        nueva_reserva = Reserva(
            usuario_id=current_user.id,
            menu_id=menu.id,
            fecha_reserva=fecha_obj,
            hora_reserva=request.form['hora_reserva'],
            cantidad_personas=request.form['cantidad_personas'],
            ubicacion_mesa=request.form['ubicacion_mesa'],
            notas_especiales=request.form['notas_especiales']
        )
        db.session.add(nueva_reserva)
        db.session.commit()
        flash('¡Tu reserva ha sido enviada! Te confirmaremos pronto.')
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