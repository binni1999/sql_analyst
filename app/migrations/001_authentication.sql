-- DataPilot authentication schema. Safe to run more than once.
-- The application also creates these tables lazily for local Docker setups.
CREATE TABLE IF NOT EXISTS datapilot_users (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS datapilot_auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES datapilot_users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_datapilot_auth_sessions_user_id ON datapilot_auth_sessions(user_id);
CREATE TABLE IF NOT EXISTS datapilot_conversation_owners (
    conversation_id VARCHAR(200) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES datapilot_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_datapilot_conversation_owners_user_id ON datapilot_conversation_owners(user_id);
CREATE TABLE IF NOT EXISTS datapilot_login_attempts (
    id BIGSERIAL PRIMARY KEY,
    client_key CHAR(64) NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_datapilot_login_attempts_key_time ON datapilot_login_attempts(client_key, attempted_at);
