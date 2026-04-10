from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from .supabase_client import get_client
from datetime import datetime

bp = Blueprint("main", __name__)

IVA = 0.19
CANALES_DCTO = [0.29, 0.20, 0.02, 0.01]
CANALES_NOM  = ["Aliados", "Int + Vinculados", "Tiendas", "E-Commerce"]

LINEAS = [
    "Línea Invisible", "Fajas", "Control Flexy®", "Reloj de Arena®",
    "Lovely", "Materna", "Deportiva", "Para Hombres", "Complementaria",
]

USUARIOS_DEMO = {
    "mercadeo": {"password": "myd123",    "rol": "mercadeo", "nombre": "Equipo Mercadeo"},
    "costos":   {"password": "myd123",    "rol": "costos",   "nombre": "Equipo Costos"},
    "finanzas": {"password": "myd123",    "rol": "finanzas", "nombre": "Equipo Finanzas"},
    "admin":    {"password": "admin123",  "rol": "admin",    "nombre": "Administrador"},
}


# ─── Helpers ────────────────────────────────────────────────
def usuario_actual(): return session.get("usuario")
def rol_actual():
    u = usuario_actual()
    return USUARIOS_DEMO[u]["rol"] if u else None

def requiere_login(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not usuario_actual():
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated

def _float(v):
    try:    return float(str(v).replace(",", ".").strip())
    except: return None

def _int(v):
    try:    return int(str(v).strip())
    except: return None

def ahora(): return datetime.now().strftime("%Y-%m-%d %H:%M")

def fmt_cop(v):
    if v is None: return "—"
    return f"${round(v):,}".replace(",", ".")


# ─── Cálculos ───────────────────────────────────────────────
def calcular(precio_cop_iva, costo, margen_obj, dist, tasa_usd=None):
    if not precio_cop_iva or not costo: return None
    d_total = sum(dist) or 100
    d = [x / d_total for x in dist]
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
    neto_usd   = round(neto / tasa_usd, 2) if tasa_usd and tasa_usd > 0 else None
    costo_obj  = round(neto * (1 - margen_obj / 100), 2)
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

def dist_de_v(v):
    """Extrae la lista de distribución de una viabilidad."""
    return [
        v.get("dist_aliados", 40) or 40,
        v.get("dist_vinculados", 25) or 25,
        v.get("dist_tiendas", 25) or 25,
        v.get("dist_ecommerce", 10) or 10,
    ]


# ─── Historial ──────────────────────────────────────────────
def _historial(viabilidad_id, accion, datos=None):
    try:
        db = get_client()
        db.table("viabilidad_historial").insert({
            "viabilidad_id": viabilidad_id,
            "usuario":       session.get("usuario", "sistema"),
            "accion":        accion,
            "datos_json":    datos or {},
        }).execute()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  LOGIN / LOGOUT
# ═══════════════════════════════════════════════════════════
@bp.route("/", methods=["GET", "POST"])
@bp.route("/login", methods=["GET", "POST"])
def login():
    if usuario_actual():
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        u = request.form.get("usuario", "").strip().lower()
        p = request.form.get("password", "").strip()
        if u in USUARIOS_DEMO and USUARIOS_DEMO[u]["password"] == p:
            session["usuario"] = u
            return redirect(url_for("main.dashboard"))
        error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# ═══════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════
@bp.route("/dashboard")
@requiere_login
def dashboard():
    db        = get_client()
    rol       = rol_actual()
    linea_sel = request.args.get("linea", "")

    query = db.table("viabilidades").select("*").order("creado_at", desc=True)
    if linea_sel:
        query = query.eq("linea", linea_sel)
    resultado    = query.execute()
    viabilidades = resultado.data or []

    todos = db.table("viabilidades").select("id,cerrada,fase1_aprobada").execute().data or []

    return render_template(
        "dashboard.html",
        viabilidades=viabilidades,
        rol=rol,
        nombre=USUARIOS_DEMO[usuario_actual()]["nombre"],
        total=len(todos),
        en_proceso=sum(1 for v in todos if not v.get("cerrada")),
        cerradas=sum(1 for v in todos if v.get("cerrada")),
        viables=sum(1 for v in todos if v.get("fase1_aprobada")),
        lineas=LINEAS,
        linea_sel=linea_sel,
    )


# ═══════════════════════════════════════════════════════════
#  NUEVA VIABILIDAD
# ═══════════════════════════════════════════════════════════
@bp.route("/nueva", methods=["GET", "POST"])
@requiere_login
def nueva():
    rol = rol_actual()

    if request.method == "POST":
        linea = request.form.get("linea", "").strip()
        if not linea:
            flash("Debes seleccionar una línea", "error")
            return redirect(url_for("main.nueva"))

        dist = [
            _float(request.form.get("dist_aliados"))    or 40.0,
            _float(request.form.get("dist_vinculados")) or 25.0,
            _float(request.form.get("dist_tiendas"))    or 25.0,
            _float(request.form.get("dist_ecommerce"))  or 10.0,
        ]
        cop    = _float(request.form.get("precio_cop_iva"))
        costo  = _float(request.form.get("costo_estimado"))
        margen = _float(request.form.get("margen_objetivo")) or 40.0
        tasa   = _float(request.form.get("tasa_usd"))
        mets   = calcular(cop, costo, margen, dist, tasa) if cop and costo else None

        datos = {
            "linea":          linea,
            "referencia":     request.form.get("referencia", "").upper().strip(),
            "ref_homologa":   request.form.get("ref_homologa", "").strip(),
            "nombre":         request.form.get("nombre", "").strip(),
            "unidades":       _int(request.form.get("unidades")),
            "precio_cop_iva": cop,
            "precio_usd":     _float(request.form.get("precio_usd")),
            "tasa_usd":       tasa,
            "dist_aliados":   dist[0],
            "dist_vinculados": dist[1],
            "dist_tiendas":   dist[2],
            "dist_ecommerce": dist[3],
            "costo_estimado": costo,
            "costo_linea":    _float(request.form.get("costo_linea")),
            "margen_objetivo": margen,
            "fase":           1,
            "creado_por":     usuario_actual(),
            "semaforo":       mets["semaforo"] if mets else None,
            "margen_pct":     round(mets["margen_bruto_pct"], 1) if mets else None,
        }

        if not datos["referencia"]:
            flash("La referencia es obligatoria", "error")
            return render_template("viabilidad_form.html", rol=rol, lineas=LINEAS, linea_sel=linea)

        db  = get_client()
        res = db.table("viabilidades").insert(datos).execute()
        vid = res.data[0]["id"]

        # Historial
        _historial(vid, "creación", datos)

        # Copiar destinatarios globales
        dest = db.table("destinatarios_globales").select("*").eq("activo", True).execute()
        for d in (dest.data or []):
            db.table("notif_destinatarios").insert({
                "viabilidad_id": vid,
                "email":         d["email"]
            }).execute()

        flash("Viabilidad creada correctamente", "ok")
        return redirect(url_for("main.detalle", vid=vid))

    linea_sel = request.args.get("linea", "")
    return render_template("viabilidad_form.html", rol=rol, lineas=LINEAS, linea_sel=linea_sel)


# ═══════════════════════════════════════════════════════════
#  DETALLE
# ═══════════════════════════════════════════════════════════
@bp.route("/viabilidad/<vid>")
@requiere_login
def detalle(vid):
    db  = get_client()
    rol = rol_actual()

    res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
    v   = res.data

    dist = dist_de_v(v)

    metricas = None
    if v.get("precio_cop_iva") and v.get("costo_estimado"):
        metricas = calcular(v["precio_cop_iva"], v["costo_estimado"], v.get("margen_objetivo", 40), dist, v.get("tasa_usd"))
        # Actualizar semáforo en DB si cambió
        if metricas and (v.get("semaforo") != metricas["semaforo"] or v.get("margen_pct") != round(metricas["margen_bruto_pct"], 1)):
            db.table("viabilidades").update({
                "semaforo":  metricas["semaforo"],
                "margen_pct": round(metricas["margen_bruto_pct"], 1),
            }).eq("id", vid).execute()

    metricas_final = None
    costo_base = v.get("costo_real") or v.get("costo_estimado")
    if v.get("precio_final_cop") and costo_base:
        metricas_final = calcular(v["precio_final_cop"], costo_base, v.get("margen_objetivo", 40), dist, v.get("tasa_usd"))

    variacion = None
    if v.get("costo_real") and v.get("costo_estimado") and v["costo_estimado"] != 0:
        variacion = round((v["costo_real"] - v["costo_estimado"]) / v["costo_estimado"] * 100, 1)

    dest_res = db.table("notif_destinatarios").select("*").eq("viabilidad_id", vid).execute()
    destinatarios = dest_res.data or []

    hist_res = db.table("viabilidad_historial").select("*").eq("viabilidad_id", vid).order("creado_at", desc=True).limit(20).execute()
    historial = hist_res.data or []

    return render_template(
        "detalle.html",
        v=v, rol=rol, vid=vid,
        dist=dist,
        metricas=metricas,
        metricas_final=metricas_final,
        variacion=variacion,
        destinatarios=destinatarios,
        historial=historial,
        fmt_cop=fmt_cop,
        lineas=LINEAS,
    )


# ═══════════════════════════════════════════════════════════
#  GUARDAR CAMBIOS POR ROL Y FASE
# ═══════════════════════════════════════════════════════════
@bp.route("/viabilidad/<vid>/guardar", methods=["POST"])
@requiere_login
def guardar(vid):
    db  = get_client()
    rol = rol_actual()

    campos_rol = {
        # Mercadeo: precios + unidades + distribución canales
        "mercadeo": [
            "precio_cop_iva", "precio_usd", "tasa_usd", "unidades",
            "dist_aliados", "dist_vinculados", "dist_tiendas", "dist_ecommerce",
        ],
        # Costos: solo costos
        "costos": [
            "costo_estimado", "costo_linea", "costo_real",
        ],
        # Finanzas: crea referencia + margen + precio final
        "finanzas": [
            "referencia", "ref_homologa", "nombre",
            "margen_objetivo",
            "precio_final_cop", "precio_final_usd", "notas_finanzas",
        ],
        # Admin: todo
        "admin": [
            "linea", "referencia", "ref_homologa", "nombre", "unidades",
            "precio_cop_iva", "precio_usd", "tasa_usd",
            "dist_aliados", "dist_vinculados", "dist_tiendas", "dist_ecommerce",
            "costo_estimado", "costo_linea", "margen_objetivo", "costo_real",
            "precio_final_cop", "precio_final_usd", "notas_finanzas",
        ],
    }

    texto_campos  = {"referencia", "ref_homologa", "nombre", "notas_finanzas", "linea"}
    entero_campos = {"unidades"}

    datos = {}
    for campo in campos_rol.get(rol, []):
        val = request.form.get(campo)
        if val is not None and str(val).strip() != "":
            if campo in texto_campos:
                datos[campo] = val.strip()
            elif campo in entero_campos:
                datos[campo] = _int(val)
            else:
                datos[campo] = _float(val)

    if datos:
        # Recalcular semáforo si cambiaron precios o costos
        res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
        v   = res.data
        v.update(datos)
        dist = dist_de_v(v)
        mets = calcular(v.get("precio_cop_iva"), v.get("costo_estimado"), v.get("margen_objetivo", 40), dist, v.get("tasa_usd"))
        if mets:
            datos["semaforo"]   = mets["semaforo"]
            datos["margen_pct"] = round(mets["margen_bruto_pct"], 1)

        db.table("viabilidades").update(datos).eq("id", vid).execute()
        _historial(vid, f"edición (rol: {rol})", {k: str(v) for k, v in datos.items() if k not in ("semaforo",)})
        flash("Cambios guardados", "ok")

    return redirect(url_for("main.detalle", vid=vid))


# ═══════════════════════════════════════════════════════════
#  APROBACIONES
# ═══════════════════════════════════════════════════════════
@bp.route("/viabilidad/<vid>/aprobar/1", methods=["POST"])
@requiere_login
def aprobar_fase1(vid):
    if rol_actual() not in ("finanzas", "admin"):
        flash("Solo Finanzas puede aprobar la Fase 1", "error")
        return redirect(url_for("main.detalle", vid=vid))
    db = get_client()
    db.table("viabilidades").update({"fase1_aprobada": True, "fase": 2}).eq("id", vid).execute()
    _historial(vid, "aprobó Fase 1")
    flash("Fase 1 aprobada. Costos puede ingresar el corrido de materiales.", "ok")
    return redirect(url_for("main.detalle", vid=vid))


@bp.route("/viabilidad/<vid>/aprobar/2", methods=["POST"])
@requiere_login
def aprobar_fase2(vid):
    if rol_actual() not in ("costos", "admin"):
        flash("Solo Costos puede enviar el corrido a Finanzas", "error")
        return redirect(url_for("main.detalle", vid=vid))
    db = get_client()
    db.table("viabilidades").update({"fase2_aprobada": True, "fase": 3}).eq("id", vid).execute()
    _historial(vid, "envió corrido de materiales a Finanzas")
    flash("Corrido enviado a Finanzas para asignación final.", "ok")
    return redirect(url_for("main.detalle", vid=vid))


# ═══════════════════════════════════════════════════════════
#  CERRAR VIABILIDAD
# ═══════════════════════════════════════════════════════════
@bp.route("/viabilidad/<vid>/cerrar", methods=["POST"])
@requiere_login
def cerrar(vid):
    if rol_actual() not in ("finanzas", "admin"):
        flash("Solo Finanzas puede cerrar la viabilidad", "error")
        return redirect(url_for("main.detalle", vid=vid))
    db  = get_client()
    res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
    v   = res.data
    if not v.get("precio_final_cop"):
        flash("Debes ingresar el precio final antes de cerrar", "error")
        return redirect(url_for("main.detalle", vid=vid))
    db.table("viabilidades").update({"cerrada": True}).eq("id", vid).execute()
    _historial(vid, "cerró la viabilidad", {"precio_final_cop": str(v["precio_final_cop"])})
    flash(f"Viabilidad cerrada. Precio: {fmt_cop(v['precio_final_cop'])}", "ok")
    return redirect(url_for("main.detalle", vid=vid))


# ═══════════════════════════════════════════════════════════
#  DESTINATARIOS
# ═══════════════════════════════════════════════════════════
@bp.route("/viabilidad/<vid>/destinatario/agregar", methods=["POST"])
@requiere_login
def agregar_destinatario(vid):
    email = request.form.get("email", "").strip().lower()
    if "@" not in email:
        flash("Email inválido", "error")
        return redirect(url_for("main.detalle", vid=vid))
    db = get_client()
    db.table("notif_destinatarios").insert({"viabilidad_id": vid, "email": email}).execute()
    flash(f"{email} agregado", "ok")
    return redirect(url_for("main.detalle", vid=vid))


@bp.route("/viabilidad/<vid>/destinatario/<did>/quitar", methods=["POST"])
@requiere_login
def quitar_destinatario(vid, did):
    db = get_client()
    db.table("notif_destinatarios").delete().eq("id", did).execute()
    flash("Destinatario eliminado", "ok")
    return redirect(url_for("main.detalle", vid=vid))


# ═══════════════════════════════════════════════════════════
#  API JSON — métricas en tiempo real
# ═══════════════════════════════════════════════════════════
@bp.route("/api/viabilidad/<vid>/metricas")
@requiere_login
def api_metricas(vid):
    db  = get_client()
    res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
    v   = res.data
    dist = dist_de_v(v)
    if not v.get("precio_cop_iva") or not v.get("costo_estimado"):
        return jsonify({"error": "datos_insuficientes"}), 400
    mets = calcular(v["precio_cop_iva"], v["costo_estimado"], v.get("margen_objetivo", 40), dist, v.get("tasa_usd"))
    return jsonify(mets)


# ═══════════════════════════════════════════════════════════
#  ADMIN — destinatarios globales
# ═══════════════════════════════════════════════════════════
@bp.route("/admin/destinatarios", methods=["GET", "POST"])
@requiere_login
def admin_destinatarios():
    if rol_actual() != "admin":
        flash("Acceso restringido", "error")
        return redirect(url_for("main.dashboard"))
    db = get_client()
    if request.method == "POST":
        email  = request.form.get("email", "").strip().lower()
        nombre = request.form.get("nombre", "").strip()
        rol_d  = request.form.get("rol", "").strip()
        if "@" in email:
            db.table("destinatarios_globales").upsert(
                {"email": email, "nombre": nombre, "rol": rol_d},
                on_conflict="email"
            ).execute()
            flash(f"{email} agregado/actualizado", "ok")
    res = db.table("destinatarios_globales").select("*").order("creado_at").execute()
    return render_template("admin_destinatarios.html", destinatarios=res.data or [])


@bp.route("/admin/destinatarios/<did>/toggle", methods=["POST"])
@requiere_login
def toggle_destinatario_global(did):
    if rol_actual() != "admin":
        return redirect(url_for("main.dashboard"))
    db  = get_client()
    res = db.table("destinatarios_globales").select("activo").eq("id", did).single().execute()
    db.table("destinatarios_globales").update({"activo": not res.data["activo"]}).eq("id", did).execute()
    return redirect(url_for("main.admin_destinatarios"))
