-- Migration: Add efficiency column to traderecord table
-- Date: 2025-01-12
-- Purpose: Add efficiency metric (capture ratio: realized_pnl / mfe)

-- Add efficiency column (nullable, since existing trades won't have this value)
ALTER TABLE traderecord
ADD COLUMN IF NOT EXISTS efficiency DOUBLE PRECISION;

-- Add comment for documentation
COMMENT ON COLUMN traderecord.efficiency IS 'Capture ratio: realized_pnl / mfe (0.0-1.0+), measures how much of maximum potential profit was captured';
