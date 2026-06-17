SELECT
    checkin_date,
    sleep_hours,
    sleep_quality,
    energy_rating,
    focus_rating,
    mood_rating,
    stress_rating,
    deep_work_minutes,
    deep_work_logged,
    caffeine_logged,
    exercise_logged,
    notes,
    created_at
FROM {{ source('public', 'daily_checkin') }}
