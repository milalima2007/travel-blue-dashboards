/* ============================================================
   TRAVEL BLUE DASHBOARDS — CSV Upload Pipeline
   Handles: parsing · type detection · composite key detection
            · duplicate comparison · Supabase Storage + UPSERT
   ============================================================ */

const CSVUpload = (() => {

  /* ---- Internal Supabase client (service role) ---- */
  let _svcClient = null;
  function _svc() {
    if (!_svcClient) {
      _svcClient = supabase.createClient(
        window.SUPABASE_URL,
        window.SUPABASE_SERVICE_KEY,
        { auth: { autoRefreshToken: false, persistSession: false, detectSessionInUrl: false } }
      );
    }
    return _svcClient;
  }

  /* ---- Parse CSV file via PapaParse ---- */
  function parseFile(file) {
    return new Promise((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        dynamicTyping: false,
        complete: r => {
          if (r.errors.length) reject(new Error(r.errors[0].message));
          else resolve(r.data);
        },
        error: reject
      });
    });
  }

  /* ---- Detect column types ---- */
  const DATE_PATTERNS = [
    /^\d{4}-\d{2}-\d{2}$/,
    /^\d{2}[\/\-]\d{2}[\/\-]\d{4}$/,
    /^\d{4}-\d{2}$/,
    /^\d{4}$/,
    /^Q[1-4][\s\-]?\d{4}$/i,
    /^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-]?\d{4}$/i,
    /^(january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{4}$/i
  ];

  function detectColumnTypes(records) {
    if (!records?.length) return {};
    const cols = Object.keys(records[0]);
    const types = {};

    cols.forEach(col => {
      const vals = records
        .map(r => String(r[col] ?? '').trim())
        .filter(v => v !== '' && v.toLowerCase() !== 'null' && v.toLowerCase() !== 'n/a' && v !== '-');

      if (!vals.length) { types[col] = 'categorical'; return; }

      const dateScore    = vals.filter(v => DATE_PATTERNS.some(p => p.test(v))).length / vals.length;
      const numericScore = vals.filter(v => !isNaN(parseFloat(v.replace(/[$€£,\s%]/g, ''))) && v.replace(/[$€£,\s%]/g, '') !== '').length / vals.length;

      if (dateScore > 0.70)    { types[col] = 'date';        return; }
      if (numericScore > 0.85) { types[col] = 'numeric';     return; }
      types[col] = 'categorical';
    });

    return types;
  }

  /* ---- Detect composite key: all non-numeric columns + dimensional numerics ----
     Numeric columns are split into two categories:
       • Dimensions  (month 1-12, year 1900-2100, small integer codes) → INCLUDED in key
       • Measures    (revenue, quantity, cost, etc.)                   → EXCLUDED from key
     This prevents UPSERT collapsing monthly rows that differ only by month number.
  ---- */
  function detectCompositeKey(types, records) {
    const keys = Object.entries(types)
      .filter(([col, t]) => {
        if (t !== 'numeric') return true; // always include non-numeric (date, categorical)

        // For numeric columns: check if it looks like a DIMENSION (month/year/code)
        // rather than a MEASURE (amount, quantity).
        if (!records?.length) return false;
        const vals = records
          .map(r => parseFloat(String(r[col] ?? '').replace(/[$€£,\s]/g, '')))
          .filter(v => !isNaN(v) && isFinite(v));
        if (!vals.length) return false;
        const min = Math.min(...vals), max = Math.max(...vals);
        const allIntegers = vals.every(v => v === Math.round(v));

        // Month-like: integer values 1–12 only
        if (allIntegers && min >= 1 && max <= 12) return true;
        // Year-like: integer values 1900–2100 only
        if (allIntegers && min >= 1900 && max <= 2100) return true;

        return false; // genuine measure → exclude from key
      })
      .map(([col]) => col);
    return keys.length ? keys : [Object.keys(types)[0]];
  }

  /* ---- Generate stable row key ---- */
  function rowKey(row, keyColumns) {
    return keyColumns.map(col => String(row[col] ?? '').trim().toLowerCase()).join('||');
  }

  /* ---- Compare CSV rows with existing Supabase data ---- */
  async function compareWithExisting(projectSlug, records, keyColumns) {
    // Paginate — Supabase returns max 1000 rows per request
    const PAGE = 1000;
    let allExisting = [], page = 0;
    while (true) {
      const { data: chunk, error } = await _svc()
        .from('project_data')
        .select('composite_key, row_data')
        .eq('project_slug', projectSlug)
        .range(page * PAGE, (page + 1) * PAGE - 1);
      if (error && error.code !== 'PGRST116') {
        console.warn('Could not fetch existing data:', error.message);
        break;
      }
      if (chunk?.length) allExisting.push(...chunk);
      if (!chunk?.length || chunk.length < PAGE) break;
      page++;
    }

    const existingMap = new Map(allExisting.map(r => [r.composite_key, r.row_data]));
    const newRows = [], updateRows = [], unchangedRows = [];

    records.forEach(row => {
      const key = rowKey(row, keyColumns);
      if (!existingMap.has(key)) {
        newRows.push({ row, key });
      } else {
        const ex = existingMap.get(key);
        const isDiff = JSON.stringify(_normalize(row)) !== JSON.stringify(_normalize(ex));
        (isDiff ? updateRows : unchangedRows).push({ row, key, existing: ex });
      }
    });

    return { newRows, updateRows, unchangedRows, existingCount: existingMap.size };
  }

  function _normalize(row) {
    const n = {};
    Object.entries(row).forEach(([k, v]) => { n[k] = String(v ?? '').trim().toLowerCase(); });
    return n;
  }

  /* ---- Upload raw CSV to Supabase Storage ---- */
  async function uploadToStorage(file, projectSlug) {
    const ts  = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const ext = file.name.endsWith('.csv') ? '' : '.csv';
    const path = `${projectSlug}/${ts}_${file.name}${ext}`;

    const { data, error } = await _svc().storage
      .from('csv-uploads')
      .upload(path, file, { upsert: false, contentType: 'text/csv' });

    if (error) throw new Error(`Storage: ${error.message}`);
    return data.path;
  }

  /* ---- UPSERT rows into project_data ---- */
  async function upsertRows(projectSlug, rows, batchId) {
    const CHUNK = 500;

    // Deduplicate by composite_key before sending to Postgres.
    // If the CSV has duplicate rows sharing the same key, a single UPSERT
    // batch would hit "ON CONFLICT DO UPDATE command cannot affect row a
    // second time". Keep the last occurrence of each key (latest value wins).
    const unique = [...new Map(rows.map(r => [r.key, r])).values()];

    const records = unique.map(({ row, key }) => ({
      project_slug:  projectSlug,
      composite_key: key,
      row_data:      row,
      batch_id:      batchId,
      uploaded_at:   new Date().toISOString()
    }));

    for (let i = 0; i < records.length; i += CHUNK) {
      const { error } = await _svc()
        .from('project_data')
        .upsert(records.slice(i, i + CHUNK), { onConflict: 'project_slug,composite_key' });
      if (error) throw new Error(`Insert failed: ${error.message}`);
    }
  }

  /* ---- Save project meta (column types, keys, row count) ---- */
  async function saveMeta(projectSlug, types, keys, totalRows, batchId) {
    const { error } = await _svc()
      .from('project_meta')
      .upsert({
        project_slug:   projectSlug,
        column_types:   types,
        composite_keys: keys,
        total_rows:     totalRows,
        last_batch_id:  batchId,
        last_upload_at: new Date().toISOString(),
        updated_at:     new Date().toISOString()
      }, { onConflict: 'project_slug' });
    if (error) console.warn('Meta save failed:', error.message);
  }

  /* ---- Get project meta from Supabase ---- */
  async function getMeta(projectSlug) {
    const { data, error } = await _svc()
      .from('project_meta')
      .select('*')
      .eq('project_slug', projectSlug)
      .maybeSingle();
    if (error) return null;
    return data;
  }

  /* ---- STEP 1: Analyse file (no writes yet) ---- */
  async function analyse(file, projectSlug) {
    const records = await parseFile(file);
    if (!records.length) throw new Error('The CSV file is empty.');

    const types   = detectColumnTypes(records);
    const keys    = detectCompositeKey(types, records); // pass records to detect dimensional numerics
    const diff    = await compareWithExisting(projectSlug, records, keys);
    const batchId = 'batch_' + Date.now();

    return { file, projectSlug, records, types, keys, diff, batchId };
  }

  /* ---- STEP 2: Confirm and execute ---- */
  async function confirm(state, onProgress) {
    const { file, projectSlug, records, types, keys, diff, batchId } = state;
    const toWrite = [...diff.newRows, ...diff.updateRows];

    onProgress?.('Uploading CSV backup…', 30);
    let storagePath = null;
    try { storagePath = await uploadToStorage(file, projectSlug); }
    catch (e) { console.warn('Storage upload skipped:', e.message); }

    if (toWrite.length > 0) {
      onProgress?.(`Writing ${toWrite.length} rows…`, 60);
      await upsertRows(projectSlug, toWrite, batchId);
    }

    onProgress?.('Saving metadata…', 85);
    await saveMeta(projectSlug, types, keys, records.length, batchId);

    onProgress?.('Done!', 100);
    return {
      inserted:    diff.newRows.length,
      updated:     diff.updateRows.length,
      unchanged:   diff.unchangedRows.length,
      storagePath, batchId
    };
  }

  /* ---- Public API ---- */
  return { analyse, confirm, getMeta, detectColumnTypes, detectCompositeKey, rowKey };

})();
