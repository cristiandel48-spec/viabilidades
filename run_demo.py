"""
M&D — Viabilidad de Precios
Versión LOCAL sin Supabase — datos en memoria
Correr con: python run_demo.py
Abrir en:   http://localhost:5000
"""

from flask import Flask, render_template_string, request, redirect, session, flash
from app.calculos import variacion_costo, fmt_cop
from datetime import datetime

app = Flask(__name__)
app.secret_key = "myd-demo-local-2025"

# ─── Datos en memoria ───────────────────────
VIABILIDADES = {}
_id_counter = [1]

LINEAS = [
    "Línea Invisible",
    "Fajas",
    "Control Flexy®",
    "Reloj de Arena®",
    "Lovely",
    "Materna",
    "Deportiva",
    "Para Hombres",
    "Complementaria",
]

USUARIOS = {
    "mercadeo": {"password": "myd123",    "rol": "mercadeo", "nombre": "Equipo Mercadeo"},
    "costos":   {"password": "myd123",    "rol": "costos",   "nombre": "Equipo Costos"},
    "finanzas": {"password": "myd123",    "rol": "finanzas", "nombre": "Equipo Finanzas"},
    "admin":    {"password": "admin123",  "rol": "admin",    "nombre": "Administrador"},
}

IVA = 0.19
CANALES_DCTO = [0.29, 0.20, 0.02, 0.01]
CANALES_NOM  = ["Aliados", "Int + Vinculados", "Tiendas", "E-Commerce"]

# ─── Helpers ────────────────────────────────
def usuario_actual():   return session.get("usuario")
def rol_actual():
    u = usuario_actual()
    return USUARIOS[u]["rol"] if u else None

def nuevo_id():
    vid = str(_id_counter[0]); _id_counter[0] += 1; return vid

def _float(v):
    try:    return float(str(v).replace(",", ".").strip())
    except: return None

def _int(v):
    try:    return int(str(v).strip())
    except: return None

def ahora(): return datetime.now().strftime("%Y-%m-%d %H:%M")

def calcular(precio_cop_iva, costo, margen_obj, dist_raw, tasa_usd=None):
    if not precio_cop_iva or not costo: return None
    d_total = sum(dist_raw) or 100
    d = [x / d_total for x in dist_raw]
    sin_iva = precio_cop_iva / (1 + IVA)
    neto    = sum(sin_iva * (1 - CANALES_DCTO[i]) * d[i] for i in range(4))
    mb      = (neto - costo) / neto if neto else 0
    sem     = "verde" if mb * 100 >= 50 else ("amarillo" if mb * 100 >= 43 else "rojo")
    canales = []
    for i in range(4):
        pn   = sin_iva * (1 - CANALES_DCTO[i])
        mb_c = (pn - costo) / pn if pn else 0
        canales.append({
            "nombre":        CANALES_NOM[i],
            "descuento_pct": CANALES_DCTO[i] * 100,
            "precio_neto":   round(pn, 2),
            "margen_pct":    round(mb_c * 100, 2),
            "participacion": round(d[i] * 100, 1),
        })
    neto_usd = round(neto / tasa_usd, 2) if tasa_usd and tasa_usd > 0 else None
    costo_obj = round(neto * (1 - margen_obj / 100), 2)
    return {
        "precio_sin_iva":   round(sin_iva, 2),
        "precio_prom_neto": round(neto, 2),
        "margen_bruto_pct": round(mb * 100, 2),
        "utilidad_bruta":   round(neto - costo, 2),
        "viable":           mb * 100 >= margen_obj,
        "semaforo":         sem,
        "canales":          canales,
        "neto_usd":         neto_usd,
        "costo_objetivo":   costo_obj,
        "brecha_costo":     round(costo_obj - costo, 2),
    }


