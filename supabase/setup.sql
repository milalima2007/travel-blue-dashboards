-- ============================================================
-- TRAVEL BLUE DASHBOARDS — Supabase Setup
-- Run this ONCE in Supabase SQL Editor before using the app.
-- Supabase → SQL Editor → New query → paste → Run
-- ============================================================

-- 1. project_data: stores all CSV rows for every project
CREATE TABLE IF NOT EXISTS public.project_data (
  id            uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  project_slug  text        NOT NULL,
  composite_key text        NOT NULL,
  row_data      jsonb       NOT NULL,
  batch_id      text,
  uploaded_at   timestamptz DEFAULT now(),
  CONSTRAINT project_data_unique UNIQUE (project_slug, composite_key)
);

CREATE INDEX IF NOT EXISTS idx_project_data_slug
  ON public.project_data (project_slug);

CREATE INDEX IF NOT EXISTS idx_project_data_slug_key
  ON public.project_data (project_slug, composite_key);

-- 2. project_meta: tracks CSV upload metadata per project
CREATE TABLE IF NOT EXISTS public.project_meta (
  project_slug    text        PRIMARY KEY,
  column_types    jsonb,        -- { "col": "date|numeric|categorical" }
  composite_keys  text[],       -- ["col1", "col2"]
  total_rows      integer DEFAULT 0,
  last_batch_id   text,
  last_upload_at  timestamptz,
  updated_at      timestamptz DEFAULT now()
);

-- 3. Row Level Security
ALTER TABLE public.project_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_meta ENABLE ROW LEVEL SECURITY;

-- Allow public read (dashboards read data without auth for now)
-- Phase 2: restrict to authenticated users via Supabase Auth
CREATE POLICY "public_read_project_data"
  ON public.project_data FOR SELECT USING (true);

CREATE POLICY "public_read_project_meta"
  ON public.project_meta FOR SELECT USING (true);

-- Allow all operations for service_role (used via config.js in admin panel)
CREATE POLICY "service_write_project_data"
  ON public.project_data FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "service_write_project_meta"
  ON public.project_meta FOR ALL
  USING (true)
  WITH CHECK (true);

-- 4. Storage bucket for raw CSV backups
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'csv-uploads',
  'csv-uploads',
  false,
  52428800,  -- 50 MB limit per file
  ARRAY['text/csv', 'text/plain', 'application/vnd.ms-excel', 'application/octet-stream']
)
ON CONFLICT (id) DO NOTHING;

-- Storage: allow service_role to upload
CREATE POLICY "service_upload_csv"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'csv-uploads');

CREATE POLICY "service_read_csv"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'csv-uploads');

-- Done!
SELECT 'Setup complete. Tables: project_data, project_meta. Bucket: csv-uploads.' AS status;
