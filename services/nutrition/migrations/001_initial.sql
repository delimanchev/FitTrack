CREATE TABLE IF NOT EXISTS meals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    meal_date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS meals_user_date_idx ON meals (user_id, meal_date, id);

CREATE TABLE IF NOT EXISTS meal_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    meal_id BIGINT NOT NULL REFERENCES meals (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity > 0),
    calories DOUBLE PRECISION NOT NULL CHECK (calories >= 0),
    protein DOUBLE PRECISION NOT NULL CHECK (protein >= 0),
    carbs DOUBLE PRECISION NOT NULL CHECK (carbs >= 0),
    fat DOUBLE PRECISION NOT NULL CHECK (fat >= 0)
);

CREATE INDEX IF NOT EXISTS meal_items_meal_id_idx ON meal_items (meal_id);