# ═══════════════════════════════════════════════
#  CSS BASE
# ═══════════════════════════════════════════════
CSS = """
<style>
:root{--myd:#c2185b;--myd-d:#8e0038;--myd-l:#fce4ec;--bd:#ede0e8;--bg:#f8f4f6;--tx:#1a1118;--tx2:#7a5a6a}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}
.topbar{background:var(--myd);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(194,24,91,.3)}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none}
.brand img{height:32px;object-fit:contain}
.bsep{width:1px;height:22px;background:rgba(255,255,255,.35)}
.blbl{font-size:13px;font-weight:500;color:rgba(255,255,255,.92)}
.tnav{display:flex;align-items:center;gap:6px}
.tnav a{color:rgba(255,255,255,.82);text-decoration:none;font-size:13px;padding:5px 12px;border-radius:6px}
.tnav a:hover{background:rgba(255,255,255,.18)}
.upill{display:flex;align-items:center;gap:7px;background:rgba(255,255,255,.15);border-radius:100px;padding:4px 12px 4px 8px}
.udot{width:24px;height:24px;border-radius:50%;background:#fff;color:var(--myd);font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center}
.uname{font-size:12px;color:#fff;font-weight:500}
.wrap{max-width:1100px;margin:0 auto;padding:1.5rem}
.banner{background:#fff3e0;border-bottom:1px solid #ffcc80;padding:7px 1.5rem;font-size:12px;color:#e65100;text-align:center}
.flash{padding:10px 16px;border-radius:8px;font-size:13px;font-weight:500;margin-bottom:1rem}
.flash.ok{background:var(--myd-l);color:var(--myd-d);border:1px solid #f48fb1}
.flash.error{background:#ffebee;color:#c62828;border:1px solid #ef9a9a}
.card{background:#fff;border:1px solid var(--bd);border-radius:12px;padding:1.25rem;margin-bottom:1rem}
.ct{font-size:14px;font-weight:600;margin-bottom:.875rem;display:flex;align-items:center;gap:8px}
.rb{font-size:11px;padding:2px 8px;border-radius:100px;font-weight:500}
.rb-m{background:var(--myd-l);color:var(--myd-d)}
.rb-c{background:#e3f2fd;color:#0d47a1}
.rb-f{background:#fff3e0;color:#e65100}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.g5{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
@media(max-width:700px){.g5,.g4,.g3{grid-template-columns:1fr 1fr}.g2{grid-template-columns:1fr}}
.fg{display:flex;flex-direction:column;gap:5px}
.fl{font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.05em}
input,select,textarea{width:100%;padding:8px 10px;font-size:13px;border:1px solid #ddd0d8;border-radius:6px;background:#fff;color:var(--tx);font-family:inherit;outline:none;transition:border-color .15s}
input:focus,select:focus,textarea:focus{border-color:var(--myd);box-shadow:0 0 0 3px rgba(194,24,91,.1)}
input:disabled,textarea:disabled,select:disabled{background:var(--bg);color:#9e9099;cursor:not-allowed}
.ro{font-size:13px;padding:8px 10px;background:var(--bg);border-radius:6px;color:var(--tx);border:1px solid var(--bd);min-height:36px;display:flex;align-items:center}
.bp{padding:9px 22px;background:var(--myd);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-block;transition:background .15s}
.bp:hover{background:var(--myd-d)}
.bp:disabled{opacity:.4;cursor:not-allowed}
.bs{padding:9px 22px;background:#fff;color:var(--tx);border:1px solid #ddd0d8;border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-block}
.bs:hover{background:var(--bg)}
.bsm{padding:5px 12px;font-size:12px}
.bx{padding:5px 12px;font-size:12px;border-radius:6px;background:#ffebee;color:#c62828;border:1px solid #ef9a9a;cursor:pointer;font-family:inherit}
.bx:hover{background:#c62828;color:#fff}
.ar{display:flex;gap:8px;justify-content:flex-end;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--bd)}
/* Semáforos */
.sem{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:4px 12px;border-radius:100px}
.sv{background:#e8f5e9;color:#1b5e20;border:1px solid #a5d6a7}
.sa{background:#fff8e1;color:#e65100;border:1px solid #ffe082}
.sr{background:#ffebee;color:#b71c1c;border:1px solid #ef9a9a}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.dv{background:#2e7d32}.da{background:#f57f17}.dr{background:#c62828}
/* Métricas */
.mets{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:1rem}
@media(max-width:700px){.mets{grid-template-columns:1fr 1fr}}
.met{background:var(--bg);border-radius:8px;padding:.875rem}
.ml{font-size:12px;color:var(--tx2);margin-bottom:4px}
.mv{font-size:20px;font-weight:600;color:var(--tx)}
.mbar{height:6px;border-radius:3px;background:var(--bd);margin-top:6px;overflow:hidden}
.fv{height:100%;border-radius:3px;background:#2e7d32}
.fa{height:100%;border-radius:3px;background:#f57f17}
.fr{height:100%;border-radius:3px;background:#c62828}
/* Alertas */
.aok{background:#e8f5e9;border:1px solid #a5d6a7;color:#1b5e20;border-radius:8px;padding:.75rem 1rem;font-size:13px;margin-bottom:.875rem}
.awk{background:#fff3e0;border:1px solid #ffcc80;color:#e65100;border-radius:8px;padding:.75rem 1rem;font-size:13px;margin-bottom:.875rem}
.abad{background:#ffebee;border:1px solid #ef9a9a;color:#c62828;border-radius:8px;padding:.75rem 1rem;font-size:13px;margin-bottom:.875rem}
/* Tabla */
.tbl{width:100%;font-size:13px;border-collapse:collapse}
.tbl th{text-align:left;font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.04em;padding:8px 10px;border-bottom:1px solid var(--bd)}
.tbl td{padding:8px 10px;border-bottom:1px solid #f5f0f2}
.tbl tbody tr:hover td{background:var(--myd-l)}
/* Status */
.stt{display:inline-block;font-size:11px;padding:2px 8px;border-radius:100px;font-weight:600}
.s0{background:#e3f2fd;color:#0d47a1}.s1{background:#fff3e0;color:#e65100}
.s2{background:#f3e5f5;color:#6a1b9a}.sc{background:#e8f5e9;color:#2e7d32}
/* Phase bar */
.pbar{display:flex;align-items:center;background:#fff;border-bottom:1px solid var(--bd);padding:.75rem 1.5rem;gap:4px;overflow-x:auto}
.pi{display:flex;align-items:center;gap:8px;padding:7px 14px;border-radius:8px;text-decoration:none;white-space:nowrap}
.pi:hover{background:var(--myd-l)}
.pn{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;background:#f0e0e8;color:var(--myd-d)}
.pl2{font-size:13px;color:var(--tx2)}
.pi.pa .pn{background:var(--myd);color:#fff}
.pi.pa .pl2{color:var(--tx);font-weight:500}
.pi.pd .pn{background:#e8f5e9;color:#1b5e20}
.pi.pd .pl2{color:#1b5e20}
.pi.plk{opacity:.4;pointer-events:none}
.psep{color:#c9a0b4;font-size:16px;user-select:none}
/* Líneas grid */
.lgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-bottom:1.25rem}
.lbtn{padding:.875rem 1rem;background:#fff;border:2px solid var(--bd);border-radius:12px;cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;color:var(--tx);text-align:center;transition:all .2s;line-height:1.4}
.lbtn:hover{border-color:var(--myd);color:var(--myd);background:var(--myd-l)}
.lbtn.sel{border-color:var(--myd);background:var(--myd);color:#fff}
.lic{font-size:22px;display:block;margin-bottom:5px}
/* Simulador */
.simbox{background:#f0f7ff;border:1px solid #90caf9;border-radius:12px;padding:1.25rem;margin-bottom:1rem}
/* Distribución */
.distrow{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.dtotal{font-size:12px;margin-top:5px;font-weight:600;color:#1b5e20}
/* Notif preview */
.nref{background:var(--bg);border:1px solid var(--bd);border-radius:8px;padding:1rem;font-size:12px;color:#5a4a54;line-height:1.8;font-family:'Courier New',monospace}
.nref strong{color:var(--tx);font-family:inherit}
.erow{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f5f0f2}
.erow span{flex:1;font-size:13px}
</style>
"""

NAV = """
<div class="topbar">
  <a class="brand" href="/dashboard">
    <img src="https://fajasmyd.com/cdn/shop/files/LOGO_M_D-03.png?v=1757106759&width=220"
         alt="M&D" onerror="this.style.display='none'">
    <div class="bsep"></div>
    <span class="blbl">Viabilidad de Precios</span>
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
<div class="banner"><strong>Modo local</strong> — datos en memoria, se borran al reiniciar.</div>
"""

def flashes():
    msgs = []
    with app.test_request_context():
        pass
    return ""

def render(tpl, **ctx):
    full = "<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>M&D Viabilidad</title>" + CSS + "</head><body>" + NAV + """
{% with msgs = get_flashed_messages(with_categories=True) %}
{% if msgs %}<div style="max-width:1100px;margin:.75rem auto 0;padding:0 1.5rem">
{% for cat,msg in msgs %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}
</div>{% endif %}{% endwith %}
""" + tpl + "</body></html>"
    return render_template_string(full, **ctx)


