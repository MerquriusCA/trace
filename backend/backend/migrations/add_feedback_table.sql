-- Migration to add Feedback table
-- Run this in your Railway PostgreSQL database

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    page_url VARCHAR(500),
    page_title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON TABLE feedback TO your_db_user;
-- GRANT USAGE, SELECT ON SEQUENCE feedback_id_seq TO your_db_user;