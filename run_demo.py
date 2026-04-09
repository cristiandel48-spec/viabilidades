"""
M&D — Viabilidad de Precios
Versión LOCAL sin Supabase — datos en memoria
Correr con: python run_demo.py
Abrir en:   http://localhost:5000
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from app.calculos import calcular_metricas, variacion_costo, fmt_cop
from datetime import datetime

app = Flask(__name__)
app.secret_key = "myd-demo-local-2025"

# ─── Datos en memoria ───────────────────────
VIABILIDADES = {}
_id_counter = [1]

USUARIOS = {
    "mercadeo": {"password": "myd123",   "rol": "mercadeo", "nombre": "Equipo Mercadeo"},
    "costos":   {"password": "myd123",   "rol": "costos",   "nombre": "Equipo Costos"},
    "finanzas": {"password": "myd123",   "rol": "finanzas", "nombre": "Equipo Finanzas"},
    "admin":    {"password": "admin123", "rol": "admin",    "nombre": "Administrador"},
}

# ─── Helpers ────────────────────────────────
def usuario_actual():
    return session.get("usuario")

def rol_actual():
    u = usuario_actual()
    return USUARIOS[u]["rol"] if u else None

def requiere_login():
    if not usuario_actual():
        return redirect(url_for("login"))
    return None

def nuevo_id():
    vid = str(_id_counter[0])
    _id_counter[0] += 1
    return vid

def _float(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except:
        return None

def _int(v):
    try:
        return int(str(v).strip())
    except:
        return None

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# ─── Plantillas inline ──────────────────────
BASE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}M&D Viabilidad{% endblock %}</title>
<style>
:root{--myd:#c2185b;--myd-dark:#8e0038;--myd-light:#fce4ec;--border:#ede0e8;--bg:#f8f4f6;--text:#1a1118;--text2:#7a5a6a}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.topbar{background:var(--myd);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(194,24,91,.3)}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none}
.brand img{height:32px;object-fit:contain}
.brand-fb{color:#fff;font-weight:700;font-size:20px;display:none}
.brand-sep{width:1px;height:22px;background:rgba(255,255,255,.35)}
.brand-lbl{font-size:13px;font-weight:500;color:rgba(255,255,255,.92)}
.tnav{display:flex;align-items:center;gap:6px}
.tnav a{color:rgba(255,255,255,.82);text-decoration:none;font-size:13px;padding:5px 12px;border-radius:6px;transition:background .15s}
.tnav a:hover{background:rgba(255,255,255,.18);color:#fff}
.upill{display:flex;align-items:center;gap:7px;background:rgba(255,255,255,.15);border-radius:100px;padding:4px 12px 4px 8px}
.udot{width:24px;height:24px;border-radius:50%;background:#fff;color:var(--myd);font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center}
.uname{font-size:12px;color:#fff;font-weight:500}
.wrap{max-width:1100px;margin:0 auto;padding:1.5rem}
.ph{font-size:22px;font-weight:600;margin-bottom:4px}
.ps{font-size:14px;color:var(--text2);margin-bottom:1.5rem}
.flash{padding:10px 16px;border-radius:8px;font-size:13px;font-weight:500;margin-bottom:1rem}
.flash.ok{background:var(--myd-light);color:var(--myd-dark);border:1px solid #f48fb1}
.flash.error{background:#ffebee;color:#c62828;border:1px solid #ef9a9a}
.card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:1.25rem;margin-bottom:1rem}
.ct{font-size:14px;font-weight:600;margin-bottom:.875rem;display:flex;align-items:center;gap:8px}
.rb{font-size:11px;padding:2px 8px;border-radius:100px;font-weight:500}
.rb-m{background:var(--myd-light);color:var(--myd-dark)}
.rb-c{background:#e3f2fd;color:#0d47a1}
.rb-f{background:#fff3e0;color:#e65100}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:700px){.g4,.g3{grid-template-columns:1fr 1fr}.g2{grid-template-columns:1fr}}
.fg{display:flex;flex-direction:column;gap:5px}
.fl{font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.05em}
input,select,textarea{width:100%;padding:8px 10px;font-size:13px;border:1px solid #ddd0d8;border-radius:6px;background:#fff;color:var(--text);font-family:inherit;outline:none;transition:border-color .15s}
input:focus,select:focus,textarea:focus{border-color:var(--myd);box-shadow:0 0 0 3px rgba(194,24,91,.1)}
input:disabled,textarea:disabled,select:disabled{background:var(--bg);color:#9e9099;cursor:not-allowed}
.ro{font-size:13px;padding:8px 10px;background:var(--bg);border-radius:6px;color:var(--text);border:1px solid var(--border);min-height:36px}
.bp{padding:9px 22px;background:var(--myd);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-block;transition:background .15s}
.bp:hover{background:var(--myd-dark)}
.bp:disabled{opacity:.4;cursor:not-allowed}
.bs{padding:9px 22px;background:#fff;color:var(--text);border:1px solid #ddd0d8;border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-block;transition:background .15s}
.bs:hover{background:var(--bg)}
.bsm{padding:5px 12px;font-size:12px}
.bx{padding:5px 12px;font-size:12px;border-radius:6px;background:#ffebee;color:#c62828;border:1px solid #ef9a9a;cursor:pointer;font-family:inherit}
.bx:hover{background:#c62828;color:#fff}
.ar{display:flex;gap:8px;justify-content:flex-end;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border)}
.mets{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:1rem}
@media(max-width:700px){.mets{grid-template-columns:1fr 1fr}}
.met{background:var(--bg);border-radius:8px;padding:.875rem}
.ml{font-size:12px;color:var(--text2);margin-bottom:4px}
.mv{font-size:20px;font-weight:600;color:var(--text)}
.mok .mv{color:var(--myd-dark)}
.mbad .mv{color:#c62828}
.mwarn .mv{color:#e65100}
.mbar{height:6px;border-radius:3px;background:var(--border);margin-top:6px;overflow:hidden}
.mfill{height:100%;border-radius:3px;background:var(--myd)}
.aok{background:var(--myd-light);border:1px solid #f48fb1;color:var(--myd-dark);border-radius:8px;padding:.75rem 1rem;font-size:13px;margin-bottom:.875rem}
.awk{background:#fff3e0;border:1px solid #ffcc80;color:#e65100;border-radius:8px;padding:.75rem 1rem;font-size:13px;margin-bottom:.875rem}
.tbl{width:100%;font-size:13px;border-collapse:collapse}
.tbl th{text-align:left;font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.04em;padding:8px 10px;border-bottom:1px solid var(--border)}
.tbl td{padding:8px 10px;border-bottom:1px solid #f5f0f2;color:var(--text)}
.tbl tr:last-child td{border-bottom:none}
.tbl tbody tr:hover td{background:var(--myd-light)}
.stt{display:inline-block;font-size:11px;padding:2px 8px;border-radius:100px;font-weight:600}
.s0{background:#e3f2fd;color:#0d47a1}
.s1{background:#fff3e0;color:#e65100}
.s2{background:#f3e5f5;color:#6a1b9a}
.sc{background:#e8f5e9;color:#2e7d32}
.pbar{display:flex;align-items:center;background:#fff;border-bottom:1px solid var(--border);padding:.75rem 1.5rem;gap:4px}
.pi{display:flex;align-items:center;gap:8px;padding:7px 14px;border-radius:8px;cursor:pointer;white-space:nowrap;text-decoration:none}
.pi:hover{background:var(--myd-light)}
.pnum{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;background:#f0e0e8;color:var(--myd-dark)}
.plbl{font-size:13px;color:var(--text2)}
.pi.pa .pnum{background:var(--myd);color:#fff}
.pi.pa .plbl{color:var(--text);font-weight:500}
.pi.pd .pnum{background:var(--myd-light);color:var(--myd-dark)}
.pi.pd .plbl{color:var(--myd)}
.pi.pl{opacity:.4;pointer-events:none}
.psep{color:#c9a0b4;font-size:16px;user-select:none}
.nref{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:1rem;font-size:13px;color:#5a4a54;line-height:1.8;font-family:'Courier New',monospace}
.nref strong{color:var(--text);font-family:inherit}
.erow{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f5f0f2}
.erow:last-child{border-bottom:none}
.erow span{flex:1;font-size:13px}
.demo-banner{background:#fff3e0;border-bottom:1px solid #ffcc80;padding:8px 1.5rem;font-size:12px;color:#e65100;text-align:center}
.demo-banner strong{font-weight:600}
</style>
</head>
<body>
{% if session.usuario %}
<div class="topbar">
  <a class="brand" href="/dashboard">
    <img src="https://fajasmyd.com/cdn/shop/files/LOGO_M_D-03.png?v=1757106759&width=220"
         alt="M&D" onerror="this.style.display='none';document.getElementById('bfb').style.display='block'">
    <span id="bfb" class="brand-fb">M&amp;D</span>
    <div class="brand-sep"></div>
    <span class="brand-lbl">Viabilidad de Precios</span>
  </a>
  <div class="tnav">
    <a href="/dashboard">Dashboard</a>
    <a href="/nueva">+ Nueva</a>
    <div class="upill">
      <div class="udot">{{ session.usuario[0]|upper }}</div>
      <span class="uname">{{ session.usuario|capitalize }}</span>
    </div>
    <a href="/logout" style="opacity:.7">Salir</a>
  </div>
</div>
<div class="demo-banner"><strong>Modo local</strong> — Los datos se guardan en memoria. Al reiniciar la app se borran.</div>
{% endif %}
{% with msgs = get_flashed_messages(with_categories=True) %}
  {% if msgs %}
  <div style="max-width:1100px;margin:.75rem auto 0;padding:0 1.5rem">
    {% for cat,msg in msgs %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}
  </div>
  {% endif %}
{% endwith %}
{% block content %}{% endblock %}
</body>
</html>"""