# ═══════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if usuario_actual(): return redirect("/dashboard")
    error = None
    if request.method == "POST":
        u, p = request.form.get("usuario",""), request.form.get("password","")
        if u in USUARIOS and USUARIOS[u]["password"] == p:
            session["usuario"] = u; return redirect("/dashboard")
        error = "Usuario o contraseña incorrectos"
    tpl = """
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--myd)">
  <div style="background:#fff;border-radius:16px;padding:2.5rem 2rem;width:100%;max-width:380px">
    <div style="text-align:center;margin-bottom:1.5rem">
      <img src="https://fajasmyd.com/cdn/shop/files/LOGO_M_D-03.png?v=1757106759&width=220" style="height:44px" alt="M&D" onerror="this.style.display='none'">
    </div>
    <h2 style="text-align:center;margin-bottom:.25rem">Viabilidad de Precios</h2>
    <p style="font-size:13px;color:var(--tx2);text-align:center;margin-bottom:1.5rem">Ingresa con tu usuario</p>
    {% if error %}<div class="flash error">{{error}}</div>{% endif %}
    <form method="POST">
      <div class="fg" style="margin-bottom:.875rem"><label class="fl">Usuario</label>
        <select name="usuario"><option value="">Selecciona...</option>
          <option value="mercadeo">Mercadeo</option><option value="costos">Costos</option>
          <option value="finanzas">Finanzas</option><option value="admin">Admin</option>
        </select>
      </div>
      <div class="fg" style="margin-bottom:1.25rem"><label class="fl">Contraseña</label>
        <input type="password" name="password" placeholder="Contraseña">
      </div>
      <button type="submit" class="bp" style="width:100%">Ingresar</button>
    </form>
    <p style="margin-top:1rem;font-size:11px;color:#b0a0b0;text-align:center">mercadeo / costos / finanzas → <strong>myd123</strong> &nbsp;|&nbsp; admin → <strong>admin123</strong></p>
  </div>
</div>"""
    return render_template_string("<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>M&D Login</title>" + CSS + "</head><body>" + tpl + "</body></html>", error=error)


@app.route("/logout")
def logout():
    session.clear(); return redirect("/")


# ═══════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════
@app.route("/dashboard")
def dashboard():
    if not usuario_actual(): return redirect("/")
    u   = usuario_actual()
    rol = USUARIOS[u]["rol"]
    linea_sel = request.args.get("linea","")
    todos  = list(VIABILIDADES.values())
    viabs  = [v for v in todos if v.get("linea")==linea_sel] if linea_sel else todos
    tpl = """
<div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:1.5rem">
    <div><h1 style="font-size:22px;font-weight:600">Dashboard</h1>
    <p style="font-size:14px;color:var(--tx2)">Bienvenido, {{nombre}} &nbsp;·&nbsp; Rol: <strong>{{rol}}</strong></p></div>
    <a href="/nueva" class="bp">+ Nueva viabilidad</a>
  </div>
  <div class="mets">
    <div class="met"><div class="ml">Total</div><div class="mv">{{total}}</div></div>
    <div class="met"><div class="ml">En proceso</div><div class="mv" style="color:#0d47a1">{{en_proceso}}</div></div>
    <div class="met"><div class="ml">Cerradas</div><div class="mv" style="color:#1b5e20">{{cerradas}}</div></div>
    <div class="met"><div class="ml">Fase 1 aprobadas</div><div class="mv" style="color:#6a1b9a">{{viables}}</div></div>
  </div>
  <!-- Filtro líneas -->
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1rem;align-items:center">
    <span style="font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.05em">Línea:</span>
    <a href="/dashboard" class="{{'bp' if not linea_sel else 'bs'}} bsm">Todas</a>
    {% for l in lineas %}
    <a href="/dashboard?linea={{l|urlencode}}" class="{{'bp' if linea_sel==l else 'bs'}} bsm">{{l}}</a>
    {% endfor %}
  </div>
  <div class="card">
    <div class="ct">Viabilidades de precio</div>
    {% if viabilidades %}
    <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Línea</th><th>Referencia</th><th>Nombre</th><th>Precio COP</th><th>Margen</th><th>Semáforo</th><th>Estado</th><th>Fecha</th><th></th></tr></thead>
      <tbody>
      {% for v in viabilidades %}
      <tr>
        <td><span class="stt s0">{{v.linea or '—'}}</span></td>
        <td><strong>{{v.referencia or '—'}}</strong></td>
        <td>{{v.nombre or '—'}}</td>
        <td>{% if v.precio_cop_iva %}${{ '{:,.0f}'.format(v.precio_cop_iva)|replace(',','.') }}{% else %}—{% endif %}</td>
        <td>
          {% if v.semaforo=='verde' %}<span class="sem sv"><span class="dot dv"></span>{{v.margen_pct}}%</span>
          {% elif v.semaforo=='amarillo' %}<span class="sem sa"><span class="dot da"></span>{{v.margen_pct}}%</span>
          {% elif v.semaforo=='rojo' %}<span class="sem sr"><span class="dot dr"></span>{{v.margen_pct}}%</span>
          {% else %}—{% endif %}
        </td>
        <td>
          {% if v.semaforo=='verde' %}🟢
          {% elif v.semaforo=='amarillo' %}🟡
          {% elif v.semaforo=='rojo' %}🔴
          {% else %}—{% endif %}
        </td>
        <td>
          {% if v.cerrada %}<span class="stt sc">Cerrada</span>
          {% elif v.fase==3 %}<span class="stt s2">Fase 3</span>
          {% elif v.fase==2 %}<span class="stt s1">Fase 2</span>
          {% else %}<span class="stt s0">Fase 1</span>{% endif %}
        </td>
        <td style="font-size:12px;color:#b0a0b0">{{v.creado_at[:10]}}</td>
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
</div>"""
    return render(tpl, viabilidades=viabs, rol=rol, nombre=USUARIOS[u]["nombre"],
        total=len(todos), en_proceso=sum(1 for v in todos if not v.get("cerrada")),
        cerradas=sum(1 for v in todos if v.get("cerrada")),
        viables=sum(1 for v in todos if v.get("fase1_aprobada")),
        lineas=LINEAS, linea_sel=linea_sel)


