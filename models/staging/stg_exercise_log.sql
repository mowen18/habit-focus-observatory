SELECT
    exercise_id,
    checkin_date,
    exercise_type,
    duration_minutes,
    intensity,
    start_time
FROM {{ source('public', 'exercise_log') }}