LOGIN_T = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--myd)">
  <div style="background:#fff;border-radius:16px;padding:2.5rem 2rem;width:100%;max-width:380px;box-shadow:0 8px 32px rgba(194,24,91,.2)">
    <div style="text-align:center;margin-bottom:1.5rem">
      <img src="https://fajasmyd.com/cdn/shop/files/LOGO_M_D-03.png?v=1757106759&width=220"
           style="height:44px;object-fit:contain" alt="M&D"
           onerror="this.style.display='none'">
    </div>
    <h1 style="font-size:20px;font-weight:600;text-align:center;margin-bottom:.25rem">Viabilidad de Precios</h1>
    <p style="font-size:13px;color:var(--text2);text-align:center;margin-bottom:1.5rem">Ingresa con tu usuario y contraseña</p>
    {% if error %}<div class="flash error">{{error}}</div>{% endif %}
    <form method="POST">
      <div class="fg" style="margin-bottom:.875rem">
        <label class="fl">Usuario</label>
        <select name="usuario">
          <option value="">Selecciona un rol...</option>
          <option value="mercadeo">Mercadeo</option>
          <option value="costos">Costos</option>
          <option value="finanzas">Finanzas</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <div class="fg" style="margin-bottom:1.25rem">
        <label class="fl">Contraseña</label>
        <input type="password" name="password" placeholder="Contraseña">
      </div>
      <button type="submit" class="bp" style="width:100%">Ingresar</button>
    </form>
    <p style="margin-top:1.25rem;font-size:11px;color:#b0a0b0;text-align:center">
      mercadeo / costos / finanzas → clave: <strong>myd123</strong><br>admin → clave: <strong>admin123</strong>
    </p>
  </div>