# ═══════════════════════════════════════════════
#  NUEVA
# ═══════════════════════════════════════════════
@app.route("/nueva", methods=["GET","POST"])
def nueva():
    if not usuario_actual(): return redirect("/")
    rol = rol_actual()
    if request.method == "POST":
        linea = request.form.get("linea","").strip()
        if not linea:
            flash("Debes seleccionar una línea","error"); return redirect("/nueva")
        dist = [_float(request.form.get("dist_aliados")) or 40.0,
                _float(request.form.get("dist_vinculados")) or 25.0,
                _float(request.form.get("dist_tiendas")) or 25.0,
                _float(request.form.get("dist_ecommerce")) or 10.0]
        cop     = _float(request.form.get("precio_cop_iva"))
        costo   = _float(request.form.get("costo_estimado"))
        margen  = _float(request.form.get("margen_objetivo")) or 40.0
        tasa    = _float(request.form.get("tasa_usd"))
        mets    = calcular(cop, costo, margen, dist, tasa) if cop and costo else None
        vid = nuevo_id()
        VIABILIDADES[vid] = {
            "id": vid, "linea": linea,
            "referencia":   request.form.get("referencia","").upper().strip(),
            "ref_homologa": request.form.get("ref_homologa","").strip(),
            "nombre":       request.form.get("nombre","").strip(),
            "unidades":     _int(request.form.get("unidades")),
            "precio_cop_iva": cop, "precio_usd": _float(request.form.get("precio_usd")),
            "tasa_usd": tasa, "costo_estimado": costo, "costo_linea": _float(request.form.get("costo_linea")),
            "margen_objetivo": margen, "dist": dist,
            "costo_real": None, "precio_final_cop": None, "precio_final_usd": None,
            "notas_finanzas": "", "fase": 1,
            "fase1_aprobada": False, "fase2_aprobada": False, "cerrada": False,
            "semaforo": mets["semaforo"] if mets else None,
            "margen_pct": round(mets["margen_bruto_pct"],1) if mets else None,
            "creado_por": usuario_actual(), "creado_at": ahora(),
            "destinatarios": [{"id":"1","email":"mercadeo@myd.com"},{"id":"2","email":"costos@myd.com"},{"id":"3","email":"finanzas@myd.com"}],
            "historial": [{"usuario": usuario_actual(), "accion": "creación", "hora": ahora()}],
        }
        flash("Viabilidad creada correctamente","ok")
        return redirect(f"/viabilidad/{vid}")

    linea_sel = request.args.get("linea","")
    tpl = """
<div class="wrap">
  <h1 style="font-size:22px;font-weight:600;margin-bottom:.25rem">Nueva viabilidad</h1>
  <p style="font-size:14px;color:var(--tx2);margin-bottom:1.5rem">Selecciona la línea y completa los datos.</p>
  <form method="POST" id="frmN">
  <!-- Paso 1: Línea -->
  <div class="card">
    <div class="ct">Paso 1 — Selecciona la línea &nbsp;<span class="rb rb-f">Finanzas</span></div>
    <div class="lgrid">
      {% for l in lineas %}
      <button type="button" class="lbtn {{'sel' if linea_sel==l}}" data-l="{{l}}" onclick="selL('{{l}}')">
        <span class="lic">{% if 'Invisible' in l %}👙{% elif 'Faja' in l %}🩱{% elif 'Flexy' in l %}💪{% elif 'Arena' in l %}⏳{% elif 'Lovely' in l %}💕{% elif 'Materna' in l %}🤰{% elif 'Deportiva' in l %}🏃{% elif 'Hombre' in l %}👔{% else %}📦{% endif %}</span>
        {{l}}
      </button>
      {% endfor %}
    </div>
    <input type="hidden" name="linea" id="lInput" value="{{linea_sel}}">
    <div id="lSel" style="font-size:13px;color:var(--myd-d);font-weight:500;{{'display:none' if not linea_sel}}">✓ Seleccionada: <span id="lNom">{{linea_sel}}</span></div>
  </div>

  <!-- Paso 2-4: Datos -->
  <div id="datos" style="{{'display:none' if not linea_sel else ''}}">
    <div class="card">
      <div class="ct">Paso 2 — Referencia &nbsp;<span class="rb rb-f">Finanzas crea la línea</span></div>
      <div class="g4">
        <div class="fg"><label class="fl">Referencia *</label><input type="text" name="referencia" required placeholder="Ej: B-06006" {{'disabled' if rol not in ('finanzas','admin')}}></div>
        <div class="fg"><label class="fl">Referencia homóloga</label><input type="text" name="ref_homologa" placeholder="Ej: B-00006" {{'disabled' if rol not in ('finanzas','admin')}}></div>
        <div class="fg"><label class="fl">Nombre producto</label><input type="text" name="nombre" placeholder="Ej: Faja corta" {{'disabled' if rol not in ('finanzas','admin')}}></div>
        <div class="fg"><label class="fl">Unidades</label><input type="number" name="unidades" min="0" placeholder="Ej: 450" {{'disabled' if rol not in ('mercadeo','finanzas','admin')}}></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">Paso 3 — Precios y canales &nbsp;<span class="rb rb-m">Mercadeo</span></div>
      <div class="g4" style="margin-bottom:1rem">
        <div class="fg"><label class="fl">Precio con IVA (COP)</label><input type="number" name="precio_cop_iva" min="0" placeholder="Ej: 179900" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Precio USD</label><input type="number" name="precio_usd" min="0" step="0.5" placeholder="Ej: 41" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Tasa de cambio COP/USD</label><input type="number" name="tasa_usd" min="0" placeholder="Ej: 4200" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Margen objetivo %</label><input type="number" name="margen_objetivo" value="40" min="0" max="100" {{'disabled' if rol not in ('finanzas','admin')}}></div>
      </div>
      <div style="font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Participación por canal (debe sumar 100%) &nbsp;<span class="rb rb-m">Mercadeo</span></div>
      <div class="distrow">
        <div class="fg"><label class="fl">Aliados %</label><input type="number" name="dist_aliados" value="40" min="0" max="100" oninput="chkD()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Int+Vinc %</label><input type="number" name="dist_vinculados" value="25" min="0" max="100" oninput="chkD()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Tiendas %</label><input type="number" name="dist_tiendas" value="25" min="0" max="100" oninput="chkD()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">E-Commerce %</label><input type="number" name="dist_ecommerce" value="10" min="0" max="100" oninput="chkD()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
      </div>
      <div class="dtotal" id="dT">Total: 100%</div>
    </div>
    <div class="card">
      <div class="ct">Paso 4 — Costos &nbsp;<span class="rb rb-c">Costos</span></div>
      <div class="g2">
        <div class="fg"><label class="fl">Costo inicial estimado (COP)</label><input type="number" name="costo_estimado" min="0" placeholder="Ej: 77497" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Costo final / cierre (COP)</label><input type="number" name="costo_linea" min="0" placeholder="Se completa al cierre" {{'disabled' if rol not in ('costos','admin')}}></div>
      </div>
    </div>
    <div class="ar" style="border:none;padding:0">
      <a href="/dashboard" class="bs">Cancelar</a>
      <button type="submit" class="bp" id="btnC" {{'disabled' if not linea_sel}}>Crear viabilidad →</button>
    </div>
  </div>
  </form>
</div>
<script>
function selL(n){
  document.querySelectorAll('.lbtn').forEach(b=>b.classList.remove('sel'));
  document.querySelector('[data-l="'+n+'"]').classList.add('sel');
  document.getElementById('lInput').value=n;
  document.getElementById('lNom').textContent=n;
  document.getElementById('lSel').style.display='block';
  document.getElementById('datos').style.display='block';
  document.getElementById('btnC').disabled=false;
}
function chkD(){
  const f=['dist_aliados','dist_vinculados','dist_tiendas','dist_ecommerce'];
  const t=f.reduce((s,n)=>s+(parseFloat(document.querySelector('[name='+n+']').value)||0),0);
  const el=document.getElementById('dT');
  el.textContent='Total: '+t.toFixed(0)+'%';
  el.style.color=Math.abs(t-100)<0.1?'#1b5e20':'#c62828';
}
</script>"""
    return render(tpl, rol=rol, lineas=LINEAS, linea_sel=linea_sel)


