SELECT
    caffeine_id,
    checkin_date,
    intake_time,
    source,
    caffeine_mg
FROM {{ source('public', 'caffeine_log') }}