</div>
{% endblock %}""")


# ─── RUTAS ──────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if usuario_actual():
        return redirect("/dashboard")
    error = None
    if request.method == "POST":
        u = request.form.get("usuario", "")
        p = request.form.get("password", "")
        if u in USUARIOS and USUARIOS[u]["password"] == p:
            session["usuario"] = u
            return redirect("/dashboard")
        error = "Usuario o contraseña incorrectos"
    return render_template_string(LOGIN_T, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard")
def dashboard():
    if not usuario_actual():
        return redirect("/")
    u   = usuario_actual()
    rol = USUARIOS[u]["rol"]
    viabs = list(VIABILIDADES.values())
    return render_template_string(DASHBOARD_T,
        viabilidades=viabs, rol=rol,
        nombre=USUARIOS[u]["nombre"],
        total=len(viabs),
        en_proceso=sum(1 for v in viabs if not v.get("cerrada")),
        cerradas=sum(1 for v in viabs if v.get("cerrada")),
        viables=sum(1 for v in viabs if v.get("fase1_aprobada")),
    )


@app.route("/nueva", methods=["GET", "POST"])
def nueva():
    if not usuario_actual():
        return redirect("/")
    rol = rol_actual()
    if rol not in ("costos", "mercadeo", "admin"):
        flash("No tienes permiso para crear viabilidades", "error")
        return redirect("/dashboard")

    if request.method == "POST":
        vid = nuevo_id()
        VIABILIDADES[vid] = {
            "id":            vid,
            "referencia":    request.form.get("referencia", "").upper().strip(),
            "ref_madre":     request.form.get("ref_madre", "").strip(),
            "nombre":        request.form.get("nombre", "").strip(),
            "unidades":      _int(request.form.get("unidades")),
            "precio_cop_iva": _float(request.form.get("precio_cop_iva")),
            "precio_usd":    _float(request.form.get("precio_usd")),
            "costo_estimado": _float(request.form.get("costo_estimado")),
            "costo_linea":   _float(request.form.get("costo_linea")),
            "margen_objetivo": _float(request.form.get("margen_objetivo")) or 40.0,
            "costo_real":    None,
            "precio_final_cop": None,
            "precio_final_usd": None,
            "notas_finanzas": "",
            "fase":          1,
            "fase1_aprobada": False,
            "fase2_aprobada": False,
            "cerrada":       False,
            "creado_por":    usuario_actual(),
            "creado_at":     ahora(),
            "destinatarios": [
                {"id": "1", "email": "mercadeo@myd.com"},
                {"id": "2", "email": "costos@myd.com"},
                {"id": "3", "email": "finanzas@myd.com"},
            ],
            "historial": [{"usuario": usuario_actual(), "accion": "creación", "hora": ahora()}],
        }
        flash("Viabilidad creada correctamente", "ok")
        return redirect(f"/viabilidad/{vid}")

    return render_template_string(NUEVA_T, rol=rol)


@app.route("/viabilidad/<vid>")
def detalle(vid):
    if not usuario_actual():
        return redirect("/")
    v = VIABILIDADES.get(vid)
    if not v:
        flash("Viabilidad no encontrada", "error")
        return redirect("/dashboard")

    rol = rol_actual()

    metricas = None
    if v.get("precio_cop_iva") and v.get("costo_estimado"):
        metricas = calcular_metricas(v["precio_cop_iva"], v["costo_estimado"], v.get("margen_objetivo", 40))

    metricas_final = None
    costo_base = v.get("costo_real") or v.get("costo_estimado")
    if v.get("precio_final_cop") and costo_base:
        metricas_final = calcular_metricas(v["precio_final_cop"], costo_base, v.get("margen_objetivo", 40))

    variacion = None
    if v.get("costo_real") and v.get("costo_estimado"):
        variacion = round(variacion_costo(v["costo_real"], v["costo_estimado"]) * 100, 1)

    return render_template_string(DETALLE_T,
        v=v, rol=rol, vid=vid,
        metricas=metricas,
        metricas_final=metricas_final,
        variacion=variacion,
        fmt_cop=fmt_cop,
    )


@app.route("/viabilidad/<vid>/guardar", methods=["POST"])
def guardar(vid):
    if not usuario_actual():
        return redirect("/")
    v   = VIABILIDADES.get(vid)
    rol = rol_actual()
    if not v:
        return redirect("/dashboard")

    campos_rol = {
        "mercadeo": ["precio_cop_iva", "precio_usd"],
        "costos":   ["referencia", "ref_madre", "nombre", "unidades",
                     "costo_estimado", "costo_linea", "costo_real"],
        "finanzas": ["margen_objetivo", "precio_final_cop", "precio_final_usd", "notas_finanzas"],
        "admin":    ["referencia", "ref_madre", "nombre", "unidades",
                     "precio_cop_iva", "precio_usd", "costo_estimado", "costo_linea",
                     "margen_objetivo", "costo_real",
                     "precio_final_cop", "precio_final_usd", "notas_finanzas"],
    }

    for campo in campos_rol.get(rol, []):
        val = request.form.get(campo)
        if val is not None and val.strip() != "":
            if campo in ("referencia", "ref_madre", "nombre", "notas_finanzas"):
                v[campo] = val.strip()
            elif campo == "unidades":
                v[campo] = _int(val)
            else:
                v[campo] = _float(val)

    v["historial"].insert(0, {"usuario": usuario_actual(), "accion": f"edición fase {v['fase']}", "hora": ahora()})
    flash("Cambios guardados", "ok")
    return redirect(f"/viabilidad/{vid}")


@app.route("/viabilidad/<vid>/aprobar/1", methods=["POST"])
def aprobar_fase1(vid):
    if not usuario_actual():
        return redirect("/")
    rol = rol_actual()
    if rol not in ("finanzas", "admin"):
        flash("Solo Finanzas puede aprobar la Fase 1", "error")
        return redirect(f"/viabilidad/{vid}")
    v = VIABILIDADES.get(vid)
    if v:
        v["fase1_aprobada"] = True
        v["fase"] = 2
        v["historial"].insert(0, {"usuario": usuario_actual(), "accion": "aprobó Fase 1", "hora": ahora()})
        flash("Fase 1 aprobada. Costos puede ingresar el corrido de materiales.", "ok")
    return redirect(f"/viabilidad/{vid}")


@app.route("/viabilidad/<vid>/aprobar/2", methods=["POST"])
def aprobar_fase2(vid):
    if not usuario_actual():
        return redirect("/")
    rol = rol_actual()
    if rol not in ("costos", "admin"):
        flash("Solo Costos puede enviar el corrido a Finanzas", "error")
        return redirect(f"/viabilidad/{vid}")
    v = VIABILIDADES.get(vid)
    if v:
        v["fase2_aprobada"] = True
        v["fase"] = 3
        v["historial"].insert(0, {"usuario": usuario_actual(), "accion": "envió corrido a Finanzas", "hora": ahora()})
        flash("Corrido enviado a Finanzas para asignación final.", "ok")
    return redirect(f"/viabilidad/{vid}")


@app.route("/viabilidad/<vid>/cerrar", methods=["POST"])
def cerrar(vid):
    if not usuario_actual():
        return redirect("/")
    rol = rol_actual()
    if rol not in ("finanzas", "admin"):
        flash("Solo Finanzas puede cerrar la viabilidad", "error")
        return redirect(f"/viabilidad/{vid}")
    v = VIABILIDADES.get(vid)
    if not v:
        return redirect("/dashboard")
    if not v.get("precio_final_cop"):
        flash("Debes ingresar el precio final antes de cerrar", "error")
        return redirect(f"/viabilidad/{vid}")
    v["cerrada"] = True
    v["historial"].insert(0, {"usuario": usuario_actual(), "accion": "cerró la viabilidad", "hora": ahora()})
    flash(f"Viabilidad cerrada. Precio definitivo: {fmt_cop(v['precio_final_cop'])}", "ok")
    return redirect(f"/viabilidad/{vid}")


@app.route("/viabilidad/<vid>/dest/add", methods=["POST"])
def dest_add(vid):
    if not usuario_actual():
        return redirect("/")
    v = VIABILIDADES.get(vid)
    email = request.form.get("email", "").strip().lower()
    if v and "@" in email:
        nid = str(len(v.get("destinatarios", [])) + 10)
        v.setdefault("destinatarios", []).append({"id": nid, "email": email})
        flash(f"{email} agregado", "ok")
    else:
        flash("Email inválido", "error")
    return redirect(f"/viabilidad/{vid}")


@app.route("/viabilidad/<vid>/dest/rm/<did>", methods=["POST"])
def dest_rm(vid, did):
    if not usuario_actual():
        return redirect("/")
    v = VIABILIDADES.get(vid)
    if v:
        v["destinatarios"] = [d for d in v.get("destinatarios", []) if d["id"] != did]
    return redirect(f"/viabilidad/{vid}")


# ─── Templates ──────────────────────────────

DASHBOARD_T = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="wrap">
  <div class="ph">Dashboard</div>
  <div class="ps">Bienvenido, {{nombre}} &nbsp;·&nbsp; Rol: <strong>{{rol}}</strong></div>

  <div class="mets">
    <div class="met"><div class="ml">Total viabilidades</div><div class="mv">{{total}}</div></div>
    <div class="met"><div class="ml">En proceso</div><div class="mv" style="color:#0d47a1">{{en_proceso}}</div></div>
    <div class="met mok"><div class="ml">Cerradas</div><div class="mv">{{cerradas}}</div></div>
    <div class="met"><div class="ml">Fase 1 aprobadas</div><div class="mv" style="color:#6a1b9a">{{viables}}</div></div>
  </div>

  <div class="card">
    <div class="ct" style="justify-content:space-between">
      <span>Viabilidades de precio</span>
      <a href="/nueva" class="bp bsm">+ Nueva</a>
    </div>
    {% if viabilidades %}
    <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Referencia</th><th>Nombre</th><th>Precio lista COP</th><th>Costo estimado</th><th>Fase</th><th>Estado</th><th>Fecha</th><th></th></tr></thead>
      <tbody>
        {% for v in viabilidades %}
        <tr>
          <td><strong>{{v.referencia or '—'}}</strong></td>
          <td>{{v.nombre or '—'}}</td>
          <td>{% if v.precio_cop_iva %}${{ '{:,.0f}'.format(v.precio_cop_iva)|replace(',','.') }}{% else %}—{% endif %}</td>
          <td>{% if v.costo_estimado %}${{ '{:,.0f}'.format(v.costo_estimado)|replace(',','.') }}{% else %}—{% endif %}</td>
          <td>{{v.fase}}</td>
          <td>
            {% if v.cerrada %}<span class="stt sc">Cerrada</span>
            {% elif v.fase == 3 %}<span class="stt s2">Fase 3</span>
            {% elif v.fase == 2 %}<span class="stt s1">Fase 2</span>
            {% else %}<span class="stt s0">Fase 1</span>{% endif %}
          </td>
          <td style="font-size:12px;color:#b0a0b0">{{v.creado_at}}</td>
          <td><a href="/viabilidad/{{v.id}}" class="bs bsm">Ver</a></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    </div>
    {% else %}
    <div style="text-align:center;padding:2.5rem;color:#b0a0b0">
      <p style="margin-bottom:.75rem">No hay viabilidades aún</p>
      <a href="/nueva" class="bp">Crear la primera</a>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}""")