# ═══════════════════════════════════════════════
#  DETALLE
# ═══════════════════════════════════════════════
@app.route("/viabilidad/<vid>")
def detalle(vid):
    if not usuario_actual(): return redirect("/")
    v = VIABILIDADES.get(vid)
    if not v: flash("No encontrada","error"); return redirect("/dashboard")
    rol  = rol_actual()
    dist = v.get("dist",[40,25,25,10])
    mets = calcular(v.get("precio_cop_iva"), v.get("costo_estimado"), v.get("margen_objetivo",40), dist, v.get("tasa_usd")) if v.get("precio_cop_iva") and v.get("costo_estimado") else None
    if mets: v["semaforo"] = mets["semaforo"]; v["margen_pct"] = round(mets["margen_bruto_pct"],1)
    cbase = v.get("costo_real") or v.get("costo_estimado")
    mfin  = calcular(v.get("precio_final_cop"), cbase, v.get("margen_objetivo",40), dist, v.get("tasa_usd")) if v.get("precio_final_cop") and cbase else None
    variacion = round(variacion_costo(v["costo_real"], v["costo_estimado"])*100,1) if v.get("costo_real") and v.get("costo_estimado") else None

    tpl = """
{% macro fv(x) %}{% if x %}${{ '{:,.0f}'.format(x)|replace(',','.') }}{% else %}—{% endif %}{% endmacro %}
{% macro pc(x) %}{% if x is not none %}{{ '%.1f'|format(x) }}%{% else %}—{% endif %}{% endmacro %}
{% macro semhml(s,p) %}
  {% if s=='verde' %}<span class="sem sv"><span class="dot dv"></span>{{pc(p)}}</span>
  {% elif s=='amarillo' %}<span class="sem sa"><span class="dot da"></span>{{pc(p)}}</span>
  {% elif s=='rojo' %}<span class="sem sr"><span class="dot dr"></span>{{pc(p)}}</span>
  {% endif %}
{% endmacro %}

<div class="pbar">
  <a class="pi {{'pa' if v.fase==1 else 'pd'}}" href="#f1"><div class="pn">{{'✓' if v.fase>1 else '1'}}</div><span class="pl2">Viabilidad inicial</span></a>
  <span class="psep">›</span>
  <a class="pi {{'pa' if v.fase==2 else ('pd' if v.fase>2 else 'plk')}}" href="#f2"><div class="pn">{{'✓' if v.fase>2 else '2'}}</div><span class="pl2">Corrido materiales</span></a>
  <span class="psep">›</span>
  <a class="pi {{'pa' if v.fase==3 else 'plk'}}" href="#f3"><div class="pn">3</div><span class="pl2">Asignación final</span></a>
</div>

<div class="wrap">
  <!-- Header -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.25rem">
    <div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
        <span class="stt s0">{{v.linea}}</span>
        {{semhml(v.semaforo, v.margen_pct)}}
      </div>
      <h1 style="font-size:22px;font-weight:600">{{v.referencia or '—'}}{% if v.nombre %} — {{v.nombre}}{% endif %}</h1>
      <p style="font-size:13px;color:var(--tx2)">Ref. homóloga: {{v.ref_homologa or '—'}} &nbsp;·&nbsp; Unidades: {{v.unidades or '—'}} &nbsp;·&nbsp; {{v.creado_at}}</p>
    </div>
    <a href="/dashboard" class="bs bsm">← Volver</a>
  </div>

  <!-- ══ FASE 1 ══ -->
  <div id="f1">
  {% if not v.cerrada %}
  <form method="POST" action="/viabilidad/{{vid}}/guardar">
    <input type="hidden" name="fase" value="1">
    <div class="card">
      <div class="ct">Identificación <span class="rb rb-f">Finanzas</span></div>
      <div class="g4">
        <div class="fg"><label class="fl">Referencia</label><input type="text" name="referencia" value="{{v.referencia or ''}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
        <div class="fg"><label class="fl">Referencia homóloga</label><input type="text" name="ref_homologa" value="{{v.ref_homologa or ''}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
        <div class="fg"><label class="fl">Nombre</label><input type="text" name="nombre" value="{{v.nombre or ''}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
        <div class="fg"><label class="fl">Unidades</label><input type="number" name="unidades" value="{{v.unidades or ''}}" {{'disabled' if rol not in ('mercadeo','finanzas','admin')}}></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">Precios y canales <span class="rb rb-m">Mercadeo</span></div>
      <div class="g5" style="margin-bottom:1rem">
        <div class="fg"><label class="fl">Precio con IVA (COP)</label><input type="number" name="precio_cop_iva" value="{{v.precio_cop_iva or ''}}" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Sin IVA</label><div class="ro">{% if v.precio_cop_iva %}${{ '{:,.0f}'.format(v.precio_cop_iva/1.19)|replace(',','.') }}{% else %}—{% endif %}</div></div>
        <div class="fg"><label class="fl">Precio USD</label><input type="number" name="precio_usd" value="{{v.precio_usd or ''}}" step="0.5" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Tasa COP/USD</label><input type="number" name="tasa_usd" value="{{v.tasa_usd or ''}}" placeholder="Ej: 4200" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Margen objetivo %</label><input type="number" name="margen_objetivo" value="{{v.margen_objetivo or 40}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
      </div>
      <div style="font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Participación por canal — editable por Mercadeo</div>
      <div class="distrow">
        <div class="fg"><label class="fl">Aliados %</label><input type="number" name="dist_aliados" value="{{v.dist[0]|round(1)}}" min="0" max="100" oninput="chkD2()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Int+Vinc %</label><input type="number" name="dist_vinculados" value="{{v.dist[1]|round(1)}}" min="0" max="100" oninput="chkD2()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">Tiendas %</label><input type="number" name="dist_tiendas" value="{{v.dist[2]|round(1)}}" min="0" max="100" oninput="chkD2()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
        <div class="fg"><label class="fl">E-Commerce %</label><input type="number" name="dist_ecommerce" value="{{v.dist[3]|round(1)}}" min="0" max="100" oninput="chkD2()" {{'disabled' if rol not in ('mercadeo','admin')}}></div>
      </div>
      <div class="dtotal" id="dT2">Total: {{(v.dist[0]+v.dist[1]+v.dist[2]+v.dist[3])|round(0)|int}}%</div>
    </div>
    <div class="card">
      <div class="ct">Costos <span class="rb rb-c">Costos</span></div>
      <div class="g2">
        <div class="fg"><label class="fl">Costo inicial estimado (COP)</label><input type="number" name="costo_estimado" value="{{v.costo_estimado or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
        <div class="fg"><label class="fl">Costo final / cierre (COP)</label><input type="number" name="costo_linea" value="{{v.costo_linea or ''}}" {{'disabled' if rol not in ('costos','admin')}}></div>
      </div>
    </div>
    {% if not v.fase1_aprobada %}
    <div class="ar" style="border:none;padding:0;margin-bottom:1rem"><button type="submit" class="bp">Guardar cambios</button></div>
    {% endif %}
  </form>
  {% endif %}

  {% if mets %}
  <!-- Métricas -->
  <div class="mets">
    <div class="met"><div class="ml">Sin IVA</div><div class="mv">{% if v.precio_cop_iva %}${{ '{:,.0f}'.format(v.precio_cop_iva/1.19)|replace(',','.') }}{% else %}—{% endif %}</div></div>
    <div class="met"><div class="ml">Precio prom. neto</div><div class="mv">{{fv(mets.precio_prom_neto)}}</div></div>
    <div class="met" style="border:2px solid {{'#a5d6a7' if mets.semaforo=='verde' else '#ffe082' if mets.semaforo=='amarillo' else '#ef9a9a'}}">
      <div class="ml">Margen bruto estimado</div>
      <div class="mv" style="color:{{'#1b5e20' if mets.semaforo=='verde' else '#e65100' if mets.semaforo=='amarillo' else '#c62828'}}">{{pc(mets.margen_bruto_pct)}}</div>
      <div class="mbar"><div class="{{'fv' if mets.semaforo=='verde' else 'fa' if mets.semaforo=='amarillo' else 'fr'}}" style="width:{{[mets.margen_bruto_pct,100]|min}}%"></div></div>
      <div style="margin-top:6px">{{semhml(mets.semaforo, mets.margen_bruto_pct)}}</div>
    </div>
    <div class="met"><div class="ml">Utilidad bruta unit.</div><div class="mv">{{fv(mets.utilidad_bruta)}}</div></div>
  </div>

  <!-- Leyenda semáforo -->
  <div class="card" style="padding:.875rem 1.25rem">
    <div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap">
      <span style="font-size:12px;font-weight:600;color:var(--tx2)">Rangos de margen:</span>
      <span class="sem sv"><span class="dot dv"></span>Verde ≥ 50%</span>
      <span class="sem sa"><span class="dot da"></span>Amarillo 43–49%</span>
      <span class="sem sr"><span class="dot dr"></span>Rojo &lt; 43%</span>
    </div>
  </div>

  {% if mets.neto_usd %}
  <!-- Análisis USD -->
  <div class="card" style="background:#f0f7ff;border-color:#90caf9">
    <div class="ct" style="color:#0d47a1">Análisis en dólares (USD)</div>
    <div class="g3">
      <div class="fg"><label class="fl">Precio prom. neto USD</label><div class="ro"><strong>USD {{ '%.2f'|format(mets.neto_usd) }}</strong></div></div>
      <div class="fg"><label class="fl">Costo en USD</label><div class="ro">{% if v.costo_estimado and v.tasa_usd %}USD {{ '%.2f'|format(v.costo_estimado/v.tasa_usd) }}{% else %}—{% endif %}</div></div>
      <div class="fg"><label class="fl">Margen en USD</label><div class="ro" style="font-weight:600;color:{{'#1b5e20' if mets.semaforo=='verde' else '#e65100' if mets.semaforo=='amarillo' else '#c62828'}}">{{pc(mets.margen_bruto_pct)}}</div></div>
    </div>
  </div>
  {% endif %}

  <!-- Canales -->
  <div class="card">
    <div class="ct">Análisis por canal</div>
    <table class="tbl">
      <thead><tr><th>Canal</th><th>Descuento</th><th>Participación</th><th>Precio neto</th><th>Margen</th></tr></thead>
      <tbody>
      {% for c in mets.canales %}
      <tr>
        <td>{{c.nombre}}</td><td>{{c.descuento_pct|int}}%</td>
        <td><strong>{{c.participacion}}%</strong></td>
        <td>${{ '{:,.0f}'.format(c.precio_neto)|replace(',','.') }}</td>
        <td>{{semhml(('verde' if c.margen_pct>=50 else ('amarillo' if c.margen_pct>=43 else 'rojo')), c.margen_pct)}}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Simulador costo objetivo -->
  <div class="simbox">
    <div style="font-size:14px;font-weight:600;color:#0d47a1;margin-bottom:.875rem">🎯 Simulador — costo requerido para llegar al margen objetivo</div>
    <div class="g4">
      <div class="fg"><label class="fl">Precio con IVA (COP)</label><input type="number" id="sP" value="{{v.precio_cop_iva or ''}}" oninput="sim()"></div>
      <div class="fg"><label class="fl">Margen objetivo %</label><input type="number" id="sM" value="{{v.margen_objetivo or 40}}" oninput="sim()"></div>
      <div class="fg"><label class="fl">Costo máximo a llegar</label><div class="ro" id="sCobj" style="font-weight:700;color:#0d47a1">—</div></div>
      <div class="fg"><label class="fl">Brecha vs. costo actual</label><div class="ro" id="sBr">—</div></div>
    </div>
    <div style="font-size:12px;color:#1565c0;margin-top:8px" id="sMsg"></div>
  </div>
  {% endif %}

  {% if rol in ('finanzas','admin') and not v.fase1_aprobada and not v.cerrada and mets %}
  <div class="card">
    <div class="ct">Aprobación Finanzas <span class="rb rb-f">Finanzas</span></div>
    {% if mets.semaforo=='verde' %}<div class="aok" style="margin-bottom:1rem">🟢 Margen ({{pc(mets.margen_bruto_pct)}}) excelente. Aprobado para continuar.</div>
    {% elif mets.semaforo=='amarillo' %}<div class="awk" style="margin-bottom:1rem">🟡 Margen ({{pc(mets.margen_bruto_pct)}}) aceptable. Revisar antes de aprobar.</div>
    {% else %}<div class="abad" style="margin-bottom:1rem">🔴 Margen ({{pc(mets.margen_bruto_pct)}}) por debajo del mínimo. Ajustar costos o precio.</div>{% endif %}
    <form method="POST" action="/viabilidad/{{vid}}/aprobar/1">
      <div class="ar" style="border:none;padding:0"><button type="submit" class="bp">Aprobar Fase 1 →</button></div>
    </form>
  </div>
  {% endif %}
  {% if v.fase1_aprobada %}<div class="aok">✓ Fase 1 aprobada.</div>{% endif %}
  </div>

  <!-- ══ FASE 2 ══ -->
  {% if v.fase1_aprobada %}
  <div id="f2" style="border-top:1px solid var(--bd);margin:1.5rem 0;padding-top:1.5rem">
    <h2 style="font-size:16px;font-weight:600;color:var(--myd-d);margin-bottom:1rem">Fase 2 — Corrido de materiales</h2>
    {% if not v.cerrada %}
    <form method="POST" action="/viabilidad/{{vid}}/guardar">
      <input type="hidden" name="fase" value="2">
      <div class="card">
        <div class="ct">Costos reales <span class="rb rb-c">Costos</span></div>
        <div class="g3">
          <div class="fg"><label class="fl">Costo real materiales (COP)</label><input type="number" name="costo_real" value="{{v.costo_real or ''}}" {{'disabled' if rol not in ('costos','admin') or v.fase2_aprobada}}></div>
          <div class="fg"><label class="fl">Costo estimado apertura</label><div class="ro">{{fv(v.costo_estimado)}}</div></div>
          <div class="fg"><label class="fl">Variación</label>
            <div class="ro" style="font-weight:600;color:{{'#c62828' if variacion and variacion>0 else '#1b5e20'}}">
              {% if variacion is not none %}{{'+'if variacion>0 else ''}}{{variacion}}%{% else %}—{% endif %}
            </div>
          </div>
        </div>
        {% if variacion is not none %}
        {% if variacion>0 %}<div class="awk" style="margin-top:.875rem">Costo real +{{variacion}}% vs. estimado. Finanzas debe revisar.</div>
        {% else %}<div class="aok" style="margin-top:.875rem">Costos dentro del estimado ({{variacion}}%). ✓</div>{% endif %}
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
    {% if v.fase2_aprobada %}<div class="aok">✓ Corrido completado.</div>{% endif %}
  </div>
  {% endif %}

  <!-- ══ FASE 3 ══ -->
  {% if v.fase2_aprobada %}
  <div id="f3" style="border-top:1px solid var(--bd);margin:1.5rem 0;padding-top:1.5rem">
    <h2 style="font-size:16px;font-weight:600;color:var(--myd-d);margin-bottom:1rem">Fase 3 — Asignación de precio definitivo</h2>
    {% if not v.cerrada %}
    <form method="POST" action="/viabilidad/{{vid}}/guardar">
      <input type="hidden" name="fase" value="3">
      <div class="card">
        <div class="ct">Precio definitivo <span class="rb rb-f">Finanzas</span></div>
        <div class="g4">
          <div class="fg"><label class="fl">Precio final con IVA (COP)</label><input type="number" name="precio_final_cop" value="{{v.precio_final_cop or ''}}" {{'disabled' if rol not in ('finanzas','admin')}}></div>
          <div class="fg"><label class="fl">Precio final USD</label><input type="number" name="precio_final_usd" value="{{v.precio_final_usd or ''}}" step="0.5" {{'disabled' if rol not in ('finanzas','admin')}}></div>
          <div class="fg"><label class="fl">Precio prom. neto final</label><div class="ro">{{fv(mfin.precio_prom_neto) if mfin else '—'}}</div></div>
          <div class="fg"><label class="fl">Semáforo final</label><div class="ro">{% if mfin %}{{semhml(mfin.semaforo, mfin.margen_bruto_pct)}}{% else %}—{% endif %}</div></div>
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

    {% if mfin %}
    <div class="mets">
      <div class="met"><div class="ml">Sin IVA final</div><div class="mv">{% if v.precio_final_cop %}${{ '{:,.0f}'.format(v.precio_final_cop/1.19)|replace(',','.') }}{% else %}—{% endif %}</div></div>
      <div class="met"><div class="ml">Precio prom. neto</div><div class="mv">{{fv(mfin.precio_prom_neto)}}</div></div>
      <div class="met" style="border:2px solid {{'#a5d6a7' if mfin.semaforo=='verde' else '#ffe082' if mfin.semaforo=='amarillo' else '#ef9a9a'}}">
        <div class="ml">Margen bruto final</div>
        <div class="mv" style="color:{{'#1b5e20' if mfin.semaforo=='verde' else '#e65100' if mfin.semaforo=='amarillo' else '#c62828'}}">{{pc(mfin.margen_bruto_pct)}}</div>
        <div class="mbar"><div class="{{'fv' if mfin.semaforo=='verde' else 'fa' if mfin.semaforo=='amarillo' else 'fr'}}" style="width:{{[mfin.margen_bruto_pct,100]|min}}%"></div></div>
      </div>
      <div class="met"><div class="ml">Utilidad bruta unit.</div><div class="mv">{{fv(mfin.utilidad_bruta)}}</div></div>
    </div>
    {% endif %}

    {% if rol in ('finanzas','admin') and not v.cerrada %}
    <div class="card">
      <div class="ct">Notificación de precio definitivo</div>
      {% for d in v.destinatarios %}
      <div class="erow"><span>{{d.email}}</span>
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
      <p style="font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Vista previa del correo</p>
      <div class="nref">
<strong>Para:</strong> {{v.destinatarios|map(attribute='email')|join(', ')}}<br>
<strong>Asunto:</strong> Precio definitivo — {{v.referencia}}{% if v.nombre %} | {{v.nombre}}{% endif %}<br><br>
<strong>LÍNEA:</strong> {{v.linea}} &nbsp;|&nbsp; <strong>REFERENCIA:</strong> {{v.referencia}} &nbsp;|&nbsp; <strong>REF. HOMÓLOGA:</strong> {{v.ref_homologa or '—'}}<br>
<strong>PRODUCTO:</strong> {{v.nombre or '—'}} &nbsp;|&nbsp; <strong>UNIDADES:</strong> {{v.unidades or '—'}}<br><br>
<strong>PRECIO LISTA COP (c/IVA):</strong> {{fv(v.precio_final_cop)}}<br>
<strong>PRECIO USD:</strong> {% if v.precio_final_usd %}USD {{v.precio_final_usd}}{% else %}—{% endif %}<br>
{% if mfin %}<strong>MARGEN BRUTO FINAL:</strong> {{pc(mfin.margen_bruto_pct)}} {% if mfin.semaforo=='verde' %}🟢{% elif mfin.semaforo=='amarillo' %}🟡{% else %}🔴{% endif %}<br>{% endif %}
<strong>COSTO CIERRE:</strong> {{fv(v.costo_real or v.costo_estimado)}}<br>
{% if v.notas_finanzas %}<br><strong>NOTAS:</strong> {{v.notas_finanzas}}<br>{% endif %}<br>
Equipo M&D — Viabilidad de Precios
      </div>
      <form method="POST" action="/viabilidad/{{vid}}/cerrar">
        <div class="ar" style="border:none;padding:0;margin-top:.875rem">
          <button type="submit" class="bp">Enviar y cerrar viabilidad</button>
        </div>
      </form>
      {% else %}<div class="awk">Ingresa el precio final COP antes de cerrar.</div>{% endif %}
    </div>
    {% endif %}

    {% if v.cerrada %}
    <div class="aok" style="font-size:15px">✓ Viabilidad cerrada. Precio: <strong>{{fv(v.precio_final_cop)}}</strong>{% if v.precio_final_usd %} / USD {{v.precio_final_usd}}{% endif %}</div>
    {% endif %}
  </div>
  {% endif %}

  <!-- Historial -->
  {% if v.historial %}
  <div class="card" style="margin-top:1.5rem">
    <div class="ct">Historial</div>
    {% for h in v.historial %}
    <div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #f5f0f2;font-size:12px">
      <div style="width:8px;height:8px;border-radius:50%;background:var(--myd);flex-shrink:0;margin-top:4px"></div>
      <span style="flex:1;color:var(--tx2)"><strong style="color:var(--tx)">{{h.usuario}}</strong> — {{h.accion}}</span>
      <span style="color:#b0a0b0">{{h.hora}}</span>
    </div>
    {% endfor %}
  </div>
  {% endif %}

</div>
<script>
function chkD2(){
  const f=['dist_aliados','dist_vinculados','dist_tiendas','dist_ecommerce'];
  const t=f.reduce((s,n)=>s+(parseFloat(document.querySelector('[name='+n+']').value)||0),0);
  const el=document.getElementById('dT2');
  if(el){el.textContent='Total: '+t.toFixed(0)+'%';el.style.color=Math.abs(t-100)<0.1?'#1b5e20':'#c62828';}
}
function sim(){
  const p=parseFloat(document.getElementById('sP').value)||0;
  const m=parseFloat(document.getElementById('sM').value)||0;
  const ca={{v.costo_estimado or 0}};
  if(!p){document.getElementById('sCobj').textContent='—';return;}
  const si=p/1.19;
  const d=[{{v.dist[0]/100}},{{v.dist[1]/100}},{{v.dist[2]/100}},{{v.dist[3]/100}}];
  const dc=[0.29,0.20,0.02,0.01];
  const neto=dc.reduce((a,dd,i)=>a+si*(1-dd)*d[i],0);
  const co=neto*(1-m/100);
  const br=co-ca;
  document.getElementById('sCobj').textContent='$'+Math.round(co).toLocaleString('es-CO');
  const bEl=document.getElementById('sBr');
  bEl.textContent=(br>=0?'+':'')+Math.round(br).toLocaleString('es-CO');
  bEl.style.color=br>=0?'#1b5e20':'#c62828';
  document.getElementById('sMsg').textContent=br<0
    ?'⚠ El costo actual supera el requerido en $'+Math.abs(Math.round(br)).toLocaleString('es-CO')+'. Reducir costos o subir precio.'
    :'✓ El costo está $'+Math.round(br).toLocaleString('es-CO')+' por debajo del requerido.';
}
window.onload=function(){sim();}
</script>"""
    return render(tpl, v=v, rol=rol, vid=vid, mets=mets, mfin=mfin, variacion=variacion)


