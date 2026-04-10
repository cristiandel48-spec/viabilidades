-- ============================================================
-- M&D Viabilidad de Precios — Supabase SQL ACTUALIZADO
-- Incluye todos los cambios de los 8 ajustes nuevos
-- Ejecutar en: Supabase > SQL Editor
-- ============================================================

-- ─── 1. Tabla principal de viabilidades ───────────────────
CREATE TABLE IF NOT EXISTS viabilidades (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Línea (nuevo: botones de línea)
    linea               TEXT,

    -- Identificación — ahora Finanzas crea esto
    referencia          TEXT NOT NULL,
    ref_homologa        TEXT,                        -- antes "ref_madre" → renombrado
    nombre              TEXT,
    unidades            INTEGER,                     -- ahora Mercadeo también puede editar

    -- Mercadeo: precios
    precio_cop_iva      NUMERIC(12,2),
    precio_usd          NUMERIC(10,2),
    tasa_usd            NUMERIC(10,2),               -- NUEVO: tasa de cambio COP/USD

    -- Mercadeo: participación por canal (editable, antes fijo)
    dist_aliados        NUMERIC(5,2) DEFAULT 40,     -- NUEVO
    dist_vinculados     NUMERIC(5,2) DEFAULT 25,     -- NUEVO
    dist_tiendas        NUMERIC(5,2) DEFAULT 25,     -- NUEVO
    dist_ecommerce      NUMERIC(5,2) DEFAULT 10,     -- NUEVO

    -- Costos: solo costo inicial y final
    costo_estimado      NUMERIC(12,2),               -- costo inicial estimado
    costo_linea         NUMERIC(12,2),               -- costo final / cierre

    -- Finanzas: margen objetivo
    margen_objetivo     NUMERIC(5,2) DEFAULT 40,

    -- Corrido de materiales (Fase 2) — Costos
    costo_real          NUMERIC(12,2),

    -- Asignación final (Fase 3) — Finanzas
    precio_final_cop    NUMERIC(12,2),
    precio_final_usd    NUMERIC(10,2),
    notas_finanzas      TEXT,

    -- Métricas calculadas (se guardan para mostrar en dashboard)
    semaforo            TEXT CHECK (semaforo IN ('verde','amarillo','rojo')),  -- NUEVO
    margen_pct          NUMERIC(5,2),                -- NUEVO: margen calculado en %

    -- Flujo de fases
    fase                INTEGER DEFAULT 1 CHECK (fase IN (1,2,3)),
    fase1_aprobada      BOOLEAN DEFAULT FALSE,
    fase2_aprobada      BOOLEAN DEFAULT FALSE,
    cerrada             BOOLEAN DEFAULT FALSE,

    -- Auditoría
    creado_por          TEXT,
    creado_at           TIMESTAMPTZ DEFAULT NOW(),
    actualizado_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 2. Destinatarios por viabilidad ──────────────────────
CREATE TABLE IF NOT EXISTS notif_destinatarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    viabilidad_id   UUID REFERENCES viabilidades(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    creado_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 3. Destinatarios globales (admin) ────────────────────
CREATE TABLE IF NOT EXISTS destinatarios_globales (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    nombre      TEXT,
    rol         TEXT,
    activo      BOOLEAN DEFAULT TRUE,
    creado_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 4. Historial de cambios ──────────────────────────────
CREATE TABLE IF NOT EXISTS viabilidad_historial (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    viabilidad_id   UUID REFERENCES viabilidades(id) ON DELETE CASCADE,
    usuario         TEXT,
    accion          TEXT,
    datos_json      JSONB,
    creado_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 5. Trigger: actualizar updated_at automáticamente ────
CREATE OR REPLACE FUNCTION update_actualizado_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_viabilidades_updated ON viabilidades;
CREATE TRIGGER trg_viabilidades_updated
    BEFORE UPDATE ON viabilidades
    FOR EACH ROW EXECUTE FUNCTION update_actualizado_at();

-- ─── 6. Datos iniciales: destinatarios globales ───────────
INSERT INTO destinatarios_globales (email, nombre, rol) VALUES
    ('mercadeo@myd.com',  'Equipo Mercadeo',  'mercadeo'),
    ('costos@myd.com',    'Equipo Costos',    'costos'),
    ('finanzas@myd.com',  'Equipo Finanzas',  'finanzas')
ON CONFLICT (email) DO NOTHING;


-- ============================================================
-- SI YA TIENES LA TABLA CREADA ANTES: ejecuta solo este ALTER
-- para agregar las columnas nuevas sin borrar datos
-- ============================================================

ALTER TABLE viabilidades
    ADD COLUMN IF NOT EXISTS linea            TEXT,
    ADD COLUMN IF NOT EXISTS ref_homologa     TEXT,
    ADD COLUMN IF NOT EXISTS tasa_usd         NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS dist_aliados     NUMERIC(5,2) DEFAULT 40,
    ADD COLUMN IF NOT EXISTS dist_vinculados  NUMERIC(5,2) DEFAULT 25,
    ADD COLUMN IF NOT EXISTS dist_tiendas     NUMERIC(5,2) DEFAULT 25,
    ADD COLUMN IF NOT EXISTS dist_ecommerce   NUMERIC(5,2) DEFAULT 10,
    ADD COLUMN IF NOT EXISTS semaforo         TEXT,
    ADD COLUMN IF NOT EXISTS margen_pct       NUMERIC(5,2);

-- Renombrar ref_madre → ref_homologa (solo si usas la tabla vieja)
-- OJO: ejecutar solo si la columna "ref_madre" existe
-- ALTER TABLE viabilidades RENAME COLUMN ref_madre TO ref_homologa;


-- ============================================================
-- PERMISOS RLS (Row Level Security) — recomendado en Supabase
-- Habilita RLS y permite acceso solo con la service_role key
-- ============================================================

ALTER TABLE viabilidades          ENABLE ROW LEVEL SECURITY;
ALTER TABLE notif_destinatarios   ENABLE ROW LEVEL SECURITY;
ALTER TABLE destinatarios_globales ENABLE ROW LEVEL SECURITY;
ALTER TABLE viabilidad_historial  ENABLE ROW LEVEL SECURITY;

-- Política: acceso total para el service role (lo usa tu app Flask)
CREATE POLICY "service_role_all" ON viabilidades
    FOR ALL USING (true);

CREATE POLICY "service_role_all" ON notif_destinatarios
    FOR ALL USING (true);

CREATE POLICY "service_role_all" ON destinatarios_globales
    FOR ALL USING (true);

CREATE POLICY "service_role_all" ON viabilidad_historial
    FOR ALL USING (true);
