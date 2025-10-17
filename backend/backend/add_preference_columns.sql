-- Add user preference columns to the User table
-- Run this SQL script if the Python migration script doesn't work

-- Add summary_style column (quick, eli8, detailed)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' AND column_name = 'summary_style'
    ) THEN
        ALTER TABLE "user" ADD COLUMN summary_style VARCHAR(20) DEFAULT 'eli8';
        RAISE NOTICE 'Added summary_style column';
    ELSE
        RAISE NOTICE 'summary_style column already exists';
    END IF;
END
$$;

-- Add auto_summarize_enabled column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' AND column_name = 'auto_summarize_enabled'
    ) THEN
        ALTER TABLE "user" ADD COLUMN auto_summarize_enabled BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added auto_summarize_enabled column';
    ELSE
        RAISE NOTICE 'auto_summarize_enabled column already exists';
    END IF;
END
$$;

-- Add notifications_enabled column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' AND column_name = 'notifications_enabled'
    ) THEN
        ALTER TABLE "user" ADD COLUMN notifications_enabled BOOLEAN DEFAULT true;
        RAISE NOTICE 'Added notifications_enabled column';
    ELSE
        RAISE NOTICE 'notifications_enabled column already exists';
    END IF;
END
$$;

-- Verify the columns were added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'user' 
  AND column_name IN ('summary_style', 'auto_summarize_enabled', 'notifications_enabled')
ORDER BY column_name;