# ─── Acciones ───────────────────────────────
@app.route("/viabilidad/<vid>/guardar", methods=["POST"])
def guardar(vid):
    if not usuario_actual(): return redirect("/")
    v = VIABILIDADES.get(vid); rol = rol_actual()
    if not v: return redirect("/dashboard")
    campos = {
        "mercadeo": ["precio_cop_iva","precio_usd","tasa_usd","unidades","dist_aliados","dist_vinculados","dist_tiendas","dist_ecommerce"],
        "costos":   ["costo_estimado","costo_linea","costo_real"],
        "finanzas": ["referencia","ref_homologa","nombre","margen_objetivo","precio_final_cop","precio_final_usd","notas_finanzas"],
        "admin":    ["referencia","ref_homologa","nombre","unidades","precio_cop_iva","precio_usd","tasa_usd","costo_estimado","costo_linea","margen_objetivo","costo_real","precio_final_cop","precio_final_usd","notas_finanzas","dist_aliados","dist_vinculados","dist_tiendas","dist_ecommerce"],
    }
    for c in campos.get(rol,[]):
        val = request.form.get(c)
        if val is not None and str(val).strip()!="":
            if c in ("referencia","ref_homologa","nombre","notas_finanzas"): v[c]=val.strip()
            elif c=="unidades": v[c]=_int(val)
            elif c in ("dist_aliados","dist_vinculados","dist_tiendas","dist_ecommerce"):
                i=["dist_aliados","dist_vinculados","dist_tiendas","dist_ecommerce"].index(c)
                v["dist"][i]=_float(val) or v["dist"][i]
            else: v[c]=_float(val)
    v["historial"].insert(0,{"usuario":usuario_actual(),"accion":f"editó fase {v['fase']}","hora":ahora()})
    flash("Cambios guardados","ok"); return redirect(f"/viabilidad/{vid}")

