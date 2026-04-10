from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import traceback

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # Modo debug solo en local
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    from .routes import bp
    app.register_blueprint(bp)

    # Manejador de errores 500 — muestra el error real
    @app.errorhandler(500)
    def internal_error(e):
        tb = traceback.format_exc()
        # En producción muestra el traceback para poder depurar
        return f"""
        <h2 style='font-family:monospace;color:red'>Error 500 — Internal Server Error</h2>
        <pre style='font-family:monospace;font-size:12px;background:#f5f5f5;padding:1rem;border-radius:8px;overflow-x:auto'>{tb}</pre>
        <p style='font-family:monospace'>Verifica que las variables de entorno SUPABASE_URL, SUPABASE_KEY y SECRET_KEY estén configuradas en Vercel.</p>
        """, 500

    @app.errorhandler(404)
    def not_found(e):
        return f"<h2>404 — Página no encontrada</h2><p><a href='/'>Ir al inicio</a></p>", 404

    return app
