-- ============================================================================
-- Migration: Make bill_date nullable in bills table
-- ============================================================================
-- Purpose: 
--   Changes bill_date column to allow NULL values. The date will be extracted
--   from receipt via OCR during processing, not set at bill creation time.
--
-- Affected objects:
--   - Table: bills (modify column bill_date)
--
-- Special considerations:
--   - Existing bills with bill_date will remain unchanged
--   - New bills will have bill_date = NULL until OCR processing completes
--   - bill_date will be set from OCR data if successfully extracted
-- ============================================================================

-- Alter bill_date column to allow NULL
ALTER TABLE bills 
ALTER COLUMN bill_date DROP NOT NULL;

-- Add comment to clarify the purpose
COMMENT ON COLUMN bills.bill_date IS 'Date extracted from receipt via OCR (set during processing, can be NULL if not extracted)';