@app.route("/viabilidad/<vid>/aprobar/1", methods=["POST"])
def aprobar_f1(vid):
    if not usuario_actual(): return redirect("/")
    if rol_actual() not in ("finanzas","admin"): flash("Solo Finanzas puede aprobar","error"); return redirect(f"/viabilidad/{vid}")
    v=VIABILIDADES.get(vid)
    if v: v["fase1_aprobada"]=True; v["fase"]=2; v["historial"].insert(0,{"usuario":usuario_actual(),"accion":"aprobó Fase 1","hora":ahora()}); flash("Fase 1 aprobada.","ok")
    return redirect(f"/viabilidad/{vid}")

@app.route("/viabilidad/<vid>/aprobar/2", methods=["POST"])
def aprobar_f2(vid):
    if not usuario_actual(): return redirect("/")
    if rol_actual() not in ("costos","admin"): flash("Solo Costos puede enviar","error"); return redirect(f"/viabilidad/{vid}")
    v=VIABILIDADES.get(vid)
    if v: v["fase2_aprobada"]=True; v["fase"]=3; v["historial"].insert(0,{"usuario":usuario_actual(),"accion":"envió corrido","hora":ahora()}); flash("Enviado a Finanzas.","ok")
    return redirect(f"/viabilidad/{vid}")

