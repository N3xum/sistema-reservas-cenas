from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Usuario
from . import db
from .ia_service import consultar_gemini
# Creamos el Blueprint para este módulo
usuario_bp = Blueprint('usuario_bp', __name__)

# ==========================================
# RUTA PRINCIPAL (Redirección)
# ==========================================
@usuario_bp.route('/')
def index():
    # Si alguien entra a la raiz, lo mandamos al login
    return redirect(url_for('usuario_bp.login'))



# ==========================================
# 1. AUTENTICACIÓN
# ==========================================
@usuario_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        rol = 'cliente' # Por defecto será cliente

        # Validación: Verificar si el correo ya existe [cite: 45]
        if Usuario.query.filter_by(email=email).first():
            flash('El correo ya está registrado.')
            return redirect(url_for('usuario_bp.registro'))

        # Hash de contraseña 
        password_hash = generate_password_hash(password)
        
        nuevo_usuario = Usuario(nombre=nombre, email=email, password_hash=password_hash, rol=rol)
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Registro exitoso. Ahora puedes iniciar sesión.')
        return redirect(url_for('usuario_bp.login'))
        
    return render_template('registro.html')

@usuario_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        usuario = Usuario.query.filter_by(email=email).first()

        # Verificamos que el usuario exista y la contraseña coincida con el hash
        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            return redirect(url_for('usuario_bp.dashboard'))
        else:
            flash('Correo o contraseña incorrectos.')
            
    return render_template('login.html')

@usuario_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('usuario_bp.login'))

@usuario_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ==========================================
# 2. CRUD DE USUARIOS (Con restricción de vistas)
# ==========================================
@usuario_bp.route('/usuarios')
@login_required
def listar_usuarios():
    # Restricción de vistas según rol
    if current_user.rol != 'administrador':
        flash('Acceso denegado. Esta vista es solo para administradores.')
        return redirect(url_for('usuario_bp.dashboard'))

    # Leer (listado con bsqueda o filtro) 
    busqueda = request.args.get('busqueda', '')
    if busqueda:
        # Filtra los usuarios si se escribió algo en el buscador
        usuarios = Usuario.query.filter(Usuario.nombre.contains(busqueda)).all()
    else:
        # Muestra todos si no hay búsqueda
        usuarios = Usuario.query.all()
        
    return render_template('listar_usuarios.html', usuarios=usuarios, busqueda=busqueda)

@usuario_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    # Restricción: Solo el administrador puede editar
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('usuario_bp.dashboard'))

    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        nuevo_email = request.form['email']
        
        # Validación: Revisar que el nuevo correo no pertenezca a otra persona
        email_existente = Usuario.query.filter(Usuario.email == nuevo_email, Usuario.id != id).first()
        if email_existente:
            flash('Ese correo ya está en uso por otro usuario.')
        else:
            usuario.nombre = request.form['nombre']
            usuario.email = nuevo_email
            usuario.rol = request.form['rol']
            
            db.session.commit()
            flash('Usuario actualizado correctamente.')
            return redirect(url_for('usuario_bp.listar_usuarios'))

    return render_template('editar_usuario.html', usuario=usuario)

@usuario_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('usuario_bp.dashboard'))

    usuario = Usuario.query.get_or_404(id)
    
    # Validación: Evitar que el admin se borre a sí mismo
    if usuario.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta mientras estás en sesión.')
        return redirect(url_for('usuario_bp.listar_usuarios'))

    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario eliminado del sistema.')
    return redirect(url_for('usuario_bp.listar_usuarios'))

@usuario_bp.route('/crear_usuario_interno', methods=['GET', 'POST'])
@login_required
def crear_usuario_interno():
    # Restricción: Solo el administrador puede crear usuarios internamente
    if current_user.rol != 'administrador':
        flash('Acceso denegado.')
        return redirect(url_for('usuario_bp.dashboard'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        rol = request.form['rol']

        if Usuario.query.filter_by(email=email).first():
            flash('El correo ya está registrado en el sistema.')
            return redirect(url_for('usuario_bp.crear_usuario_interno'))

        password_hash = generate_password_hash(password)
        nuevo_usuario = Usuario(nombre=nombre, email=email, password_hash=password_hash, rol=rol)
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash(f'Usuario {nombre} creado exitosamente como {rol}.')
        return redirect(url_for('usuario_bp.listar_usuarios'))
        
    return render_template('crear_usuario_interno.html')

@usuario_bp.route('/analisis_ia_clientes')
@login_required
def analisis_ia_clientes():
    if current_user.rol != 'administrador':
        flash('Acceso denegado al panel de inteligencia.')
        return redirect(url_for('usuario_bp.dashboard'))
    
    # 1. Extraer datos reales de tu tabla Usuario
    total_usuarios = Usuario.query.count()
    clientes = Usuario.query.filter_by(rol='cliente').count()
    admins = Usuario.query.filter_by(rol='administrador').count()
    
    # 2. Armar el contexto para la IA
    contexto_datos = f"Total de cuentas: {total_usuarios}. Clientes: {clientes}. Administradores del sistema: {admins}."
    pregunta_admin = "Genera un breve párrafo analizando el tamaño de nuestra base de clientes registrados. Comenta sobre la proporción entre clientes y administradores, e indica si es una métrica saludable para el inicio de operaciones de nuestro restaurante rústico."
    
    # 3. Consultar a Gemini
    analisis_generado = consultar_gemini(pregunta_admin, contexto_datos)
    
    # 4. Enviar los datos y la respuesta de la IA al HTML
    return render_template('analisis_clientes.html', 
                           clientes=clientes, 
                           admins=admins, 
                           analisis_ia=analisis_generado)

