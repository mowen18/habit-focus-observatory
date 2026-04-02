-- Stores one daily rollup row per calendar date.
CREATE TABLE daily_checkin (
    checkin_date DATE PRIMARY KEY,
    sleep_hours NUMERIC(4,2) CHECK (sleep_hours IS NULL OR sleep_hours >= 0),
    sleep_quality INTEGER CHECK (sleep_quality IS NULL OR sleep_quality BETWEEN 1 AND 10),
    energy_rating INTEGER CHECK (energy_rating IS NULL OR energy_rating BETWEEN 1 AND 10),
    focus_rating INTEGER CHECK (focus_rating IS NULL OR focus_rating BETWEEN 1 AND 10),
    mood_rating INTEGER CHECK (mood_rating IS NULL OR mood_rating BETWEEN 1 AND 10),
    stress_rating INTEGER CHECK (stress_rating IS NULL OR stress_rating BETWEEN 1 AND 10),
    deep_work_minutes INTEGER CHECK (deep_work_minutes IS NULL OR deep_work_minutes >= 0),
    deep_work_logged BOOLEAN NOT NULL DEFAULT FALSE,
    caffeine_logged BOOLEAN NOT NULL DEFAULT FALSE,
    exercise_logged BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stores individual caffeine intake events linked to a daily check-in.
CREATE TABLE caffeine_log (
    caffeine_id SERIAL PRIMARY KEY,
    checkin_date DATE NOT NULL REFERENCES daily_checkin(checkin_date),
    intake_time TIME NOT NULL,
    source VARCHAR(50),
    caffeine_mg INTEGER NOT NULL CHECK (caffeine_mg >= 0)
);

-- Stores individual exercise sessions linked to a daily check-in.
CREATE TABLE exercise_log (
    exercise_id SERIAL PRIMARY KEY,
    checkin_date DATE NOT NULL REFERENCES daily_checkin(checkin_date),
    exercise_type VARCHAR(50) NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes >= 0),
    intensity VARCHAR(20),
    start_time TIME
);