@app.route("/viabilidad/<vid>/cerrar", methods=["POST"])
def cerrar(vid):
    if not usuario_actual(): return redirect("/")
    if rol_actual() not in ("finanzas","admin"): flash("Solo Finanzas puede cerrar","error"); return redirect(f"/viabilidad/{vid}")
    v=VIABILIDADES.get(vid)
    if not v: return redirect("/dashboard")
    if not v.get("precio_final_cop"): flash("Ingresa el precio final antes de cerrar","error"); return redirect(f"/viabilidad/{vid}")
    v["cerrada"]=True; v["historial"].insert(0,{"usuario":usuario_actual(),"accion":"cerró la viabilidad","hora":ahora()})
    flash(f"Viabilidad cerrada. Precio: {fmt_cop(v['precio_final_cop'])}","ok"); return redirect(f"/viabilidad/{vid}")

@app.route("/viabilidad/<vid>/dest/add", methods=["POST"])
def dest_add(vid):
    if not usuario_actual(): return redirect("/")
    v=VIABILIDADES.get(vid); email=request.form.get("email","").strip().lower()
    if v and "@" in email:
        nid=str(len(v.get("destinatarios",[]))+10); v.setdefault("destinatarios",[]).append({"id":nid,"email":email}); flash(f"{email} agregado","ok")
    return redirect(f"/viabilidad/{vid}")

@app.route("/viabilidad/<vid>/dest/rm/<did>", methods=["POST"])
def dest_rm(vid,did):
    if not usuario_actual(): return redirect("/")
    v=VIABILIDADES.get(vid)
    if v: v["destinatarios"]=[d for d in v.get("destinatarios",[]) if d["id"]!=did]
    return redirect(f"/viabilidad/{vid}")


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  M&D — Viabilidad de Precios  (modo local)")
    print("="*55)
    print("  URL:      http://localhost:5000")
    print("  Usuarios: mercadeo / costos / finanzas / admin")
    print("  Clave:    myd123  (admin → admin123)")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
