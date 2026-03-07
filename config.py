import os

class Config:
    # Clave secreta para la seguridad de las sesiones de Flask-Login
    SECRET_KEY = 'clave_secreta_super_segura'

    # Configuración de conexión a MySQL
    # OJO: Si tu MySQL tiene contraseña, ponla después de 'root:'. 
    # Si usas XAMPP por defecto, suele ser 'root' sin contraseña.
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/reservas_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False