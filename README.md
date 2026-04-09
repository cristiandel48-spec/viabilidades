# M&D — Viabilidad de Precios

Aplicación web en Python/Flask para gestionar el flujo de viabilidades de precios de **FAJAS M&D**, con base de datos en Supabase.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+ / Flask |
| Base de datos | Supabase (PostgreSQL) |
| Frontend | HTML/CSS/Jinja2 (sin dependencias externas) |
| Deploy | Render / Railway / Fly.io |

---

## Estructura del proyecto

```
viabilidad-myd/
├── app/
│   ├── __init__.py          # Flask factory
│   ├── routes.py            # Todas las rutas
│   ├── calculos.py          # Lógica financiera (IVA, márgenes, canales)
│   ├── supabase_client.py   # Conexión a Supabase
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── viabilidad_form.html
│       ├── detalle.html
│       └── admin_destinatarios.html
├── migrations/
│   └── 001_init.sql         # SQL para crear las tablas en Supabase
├── run.py                   # Punto de entrada
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Configuración local

### 1. Clonar y crear entorno virtual

```bash
git clone https://github.com/tu-usuario/viabilidad-myd.git
cd viabilidad-myd
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales de Supabase:

```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=tu-anon-public-key
SECRET_KEY=una-clave-secreta-larga-y-random
```

### 3. Crear las tablas en Supabase

1. Ve a **Supabase → SQL Editor**
2. Copia y ejecuta el contenido de `migrations/001_init.sql`

### 4. Correr en local

```bash
python run.py
```

Abre `http://localhost:5000`

---

## Usuarios demo

| Usuario | Contraseña | Puede hacer |
|---|---|---|
| `mercadeo` | `myd123` | Ingresar precios COP y USD |
| `costos` | `myd123` | Ingresar referencia, costo estimado, costo real |
| `finanzas` | `myd123` | Aprobar fases, asignar precio definitivo, cerrar |
| `admin` | `admin123` | Todo lo anterior + gestión de destinatarios |

> Para producción: reemplazar la autenticación demo con **Supabase Auth**.

---

## Flujo de viabilidad

```
[Costos/Mercadeo] Crea viabilidad
         ↓
[Todos] Ingresan su parte (precios, costos, margen objetivo)
         ↓
[Finanzas] Revisa margen → Aprueba Fase 1
         ↓
[Costos] Ingresa costos reales del corrido de materiales → Envía a Finanzas
         ↓
[Finanzas] Revisa margen final → Asigna precio definitivo → Cierra y notifica
```

---

## Tablas en Supabase

| Tabla | Descripción |
|---|---|
| `viabilidades` | Registro principal con todos los campos por fase |
| `notif_destinatarios` | Emails por viabilidad |
| `destinatarios_globales` | Emails globales (admin) |
| `viabilidad_historial` | Log de cambios por usuario |

---

## Deploy en Render (gratuito)

1. Sube el proyecto a GitHub
2. Crea un nuevo **Web Service** en [render.com](https://render.com)
3. Conecta tu repositorio
4. Configura:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn run:app`
5. Agrega las variables de entorno (`SUPABASE_URL`, `SUPABASE_KEY`, `SECRET_KEY`)

Agrega `gunicorn` al `requirements.txt` para producción:
```
gunicorn==21.2.0
```

---

## Próximos pasos sugeridos

- [ ] Integrar **Supabase Auth** para login real por email
- [ ] Envío real de correos con **Resend** o **SendGrid**
- [ ] Exportar viabilidad a PDF
- [ ] Notificaciones en tiempo real con Supabase Realtime