NUEVA_T = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="wrap">
  <div class="ph">Nueva viabilidad de precio</div>
  <div class="ps">Ingresa los datos iniciales.</div>
  <form method="POST" action="/nueva">
    <div class="card">
      <div class="ct">Identificación de referencia <span class="rb rb-c">Costos</span></div>
      <div class="g4">
        <div class="fg"><label class="fl">Referencia *</label><input type="text" name="referencia" required placeholder="Ej: B-06006" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Referencia madre</label><input type="text" name="ref_madre" placeholder="Ej: B-00006" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Nombre producto</label><input type="text" name="nombre" placeholder="Ej: Faja corta reloj de arena" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Unidades</label><input type="number" name="unidades" min="0" placeholder="Ej: 450" {{'disabled' if rol not in ('costos','admin')}}></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">Precios de venta <span class="rb rb-m">Mercadeo</span></div>
      <div class="g3">
        <div class="fg"><label class="fl">Precio con IVA (COP)</label><input type="number" name="precio_cop_iva" min="0" placeholder="Ej: 179900" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Precio USD</label><input type="number" name="precio_usd" min="0" step="0.5" placeholder="Ej: 41" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Margen objetivo (%)</label><input type="number" name="margen_objetivo" value="40" min="0" max="100" {{'disabled' if rol not in ('finanzas','admin')}}></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">Costos estimados de apertura <span class="rb rb-c">Costos</span></div>
      <div class="g2">
        <div class="fg"><label class="fl">Costo estimado producto (COP)</label><input type="number" name="costo_estimado" min="0" placeholder="Ej: 77497" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Costo de la línea (COP)</label><input type="number" name="costo_linea" min="0" placeholder="Ej: 5000" {{'disabled' if rol not in ('costos','admin')}}></div>
      </div>
    </div>
    <div class="ar" style="border:none;padding:0">
      <a href="/dashboard" class="bs">Cancelar</a>
      <button type="submit" class="bp">Crear viabilidad →</button>
    </div>
  </form>
