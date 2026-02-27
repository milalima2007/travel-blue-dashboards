-- ============================================================
-- Travel Blue Dashboards — Supabase Setup SQL
-- Run this in the Supabase SQL Editor before first deploy.
-- Safe to re-run (uses CREATE TABLE IF NOT EXISTS, DO NOTHING).
-- ============================================================

-- ── 1. Projects table ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
  id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  slug         TEXT        UNIQUE NOT NULL,
  name         TEXT        NOT NULL,
  description  TEXT        DEFAULT '',
  icon         TEXT        DEFAULT '📊',
  status       TEXT        DEFAULT 'draft'
                           CHECK (status IN ('draft', 'active', 'archived')),
  custom_url   TEXT        DEFAULT NULL,   -- e.g. '/avolta/index.html' for legacy pages
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ
);

-- Add custom_url column if table already existed without it
ALTER TABLE projects ADD COLUMN IF NOT EXISTS custom_url TEXT DEFAULT NULL;

-- RLS: authenticated users read; service role writes
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth read projects"    ON projects;
DROP POLICY IF EXISTS "service write projects" ON projects;

CREATE POLICY "auth read projects"
  ON projects FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "service write projects"
  ON projects FOR ALL
  USING (auth.role() = 'service_role');


-- ── 2. project_data table ──────────────────────────────────
CREATE TABLE IF NOT EXISTS project_data (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  project_slug  TEXT        NOT NULL,
  composite_key TEXT        NOT NULL,
  row_data      JSONB       NOT NULL,
  batch_id      TEXT,
  uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (project_slug, composite_key)
);

ALTER TABLE project_data ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth read project_data"    ON project_data;
DROP POLICY IF EXISTS "service write project_data" ON project_data;

CREATE POLICY "auth read project_data"
  ON project_data FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "service write project_data"
  ON project_data FOR ALL
  USING (auth.role() = 'service_role');


-- ── 3. project_meta table ──────────────────────────────────
CREATE TABLE IF NOT EXISTS project_meta (
  project_slug   TEXT PRIMARY KEY,
  column_types   JSONB,
  composite_keys JSONB,
  chart_config   JSONB,   -- owner-configured column → viz type overrides
  total_rows     INTEGER,
  last_batch_id  TEXT,
  last_upload_at TIMESTAMPTZ
);

ALTER TABLE project_meta ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth read project_meta"    ON project_meta;
DROP POLICY IF EXISTS "service write project_meta" ON project_meta;

CREATE POLICY "auth read project_meta"
  ON project_meta FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "service write project_meta"
  ON project_meta FOR ALL
  USING (auth.role() = 'service_role');


-- ── 4. Seed existing projects ──────────────────────────────
-- custom_url points to the legacy hand-crafted pages.
-- New auto-generated projects will have custom_url = NULL
-- and will be served by /project/index.html?slug=<slug>.

INSERT INTO projects (slug, name, description, icon, status, custom_url, published_at)
VALUES
  ('avolta',
   'Avolta',
   'Global analytics dashboard for the Avolta partnership.',
   '✈️', 'active', '/avolta/index.html', NOW()),

  ('backpacks-and-luggage',
   'Backpacks & Luggage',
   'Sales and inventory for backpacks and luggage category.',
   '🧳', 'active', '/backpacks-and-luggage/index.html', NOW()),

  ('total-sales-bp-latam',
   'Total Sales BP LATAM',
   'Total sales vs budget plan for LATAM region.',
   '🌎', 'active', '/total-sales-bp-latam/index.html', NOW())

ON CONFLICT (slug) DO UPDATE
  SET custom_url   = EXCLUDED.custom_url,
      name         = EXCLUDED.name,
      description  = EXCLUDED.description,
      icon         = EXCLUDED.icon,
      status       = EXCLUDED.status,
      published_at = COALESCE(projects.published_at, EXCLUDED.published_at);


-- ── 5. Storage bucket (manual step) ───────────────────────
-- The csv-upload.js references the 'csv-uploads' storage bucket.
-- Create it manually in the Supabase dashboard:
--   Storage → New Bucket → Name: csv-uploads, Public: false
--
-- Or uncomment and run if using the CLI / migrations:
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('csv-uploads', 'csv-uploads', false)
-- ON CONFLICT (id) DO NOTHING;
