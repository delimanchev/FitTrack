CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('weight', 'body')),
    area TEXT,
    value DOUBLE PRECISION NOT NULL CHECK (value > 0 AND value <= 1000),
    measured_at DATE NOT NULL,
    CHECK ((kind = 'weight' AND area IS NULL) OR (kind = 'body' AND area IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS measurements_user_history_idx
    ON measurements (user_id, kind, measured_at DESC, id DESC);
