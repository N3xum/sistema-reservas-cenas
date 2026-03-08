from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import Menu
from . import db

# Creamos el Blueprint para el módulo de menús
menu_bp = Blueprint('menu_bp', __name__)

# 1. LEER (Listado con buscador)
@menu_bp.route('/menus')
@login_required
def listar_menus():
    busqueda = request.args.get('busqueda', '')
    if busqueda:
        # Filtro de búsqueda requerido por el examen
        menus = Menu.query.filter(Menu.nombre_experiencia.contains(busqueda)).all()
    else:
        menus = Menu.query.all()
    return render_template('listar_menus.html', menus=menus, busqueda=busqueda)

# 2. CREAR
@menu_bp.route('/menus/crear', methods=['GET', 'POST'])
@login_required
def crear_menu():
    if current_user.rol != 'administrador':
        flash('Solo el administrador puede crear menús.')
        return redirect(url_for('menu_bp.listar_menus'))

    if request.method == 'POST':
        nombre = request.form['nombre_experiencia']
        precio = request.form['precio']
        
        # Validación requerida por el examen
        if float(precio) <= 0:
            flash('El precio debe ser un valor válido y mayor a 0.')
            return redirect(url_for('menu_bp.crear_menu'))

        nuevo_menu = Menu(
            nombre_experiencia=nombre,
            descripcion=request.form['descripcion'],
            precio=precio,
            disponibilidad='disponibilidad' in request.form
        )
        db.session.add(nuevo_menu)
        db.session.commit()
        flash('Nueva experiencia gastronómica añadida con éxito.')
        return redirect(url_for('menu_bp.listar_menus'))
        
    return render_template('crear_menu.html')

# 3. EDITAR
@menu_bp.route('/menus/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_menu(id):
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('menu_bp.listar_menus'))

    menu = Menu.query.get_or_404(id)

    if request.method == 'POST':
        menu.nombre_experiencia = request.form['nombre_experiencia']
        menu.descripcion = request.form['descripcion']
        menu.precio = request.form['precio']
        menu.disponibilidad = 'disponibilidad' in request.form
        
        db.session.commit()
        flash('Menú actualizado correctamente.')
        return redirect(url_for('menu_bp.listar_menus'))

    return render_template('editar_menu.html', menu=menu)

# 4. ELIMINAR
@menu_bp.route('/menus/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_menu(id):
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('menu_bp.listar_menus'))

    menu = Menu.query.get_or_404(id)
    db.session.delete(menu)
    db.session.commit()
    flash('Menú eliminado del catálogo.')
    return redirect(url_for('menu_bp.listar_menus'))