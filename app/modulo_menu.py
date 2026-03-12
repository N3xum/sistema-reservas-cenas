import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import Menu
from . import db
from .ia_service import consultar_gemini

# Crear el Blueprint para el módulo de menús
menu_bp = Blueprint('menu_bp', __name__)

# Configurar de la carpeta donde se guardarán las fotos
CARPETA_IMAGENES = 'app/static/img/menus'

# 1. LEER (Listado con buscador)
@menu_bp.route('/menus')
@login_required
def listar_menus():
    busqueda = request.args.get('busqueda', '')
    if busqueda:
        # Filtro de búsqueda 
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
        
        # Validación
        if float(precio) <= 0:
            flash('El precio debe ser un valor válido y mayor a 0.')
            return redirect(url_for('menu_bp.crear_menu'))

        # guardar la imagen
        imagen = request.files.get('imagen')
        nombre_imagen = '' # Vacío si el usuario no sube ninguna foto
        
        if imagen and imagen.filename != '':
            nombre_imagen = secure_filename(imagen.filename)
            ruta_guardado = os.path.join(CARPETA_IMAGENES, nombre_imagen)
            
            # Crea la carpeta automáticamente si no existe
            os.makedirs(CARPETA_IMAGENES, exist_ok=True)
            imagen.save(ruta_guardado)

        nuevo_menu = Menu(
            nombre_experiencia=nombre,
            descripcion=request.form['descripcion'],
            precio=precio,
            disponibilidad='disponibilidad' in request.form,
            imagen_referencial=nombre_imagen # Se guarda el nombre en la Base de Datos
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
        
        # Lógica para actualizar la foto si sube una nueva
        imagen = request.files.get('imagen')
        if imagen and imagen.filename != '':
            nombre_imagen = secure_filename(imagen.filename)
            ruta_guardado = os.path.join(CARPETA_IMAGENES, nombre_imagen)
            os.makedirs(CARPETA_IMAGENES, exist_ok=True)
            imagen.save(ruta_guardado)
            
            # Actualizar el nombre del archivo en la BD solo si subió una nueva
            menu.imagen_referencial = nombre_imagen
        
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


#analisis menu (Dashboard)

@menu_bp.route('/analisis_ia_menus')
@login_required
def analisis_ia_menus():
    if current_user.rol != 'administrador':
        return redirect(url_for('usuario_bp.dashboard'))
    
    # Traemos todos los menús para analizarlos
    menus = Menu.query.all()
    
    # CORREGIDO: Usamos nombre_experiencia para el gráfico
    nombres = [m.nombre_experiencia for m in menus]
    precios = [float(m.precio) for m in menus]
    
    # CORREGIDO: Usamos nombre_experiencia para el contexto de la IA
    contexto = f"Tenemos {len(menus)} menús. Lista con precios: " + ", ".join([f"{m.nombre_experiencia} ({m.precio} Bs)" for m in menus])
    pregunta = "Eres un consultor gastronómico analizando la carta de Detalle Añejo. Revisa nuestros menús y precios. ¿Tenemos una oferta equilibrada? Genera un párrafo corto dándole al administrador un consejo de negocio sobre estos precios."
    
    analisis = consultar_gemini(pregunta, contexto)
    
    return render_template('analisis_menus.html', 
                           nombres=nombres, 
                           precios=precios, 
                           analisis_ia=analisis)