import sys
import os

# Agrega la raíz del proyecto al path para que Flask encuentre el módulo "app"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

# Vercel necesita que el objeto se llame "app"
# No uses app.run() aquí — Vercel lo maneja solo
