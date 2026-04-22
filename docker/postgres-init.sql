-- Initial extensions for the shared agentic_commerce DB.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

-- Read-only role used by the conversational-assistant's search_kb tool.
-- kbgen owns kb.*; the assistant reads it.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'assistant_ro') THEN
        CREATE ROLE assistant_ro LOGIN PASSWORD 'assistant_ro_dev_2026';
    END IF;
END $$;

GRANT CONNECT ON DATABASE agentic_commerce TO assistant_ro;
