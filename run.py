from app import create_app
from flask_migrate import upgrade

app = create_app()


with app.app_context():
    try:
        # Esto lee la carpeta "migrations" y crea/actualiza 
        # las tablas en MySQL automáticamente sin usar la terminal.
        upgrade()
        print("✅ Base de datos sincronizada y tablas actualizadas correctamente.")
    except Exception as e:
        print("⚠️ Atención: Asegúrate de haber creado la base de datos 'reservas_db' en tu XAMPP/MySQL.")
        print(f"Error detallado: {e}")

if __name__ == '__main__':
    app.run(debug=True)