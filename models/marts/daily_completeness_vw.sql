WITH section_status AS (
    SELECT
        dc.checkin_date,
        (
            dc.sleep_hours IS NOT NULL
            OR dc.sleep_quality IS NOT NULL
            OR dc.energy_rating IS NOT NULL
            OR dc.focus_rating IS NOT NULL
            OR dc.mood_rating IS NOT NULL
            OR dc.stress_rating IS NOT NULL
            OR dc.notes IS NOT NULL
        ) AS has_checkin,
        dc.deep_work_logged AS has_deep_work_entry,
        dc.caffeine_logged AS has_caffeine_entry,
        dc.exercise_logged AS has_exercise_entry
    FROM {{ ref('stg_daily_checkin') }} AS dc
)
SELECT
    checkin_date,
    has_checkin,
    has_deep_work_entry,
    has_caffeine_entry,
    has_exercise_entry,
    (
        has_checkin::INTEGER
        + has_deep_work_entry::INTEGER
        + has_caffeine_entry::INTEGER
        + has_exercise_entry::INTEGER
    ) AS completed_sections,
    4 AS expected_sections,
    ROUND(
        100.0 * (
            has_checkin::INTEGER
            + has_deep_work_entry::INTEGER
            + has_caffeine_entry::INTEGER
            + has_exercise_entry::INTEGER
        ) / 4,
        1
    ) AS completeness_pct
FROM section_status
