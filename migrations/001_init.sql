-- ============================================================
-- M&D Viabilidad de Precios — Supabase SQL
-- Ejecutar en: Supabase > SQL Editor
-- ============================================================

-- Tabla principal de viabilidades
CREATE TABLE IF NOT EXISTS viabilidades (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referencia    TEXT NOT NULL,
    ref_madre     TEXT,
    nombre        TEXT,
    unidades      INTEGER,

    -- Mercadeo
    precio_cop_iva  NUMERIC(12,2),
    precio_usd      NUMERIC(10,2),

    -- Costos
    costo_estimado  NUMERIC(12,2),
    costo_linea     NUMERIC(12,2),
    margen_objetivo NUMERIC(5,2) DEFAULT 40,

    -- Corrido de materiales (Fase 2)
    costo_real      NUMERIC(12,2),

    -- Asignación final (Fase 3)
    precio_final_cop  NUMERIC(12,2),
    precio_final_usd  NUMERIC(10,2),
    notas_finanzas    TEXT,

    -- Flujo
    fase              INTEGER DEFAULT 1 CHECK (fase IN (1,2,3)),
    fase1_aprobada    BOOLEAN DEFAULT FALSE,
    fase2_aprobada    BOOLEAN DEFAULT FALSE,
    cerrada           BOOLEAN DEFAULT FALSE,

    -- Auditoría
    creado_por    TEXT,
    creado_at     TIMESTAMPTZ DEFAULT NOW(),
    actualizado_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de destinatarios de notificación por viabilidad
CREATE TABLE IF NOT EXISTS notif_destinatarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    viabilidad_id   UUID REFERENCES viabilidades(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    creado_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de destinatarios globales (configuración del admin)
CREATE TABLE IF NOT EXISTS destinatarios_globales (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email     TEXT UNIQUE NOT NULL,
    nombre    TEXT,
    rol       TEXT,
    activo    BOOLEAN DEFAULT TRUE,
    creado_at TIMESTAMPTZ DEFAULT NOW()
);

-- Historial de cambios por viabilidad
CREATE TABLE IF NOT EXISTS viabilidad_historial (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    viabilidad_id   UUID REFERENCES viabilidades(id) ON DELETE CASCADE,
    usuario         TEXT,
    accion          TEXT,
    datos_json      JSONB,
    creado_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_actualizado_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_viabilidades_updated
    BEFORE UPDATE ON viabilidades
    FOR EACH ROW EXECUTE FUNCTION update_actualizado_at();

-- Datos iniciales: destinatarios globales de ejemplo
INSERT INTO destinatarios_globales (email, nombre, rol) VALUES
    ('mercadeo@myd.com',  'Equipo Mercadeo',  'mercadeo'),
    ('costos@myd.com',    'Equipo Costos',    'costos'),
    ('finanzas@myd.com',  'Equipo Finanzas',  'finanzas')
ON CONFLICT (email) DO NOTHING;
