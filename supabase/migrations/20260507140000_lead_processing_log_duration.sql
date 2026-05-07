ALTER TABLE lead_processing_logs
    ADD COLUMN IF NOT EXISTS duration_ms integer;
