from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from .supabase_client import get_client
from .calculos import calcular_metricas, variacion_costo, precio_promedio_neto, margen_bruto, fmt_cop

bp = Blueprint("main", __name__)

ROLES_VALIDOS = {"mercadeo", "costos", "finanzas", "admin"}


# ─────────────────────────────────────────────
# LOGIN  (simulado con sesión — sin Supabase Auth)
# Para producción: integrar Supabase Auth aquí
# ─────────────────────────────────────────────
USUARIOS_DEMO = {
    "mercadeo": {"password": "myd123", "rol": "mercadeo", "nombre": "Equipo Mercadeo"},
    "costos":   {"password": "myd123", "rol": "costos",   "nombre": "Equipo Costos"},
    "finanzas": {"password": "myd123", "rol": "finanzas", "nombre": "Equipo Finanzas"},
    "admin":    {"password": "admin123", "rol": "admin",  "nombre": "Administrador"},
}


def usuario_actual():
    return session.get("usuario")


def rol_actual():
    u = usuario_actual()
    if u and u in USUARIOS_DEMO:
        return USUARIOS_DEMO[u]["rol"]
    return None


def requiere_login(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not usuario_actual():
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated


# ─── LOGIN / LOGOUT ───────────────────────────
@bp.route("/", methods=["GET", "POST"])
@bp.route("/login", methods=["GET", "POST"])
def login():
    if usuario_actual():
        return redirect(url_for("main.dashboard"))

    error = None
    if request.method == "POST":
        user = request.form.get("usuario", "").strip().lower()
        pwd  = request.form.get("password", "").strip()
        if user in USUARIOS_DEMO and USUARIOS_DEMO[user]["password"] == pwd:
            session["usuario"] = user
            return redirect(url_for("main.dashboard"))
        error = "Usuario o contraseña incorrectos"

    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# ─── DASHBOARD ────────────────────────────────
@bp.route("/dashboard")
@requiere_login
def dashboard():
    db  = get_client()
    rol = rol_actual()

    resultado = db.table("viabilidades").select("*").order("creado_at", desc=True).execute()
    viabilidades = resultado.data or []

    # Métricas de resumen
    total      = len(viabilidades)
    en_proceso = sum(1 for v in viabilidades if not v.get("cerrada"))
    cerradas   = sum(1 for v in viabilidades if v.get("cerrada"))
    viables    = sum(1 for v in viabilidades if v.get("fase1_aprobada"))

    return render_template(
        "dashboard.html",
        viabilidades=viabilidades,
        rol=rol,
        nombre=USUARIOS_DEMO[usuario_actual()]["nombre"],
        total=total,
        en_proceso=en_proceso,
        cerradas=cerradas,
        viables=viables,
    )


# ─── NUEVA VIABILIDAD ─────────────────────────
@bp.route("/nueva", methods=["GET", "POST"])
@requiere_login
def nueva():
    rol = rol_actual()
    if rol not in ("costos", "mercadeo", "admin"):
        flash("No tienes permiso para crear viabilidades", "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        db = get_client()
        datos = {
            "referencia":    request.form.get("referencia", "").upper().strip(),
            "ref_madre":     request.form.get("ref_madre", "").strip(),
            "nombre":        request.form.get("nombre", "").strip(),
            "unidades":      _int(request.form.get("unidades")),
            "precio_cop_iva": _float(request.form.get("precio_cop_iva")),
            "precio_usd":    _float(request.form.get("precio_usd")),
            "costo_estimado": _float(request.form.get("costo_estimado")),
            "costo_linea":   _float(request.form.get("costo_linea")),
            "margen_objetivo": _float(request.form.get("margen_objetivo")) or 40.0,
            "fase":          1,
            "creado_por":    usuario_actual(),
        }

        if not datos["referencia"]:
            flash("La referencia es obligatoria", "error")
            return render_template("viabilidad_form.html", rol=rol, v=datos, fase=1)

        result = db.table("viabilidades").insert(datos).execute()
        vid = result.data[0]["id"]

        # Registrar en historial
        _historial(vid, "creacion", datos)

        # Copiar destinatarios globales
        dest = db.table("destinatarios_globales").select("*").eq("activo", True).execute()
        for d in (dest.data or []):
            db.table("notif_destinatarios").insert({
                "viabilidad_id": vid,
                "email": d["email"]
            }).execute()

        flash("Viabilidad creada correctamente", "ok")
        return redirect(url_for("main.detalle", vid=vid))

    return render_template("viabilidad_form.html", rol=rol, v={}, fase=1)


# ─── DETALLE / EDICIÓN ────────────────────────
@bp.route("/viabilidad/<vid>", methods=["GET"])
@requiere_login
def detalle(vid):
    db  = get_client()
    rol = rol_actual()

    res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
    v   = res.data

    metricas = None
    if v.get("precio_cop_iva") and v.get("costo_estimado"):
        metricas = calcular_metricas(
            v["precio_cop_iva"],
            v["costo_estimado"],
            v.get("margen_objetivo", 40),
        )

    metricas_final = None
    costo_real = v.get("costo_real") or v.get("costo_estimado")
    if v.get("precio_final_cop") and costo_real:
        metricas_final = calcular_metricas(
            v["precio_final_cop"],
            costo_real,
            v.get("margen_objetivo", 40),
        )

    variacion = None
    if v.get("costo_real") and v.get("costo_estimado"):
        variacion = round(variacion_costo(v["costo_real"], v["costo_estimado"]) * 100, 1)

    dest_res = db.table("notif_destinatarios").select("*").eq("viabilidad_id", vid).execute()
    destinatarios = dest_res.data or []

    hist_res = db.table("viabilidad_historial").select("*").eq("viabilidad_id", vid).order("creado_at", desc=True).execute()
    historial = hist_res.data or []

    return render_template(
        "detalle.html",
        v=v, rol=rol, vid=vid,
        metricas=metricas,
        metricas_final=metricas_final,
        variacion=variacion,
        destinatarios=destinatarios,
        historial=historial,
        fmt_cop=fmt_cop,
    )


# ─── GUARDAR CAMBIOS POR FASE ─────────────────
@bp.route("/viabilidad/<vid>/guardar", methods=["POST"])
@requiere_login
def guardar(vid):
    db  = get_client()
    rol = rol_actual()
    fase = int(request.form.get("fase", 1))

    campos_por_rol = {
        "mercadeo": ["precio_cop_iva", "precio_usd"],
        "costos":   ["referencia", "ref_madre", "nombre", "unidades",
                     "costo_estimado", "costo_linea", "costo_real"],
        "finanzas": ["margen_objetivo", "precio_final_cop", "precio_final_usd", "notas_finanzas"],
        "admin":    ["referencia", "ref_madre", "nombre", "unidades",
                     "precio_cop_iva", "precio_usd", "costo_estimado", "costo_linea",
                     "margen_objetivo", "costo_real",
                     "precio_final_cop", "precio_final_usd", "notas_finanzas"],
    }

    campos_permitidos = campos_por_rol.get(rol, [])
    datos = {}
    for campo in campos_permitidos:
        val = request.form.get(campo)
        if val is not None and val != "":
            if campo in ("unidades",):
                datos[campo] = _int(val)
            elif campo in ("referencia", "ref_madre", "nombre", "notas_finanzas"):
                datos[campo] = val.strip()
            else:
                datos[campo] = _float(val)

    if datos:
        db.table("viabilidades").update(datos).eq("id", vid).execute()
        _historial(vid, f"edicion_fase{fase}", datos)
        flash("Cambios guardados", "ok")

    return redirect(url_for("main.detalle", vid=vid))


# ─── APROBAR FASES ────────────────────────────
@bp.route("/viabilidad/<vid>/aprobar/1", methods=["POST"])
@requiere_login
def aprobar_fase1(vid):
    rol = rol_actual()
    if rol not in ("finanzas", "admin"):
        flash("Solo Finanzas puede aprobar la Fase 1", "error")
        return redirect(url_for("main.detalle", vid=vid))

    db = get_client()
    db.table("viabilidades").update({"fase1_aprobada": True, "fase": 2}).eq("id", vid).execute()
    _historial(vid, "aprobacion_fase1", {})
    flash("Fase 1 aprobada. El área de Costos puede ingresar los materiales.", "ok")
    return redirect(url_for("main.detalle", vid=vid))


@bp.route("/viabilidad/<vid>/aprobar/2", methods=["POST"])
@requiere_login
def aprobar_fase2(vid):
    rol = rol_actual()
    if rol not in ("costos", "admin"):
        flash("Solo Costos puede enviar el corrido a Finanzas", "error")
        return redirect(url_for("main.detalle", vid=vid))

    db = get_client()
    db.table("viabilidades").update({"fase2_aprobada": True, "fase": 3}).eq("id", vid).execute()
    _historial(vid, "aprobacion_fase2", {})
    flash("Corrido de materiales enviado a Finanzas.", "ok")
    return redirect(url_for("main.detalle", vid=vid))


# ─── CERRAR VIABILIDAD (envío final) ──────────
@bp.route("/viabilidad/<vid>/cerrar", methods=["POST"])
@requiere_login
def cerrar(vid):
    rol = rol_actual()
    if rol not in ("finanzas", "admin"):
        flash("Solo Finanzas puede cerrar y enviar la viabilidad", "error")
        return redirect(url_for("main.detalle", vid=vid))

    db  = get_client()
    res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
    v   = res.data

    if not v.get("precio_final_cop"):
        flash("Debes ingresar el precio final antes de cerrar", "error")
        return redirect(url_for("main.detalle", vid=vid))

    db.table("viabilidades").update({"cerrada": True}).eq("id", vid).execute()
    _historial(vid, "cierre_viabilidad", {"precio_final_cop": v["precio_final_cop"]})

    flash(f"Viabilidad cerrada. Precio definitivo: {fmt_cop(v['precio_final_cop'])}", "ok")
    return redirect(url_for("main.detalle", vid=vid))


# ─── DESTINATARIOS ────────────────────────────
@bp.route("/viabilidad/<vid>/destinatario/agregar", methods=["POST"])
@requiere_login
def agregar_destinatario(vid):
    email = request.form.get("email", "").strip().lower()
    if "@" not in email:
        flash("Email inválido", "error")
        return redirect(url_for("main.detalle", vid=vid))
    db = get_client()
    db.table("notif_destinatarios").insert({"viabilidad_id": vid, "email": email}).execute()
    flash(f"Destinatario {email} agregado", "ok")
    return redirect(url_for("main.detalle", vid=vid))


@bp.route("/viabilidad/<vid>/destinatario/<did>/quitar", methods=["POST"])
@requiere_login
def quitar_destinatario(vid, did):
    db = get_client()
    db.table("notif_destinatarios").delete().eq("id", did).execute()
    flash("Destinatario eliminado", "ok")
    return redirect(url_for("main.detalle", vid=vid))


# ─── API JSON (para posible uso futuro / frontend) ──
@bp.route("/api/viabilidad/<vid>/metricas")
@requiere_login
def api_metricas(vid):
    db  = get_client()
    res = db.table("viabilidades").select("*").eq("id", vid).single().execute()
    v   = res.data
    if not v.get("precio_cop_iva") or not v.get("costo_estimado"):
        return jsonify({"error": "datos_insuficientes"}), 400
    metricas = calcular_metricas(v["precio_cop_iva"], v["costo_estimado"], v.get("margen_objetivo", 40))
    return jsonify(metricas)


# ─── ADMIN: destinatarios globales ────────────
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
        rol    = request.form.get("rol", "").strip()
        if "@" in email:
            db.table("destinatarios_globales").upsert(
                {"email": email, "nombre": nombre, "rol": rol},
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
    nuevo = not res.data["activo"]
    db.table("destinatarios_globales").update({"activo": nuevo}).eq("id", did).execute()
    return redirect(url_for("main.admin_destinatarios"))


# ─── Utilidades internas ──────────────────────
def _float(val):
    try:
        return float(str(val).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _int(val):
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return None


def _historial(viabilidad_id, accion, datos):
    try:
        db = get_client()
        db.table("viabilidad_historial").insert({
            "viabilidad_id": viabilidad_id,
            "usuario":       session.get("usuario", "sistema"),
            "accion":        accion,
            "datos_json":    datos,
        }).execute()
    except Exception:
        pass
