from . import db
from flask_login import UserMixin
from datetime import datetime

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='cliente') # 'administrador' o 'cliente'
    telefono = db.Column(db.String(20))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación 1 a N: Un usuario puede tener muchas reservas
    reservas = db.relationship('Reserva', backref='cliente', lazy=True)

class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.Integer, primary_key=True)
    nombre_experiencia = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    disponibilidad = db.Column(db.Boolean, default=True)
    imagen_referencial = db.Column(db.String(255)) # Útil para el reto de subida de archivos

    # Relación 1 a N: Un menú puede estar en muchas reservas
    reservas = db.relationship('Reserva', backref='menu_elegido', lazy=True)

class Reserva(db.Model):
    __tablename__ = 'reservas'
    id = db.Column(db.Integer, primary_key=True)
    # Claves foráneas para relacionar las tablas
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    
    fecha_reserva = db.Column(db.Date, nullable=False)
    hora_reserva = db.Column(db.Time, nullable=False)
    cantidad_personas = db.Column(db.Integer, nullable=False)
    ubicacion_mesa = db.Column(db.String(50)) # Opciones: "Bajo el parral", "Comedor interior", etc.
    estado = db.Column(db.String(20), default='Pendiente') # Pendiente, Confirmada, Cancelada
    notas_especiales = db.Column(db.Text)