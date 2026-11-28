CREATE TABLE IF NOT EXISTS goals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    goal_type TEXT NOT NULL CHECK (goal_type IN ('weight', 'weekly_workouts')),
    target DOUBLE PRECISION NOT NULL CHECK (target > 0 AND target <= 1000),
    start_weight_kg DOUBLE PRECISION,
    CHECK (
        (goal_type = 'weight' AND start_weight_kg IS NOT NULL
            AND start_weight_kg > 0 AND start_weight_kg <= 1000 AND start_weight_kg <> target)
        OR (goal_type = 'weekly_workouts' AND start_weight_kg IS NULL AND target = trunc(target))
    )
);

CREATE INDEX IF NOT EXISTS goals_user_idx ON goals (user_id, id);

CREATE TABLE IF NOT EXISTS goal_reminders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    goal_id BIGINT NOT NULL REFERENCES goals (id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    reminder_time TIME NOT NULL,
    enabled BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS goal_reminders_goal_idx ON goal_reminders (goal_id);