</div>
{% endblock %}""")


DETALLE_T = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
{% macro fmtv(val) %}{% if val %}${{ '{:,.0f}'.format(val)|replace(',','.') }}{% else %}—{% endif %}{% endmacro %}
{% macro pctt(val) %}{% if val is not none %}{{ '%.1f'|format(val) }}%{% else %}—{% endif %}{% endmacro %}

<div class="pbar">
  <a class="pi {{'pa' if v.fase==1 else 'pd'}}" href="#f1"><div class="pnum">{{'✓' if v.fase>1 else '1'}}</div><span class="plbl">Viabilidad inicial</span></a>
  <span class="psep">›</span>
  <a class="pi {{'pa' if v.fase==2 else ('pd' if v.fase>2 else 'pl')}}" href="#f2"><div class="pnum">{{'✓' if v.fase>2 else '2'}}</div><span class="plbl">Corrido de materiales</span></a>
  <span class="psep">›</span>
  <a class="pi {{'pa' if v.fase==3 else 'pl'}}" href="#f3"><div class="pnum">3</div><span class="plbl">Asignación final</span></a>
</div>

<div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.25rem">
    <div>
      <div class="ph">{{v.referencia or 'Sin referencia'}} {% if v.nombre %}— {{v.nombre}}{% endif %}</div>
      <div class="ps">Ref. madre: {{v.ref_madre or '—'}} &nbsp;·&nbsp; Unidades: {{v.unidades or '—'}} &nbsp;·&nbsp; Creada: {{v.creado_at}}
        &nbsp;·&nbsp;
        {% if v.cerrada %}<span class="stt sc">Cerrada</span>
        {% elif v.fase==3 %}<span class="stt s2">Fase 3</span>
        {% elif v.fase==2 %}<span class="stt s1">Fase 2</span>
        {% else %}<span class="stt s0">Fase 1</span>{% endif %}
      </div>
    </div>
    <a href="/dashboard" class="bs bsm">← Volver</a>
  </div>

  <!-- FASE 1 -->
  <div id="f1">
  {% if not v.cerrada %}
  <form method="POST" action="/viabilidad/{{vid}}/guardar">
    <input type="hidden" name="fase" value="1">
    <div class="card">
      <div class="ct">Identificación <span class="rb rb-c">Costos</span></div>
      <div class="g4">
        <div class="fg"><label class="fl">Referencia</label><input type="text" name="referencia" value="{{v.referencia or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Ref. madre</label><input type="text" name="ref_madre" value="{{v.ref_madre or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Nombre</label><input type="text" name="nombre" value="{{v.nombre or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Unidades</label><input type="number" name="unidades" value="{{v.unidades or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">Precios de venta <span class="rb rb-m">Mercadeo</span></div>
      <div class="g4">
        <div class="fg"><label class="fl">Precio con IVA (COP)</label><input type="number" name="precio_cop_iva" value="{{v.precio_cop_iva or ''}}" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Precio sin IVA</label><div class="ro">{% if v.precio_cop_iva %}${{ '{:,.0f}'.format(v.precio_cop_iva/1.19)|replace(',','.') }}{% else %}—{% endif %}</div></div>
        <div class="fg"><label class="fl">Precio USD</label><input type="number" name="precio_usd" value="{{v.precio_usd or ''}}" step="0.5" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Precio prom. neto</label><div class="ro">{{fmtv(metricas.precio_prom_neto) if metricas else '—'}}</div></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">Costos estimados <span class="rb rb-c">Costos</span></div>
      <div class="g3">
        <div class="fg"><label class="fl">Costo estimado producto</label><input type="number" name="costo_estimado" value="{{v.costo_estimado or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Costo de la línea</label><input type="number" name="costo_linea" value="{{v.costo_linea or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Margen objetivo (%)</label><input type="number" name="margen_objetivo" value="{{v.margen_objetivo or 40}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
      </div>
    </div>
    {% if rol in ('mercadeo','costos','admin') and not v.fase1_aprobada %}
    <div class="ar" style="border:none;padding:0;margin-bottom:1rem"><button type="submit" class="bp">Guardar cambios</button></div>
    {% endif %}
  </form>
  {% endif %}

  {% if metricas %}
  <div class="mets">
    <div class="met"><div class="ml">Sin IVA</div><div class="mv">{% if v.precio_cop_iva %}${{ '{:,.0f}'.format(v.precio_cop_iva/1.19)|replace(',','.') }}{% else %}—{% endif %}</div></div>
    <div class="met"><div class="ml">Precio prom. neto</div><div class="mv">{{fmtv(metricas.precio_prom_neto)}}</div></div>
    <div class="met {{'mok' if metricas.viable else 'mbad'}}">
      <div class="ml">Margen bruto estimado</div>
      <div class="mv">{{pctt(metricas.margen_bruto_pct)}}</div>
      <div class="mbar"><div class="mfill" style="width:{{[metricas.margen_bruto_pct,100]|min}}%"></div></div>
    </div>
    <div class="met {{'mok' if metricas.viable else 'mbad'}}">
      <div class="ml">vs. objetivo ({{v.margen_objetivo or 40}}%)</div>
      <div class="mv">{{'✓ Viable' if metricas.viable else '✗ No viable'}}</div>
    </div>
  </div>
  <div class="card">
    <div class="ct">Análisis por canal</div>
    <table class="tbl">
      <thead><tr><th>Canal</th><th>Descuento</th><th>Precio neto canal</th><th>Participación</th><th>Margen canal</th></tr></thead>
      <tbody>
        {% for c in metricas.canales %}
        <tr>
          <td>{{c.nombre}}</td><td>{{c.descuento_pct|int}}%</td><td>${{ '{:,.0f}'.format(c.precio_neto)|replace(',','.') }}</td>
          <td>{{c.participacion|int}}%</td>
          <td style="font-weight:600;color:{{'#8e0038' if c.margen_pct>=(v.margen_objetivo or 40) else '#c62828'}}">{{pctt(c.margen_pct)}}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if rol in ('finanzas','admin') and not v.fase1_aprobada and not v.cerrada and metricas %}
  <div class="card">
    <div class="ct">Aprobación Finanzas <span class="rb rb-f">Finanzas</span></div>
    {% if metricas.viable %}<div class="aok" style="margin-bottom:1rem">Margen ({{pctt(metricas.margen_bruto_pct)}}) cumple el objetivo. Se puede aprobar.</div>
    {% else %}<div class="awk" style="margin-bottom:1rem">Margen ({{pctt(metricas.margen_bruto_pct)}}) por debajo del objetivo ({{v.margen_objetivo or 40}}%). Revisar antes de aprobar.</div>{% endif %}
    <form method="POST" action="/viabilidad/{{vid}}/aprobar/1">
      <div class="ar" style="border:none;padding:0"><button type="submit" class="bp">Aprobar Fase 1 →</button></div>
    </form>
  </div>
  {% endif %}
  {% if v.fase1_aprobada %}<div class="aok">✓ Fase 1 aprobada.</div>{% endif %}
  </div>

  <!-- FASE 2 -->
  {% if v.fase1_aprobada %}
  <div id="f2" style="border-top:1px solid var(--border);margin:1.5rem 0;padding-top:1.5rem">
    <div style="font-size:16px;font-weight:600;color:var(--myd-dark);margin-bottom:1rem">Fase 2 — Corrido de materiales</div>
    {% if not v.cerrada %}
    <form method="POST" action="/viabilidad/{{vid}}/guardar">
      <input type="hidden" name="fase" value="2">
      <div class="card">
        <div class="ct">Costos reales de materiales <span class="rb rb-c">Costos</span></div>
        <div class="g3">
          <div class="fg"><label class="fl">Costo real materiales (COP)</label><input type="number" name="costo_real" value="{{v.costo_real or ''}}" {{'disabled' if rol not in ('costos','admin') or v.fase2_aprobada}}></div>
          <div class="fg"><label class="fl">Costo estimado apertura</label><div class="ro">{{fmtv(v.costo_estimado)}}</div></div>
          <div class="fg"><label class="fl">Variación vs. estimado</label>
            <div class="ro" style="font-weight:600;color:{{'#c62828' if variacion and variacion>0 else '#8e0038'}}">
              {% if variacion is not none %}{{'+'if variacion>0 else ''}}{{variacion}}%{% else %}—{% endif %}
            </div>
          </div>
        </div>
        {% if variacion is not none %}
          {% if variacion>0 %}<div class="awk" style="margin-top:.875rem">Costo real supera el estimado (+{{variacion}}%). Finanzas debe revisar el margen.</div>
          {% else %}<div class="aok" style="margin-top:.875rem">Costos dentro del estimado ({{variacion}}%).</div>{% endif %}
        {% endif %}
      </div>
      {% if rol in ('costos','admin') and not v.fase2_aprobada %}
      <div class="ar" style="border:none;padding:0;margin-bottom:.875rem"><button type="submit" class="bs">Guardar materiales</button></div>
      {% endif %}
    </form>
    {% endif %}
    {% if rol in ('costos','admin') and not v.fase2_aprobada and v.costo_real and not v.cerrada %}
    <form method="POST" action="/viabilidad/{{vid}}/aprobar/2">
      <div class="ar" style="border:none;padding:0;margin-bottom:.875rem"><button type="submit" class="bp">Enviar a Finanzas →</button></div>
    </form>
    {% endif %}
    {% if v.fase2_aprobada %}<div class="aok">✓ Corrido completado — asignación final habilitada.</div>{% endif %}
  </div>
  {% endif %}

  <!-- FASE 3 -->
  {% if v.fase2_aprobada %}
  <div id="f3" style="border-top:1px solid var(--border);margin:1.5rem 0;padding-top:1.5rem">
    <div style="font-size:16px;font-weight:600;color:var(--myd-dark);margin-bottom:1rem">Fase 3 — Asignación de precio definitivo</div>
    {% if not v.cerrada %}
    <form method="POST" action="/viabilidad/{{vid}}/guardar">
      <input type="hidden" name="fase" value="3">
      <div class="card">
        <div class="ct">Precio definitivo <span class="rb rb-f">Finanzas</span></div>
        <div class="g3">
          <div class="fg"><label class="fl">Precio final con IVA (COP)</label><input type="number" name="precio_final_cop" value="{{v.precio_final_cop or ''}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
          <div class="fg"><label class="fl">Precio final USD</label><input type="number" name="precio_final_usd" value="{{v.precio_final_usd or ''}}" step="0.5" {{'disabled' if rol not in ('finanzas','admin')}}></div>
          <div class="fg"><label class="fl">Precio prom. neto final</label><div class="ro">{{fmtv(metricas_final.precio_prom_neto) if metricas_final else '—'}}</div></div>
        </div>
        <div class="fg" style="margin-top:.875rem"><label class="fl">Notas de Finanzas</label>
          <textarea name="notas_finanzas" rows="3" {{'disabled' if rol not in ('finanzas','admin')}}>{{v.notas_finanzas or ''}}</textarea>
        </div>
      </div>
      {% if rol in ('finanzas','admin') %}
      <div class="ar" style="border:none;padding:0;margin-bottom:.875rem"><button type="submit" class="bs">Guardar precio</button></div>
      {% endif %}
    </form>
    {% endif %}

    {% if metricas_final %}
    <div class="mets">
      <div class="met"><div class="ml">Sin IVA final</div><div class="mv">{% if v.precio_final_cop %}${{ '{:,.0f}'.format(v.precio_final_cop/1.19)|replace(',','.') }}{% else %}—{% endif %}</div></div>
      <div class="met"><div class="ml">Precio prom. neto</div><div class="mv">{{fmtv(metricas_final.precio_prom_neto)}}</div></div>
      <div class="met {{'mok' if metricas_final.viable else 'mbad'}}">
        <div class="ml">Margen bruto final</div><div class="mv">{{pctt(metricas_final.margen_bruto_pct)}}</div>
        <div class="mbar"><div class="mfill" style="width:{{[metricas_final.margen_bruto_pct,100]|min}}%"></div></div>
      </div>
      <div class="met {{'mok' if metricas_final.viable else 'mbad'}}">
        <div class="ml">vs. objetivo {{v.margen_objetivo or 40}}%</div>
        <div class="mv">{{'✓ Viable' if metricas_final.viable else '✗ Ajustar'}}</div>
      </div>
    </div>
    {% endif %}

    {% if rol in ('finanzas','admin') and not v.cerrada %}
    <div class="card">
      <div class="ct">Notificación de precio definitivo</div>
      {% for d in v.destinatarios %}
      <div class="erow">
        <span>{{d.email}}</span>
        <form method="POST" action="/viabilidad/{{vid}}/dest/rm/{{d.id}}" style="display:inline">
          <button type="submit" class="bx">Quitar</button>
        </form>
      </div>
      {% endfor %}
      <form method="POST" action="/viabilidad/{{vid}}/dest/add" style="display:flex;gap:8px;margin:1rem 0">
        <input type="email" name="email" placeholder="Agregar correo..." style="flex:1">
        <button type="submit" class="bs">+ Agregar</button>
      </form>
      {% if v.precio_final_cop %}
      <div style="font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Vista previa del correo</div>
      <div class="nref">
        <strong>Para:</strong> {{v.destinatarios|map(attribute='email')|join(', ')}}<br>
        <strong>Asunto:</strong> Precio definitivo — {{v.referencia}}{% if v.nombre %} | {{v.nombre}}{% endif %}<br><br>
        <strong>REFERENCIA:</strong> {{v.referencia}} &nbsp;|&nbsp; <strong>REF. MADRE:</strong> {{v.ref_madre or '—'}}<br>
        <strong>PRODUCTO:</strong> {{v.nombre or '—'}} &nbsp;|&nbsp; <strong>UNIDADES:</strong> {{v.unidades or '—'}}<br><br>
        <strong>PRECIO LISTA COP (c/IVA):</strong> {{fmtv(v.precio_final_cop)}}<br>
        <strong>PRECIO USD:</strong> {% if v.precio_final_usd %}USD {{v.precio_final_usd}}{% else %}—{% endif %}<br>
        {% if metricas_final %}<strong>MARGEN BRUTO FINAL:</strong> {{pctt(metricas_final.margen_bruto_pct)}}<br>{% endif %}
        <strong>COSTO CIERRE:</strong> {{fmtv(v.costo_real or v.costo_estimado)}}<br>
        {% if v.notas_finanzas %}<br><strong>NOTAS:</strong> {{v.notas_finanzas}}<br>{% endif %}<br>
        Equipo M&amp;D — Viabilidad de Precios
      </div>
      <form method="POST" action="/viabilidad/{{vid}}/cerrar">
        <div class="ar" style="border:none;padding:0;margin-top:.875rem">
          <button type="submit" class="bp">Enviar y cerrar viabilidad</button>
        </div>
      </form>
      {% else %}
      <div class="awk">Ingresa el precio final COP antes de cerrar.</div>
      {% endif %}
    </div>
    {% endif %}

    {% if v.cerrada %}
    <div class="aok" style="font-size:15px">✓ Viabilidad cerrada. Precio definitivo: <strong>{{fmtv(v.precio_final_cop)}}</strong>{% if v.precio_final_usd %} / USD {{v.precio_final_usd}}{% endif %}</div>
    {% endif %}
  </div>
  {% endif %}

  <!-- Historial -->
  {% if v.historial %}
  <div class="card" style="margin-top:1.5rem">
    <div class="ct">Historial de cambios</div>
    {% for h in v.historial %}
    <div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #f5f0f2;font-size:12px">
      <div style="width:8px;height:8px;border-radius:50%;background:var(--myd);flex-shrink:0;margin-top:4px"></div>
      <span style="color:#7a5a6a;flex:1"><strong style="color:var(--text)">{{h.usuario}}</strong> — {{h.accion}}</span>
      <span style="color:#b0a0b0">{{h.hora}}</span>
    </div>
    {% endfor %}
  </div>
  {% endif %}

</div>
{% endblock %}""")


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  M&D — Viabilidad de Precios  (modo local)")
    print("="*55)
    print("  URL:      http://localhost:5000")
    print("  Usuarios: mercadeo / costos / finanzas / admin")
    print("  Clave:    myd123  (admin → admin123)")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
